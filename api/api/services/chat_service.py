import asyncio
import random
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from typing import AsyncGenerator, Callable

import faker
from bson import ObjectId

from api.db import chats
from api.schemas.chat import (
    BaseChat,
    ChatData,
    ChatEvent,
    ChatInfo,
    ChatMessage,
    InChatFeedback,
    Suggestion,
    suggestion_list_adapter,
)
from api.schemas.user import UserData
from api.services import (
    chat_generation,
    generate_feedback,
    generate_suggestions,
    message_generation,
)

_fake = faker.Faker()


async def create_chat(user: UserData) -> ChatData:
    chat = BaseChat(
        user_id=user.id,
        agent=_fake.first_name(),
        last_updated=datetime.now(timezone.utc),
    )

    return await chats.create(chat)


async def get_chat(chat_id: ObjectId, user_id: ObjectId) -> ChatData | None:
    return await chats.get(chat_id, user_id)


async def update_chat(chat: ChatData) -> ChatData:
    return await chats.update_chat(chat)


async def get_chats(user_id: ObjectId) -> list[ChatInfo]:
    return [ChatInfo.from_data(chat) for chat in await chats.get_chats(user_id)]


class ChatState:
    def __init__(self, chat: ChatData):
        self._chat = chat
        self._lock = asyncio.Lock()
        self._changed = asyncio.Event()
        self.id = chat.id

    async def wait_for_change(self):
        await self._changed.wait()
        self._changed.clear()

    def read(self) -> ChatData:
        return self._chat

    def mark_changed(self):
        self._changed.set()

    @asynccontextmanager
    async def transaction(
        self,
    ) -> AsyncGenerator[tuple[ChatData, Callable[[], None]], None]:
        try:
            async with self._lock:
                yield self._chat, self.mark_changed
        finally:
            self.mark_changed()
            await update_chat(self._chat)


async def generate_agent_message(
    chat_state: ChatState, user: UserData, objective: str | None = None
):
    async with chat_state.transaction() as (chat, mark_changed):
        chat.agent_typing = True
        mark_changed()

        next_state = None

        match (chat.state, user.options.feedback_mode):
            case ("no-objective", _):
                next_state = (
                    "objective"
                    if len(generate_suggestions.objectives) > 0
                    else "no-objective"
                )
            case ("objective" | "objective-blunt", "on-suggestion"):
                next_state = "no-objective"
            case ("objective" | "objective-blunt", "on-submit"):
                next_state = "react"
            case ("react", _):
                next_state = "no-objective"

        assert next_state is not None

        if len(chat.objectives_used) > len(generate_suggestions.objectives):
            chat.objectives_used = []

        if (
            chat.state == "no-objective"
            and "blunt" not in chat.objectives_used
            and len(chat.messages) > 1
        ) and (
            len(chat.objectives_used) >= len(generate_suggestions.objectives)
            or random.random() < 0.4
        ):
            objective = "blunt-initial"
            next_state = "objective-blunt"

        response_content = await chat_generation.generate_agent_message(
            user=user,
            chat=chat,
            state=next_state,
            objective=objective,
            problem=chat.current_problem,
        )

        response = ChatMessage(
            sender=chat.agent,
            content=response_content,
            created_at=datetime.now(timezone.utc),
        )

        chat.messages.append(response)
        chat.last_updated = datetime.now(timezone.utc)
        chat.agent_typing = False
        chat.unread = True
        chat.loading_feedback = next_state == "react" and objective is not None
        chat.state = next_state
        chat.events.append(
            ChatEvent(
                name="agent-message",
                data={"content": response_content, "objective": objective},
                created_at=datetime.now(timezone.utc),
            )
        )
        mark_changed()

        if chat.state == "react":
            if not objective:
                chat.state = "objective"
            else:
                chat.loading_feedback = True
                mark_changed()

                assert isinstance(chat.messages[-2], ChatMessage)
                assert isinstance(chat.messages[-1], ChatMessage)
                assert chat.current_problem is not None
                assert chat.best_suggestion is not None

                alternative_message = chat.best_suggestion.message

                async def generate_feedback_suggestions():
                    follow_up = await message_generation.generate_message(
                        user=user,
                        user_sent=True,
                        agent_name=chat.agent,
                        messages=chat.messages,
                        objective_prompt=generate_suggestions.objective_misunderstand_follow_up_prompt(
                            objective, chat.current_problem
                        ),
                    )

                    return [
                        Suggestion(
                            message=follow_up,
                            objective=objective,
                            problem=chat.current_problem,
                        )
                    ]

                context = message_generation.format_messages_context_long(
                    chat.messages, chat.agent
                )

                (
                    feedback_original,
                    suggestions,
                ) = await asyncio.gather(
                    generate_feedback.explain_message(
                        user,
                        chat.agent,
                        objective,
                        chat.current_problem,
                        chat.messages[-2].content,
                        context,
                        chat.messages[-1].content,
                        chat.messages[-3].content
                        if len(chat.messages) > 2
                        and isinstance(chat.messages[-3], ChatMessage)
                        else None,
                    ),
                    generate_feedback_suggestions(),
                )

                feedback_alternative = (
                    await generate_feedback.explain_message_alternative(
                        user,
                        chat.agent,
                        objective,
                        alternative_message,
                        context,
                        original=chat.messages[-2].content,
                        feedback_original=feedback_original.body,
                    )
                )

                chat.messages.append(
                    InChatFeedback(
                        feedback=feedback_original,
                        alternative=alternative_message,
                        alternative_feedback=feedback_alternative,
                        created_at=datetime.now(timezone.utc),
                    )
                )
                chat.suggestions = suggestions
                chat.loading_feedback = False
                chat.events.append(
                    ChatEvent(
                        name="feedback-generated",
                        data=feedback_original,
                        created_at=datetime.now(timezone.utc),
                    )
                )
                chat.events.append(
                    ChatEvent(
                        name="suggested-messages",
                        data={
                            "suggestions": suggestion_list_adapter.dump_python(
                                suggestions
                            )
                        },
                        created_at=datetime.now(timezone.utc),
                    )
                )
                chat.state = "react"

            return chat


async def suggest_messages(chat_state: ChatState, user: UserData, prompt_message: str):
    async with chat_state.transaction() as (chat, mark_changed):
        chat.generating_suggestions = 3
        chat.events.append(
            ChatEvent(
                name="suggestion-request",
                data={
                    "prompt_message": prompt_message,
                },
                created_at=datetime.now(timezone.utc),
            )
        )
        mark_changed()

        context = message_generation.format_messages_context_long(
            chat.messages, chat.agent
        )

        objective = None

        if user.options.suggestion_generation == "random":
            base_message = await message_generation.generate_message(
                user=user,
                agent_name=chat.agent,
                user_sent=True,
                messages=chat.messages,
            )
        else:
            base_message = prompt_message

        if chat.state == "no-objective":
            suggestions = await generate_suggestions.generate_message_variations_ok(
                user,
                chat.agent,
                context,
                base_message,
                user.options.feedback_mode == "on-suggestion",
            )
        elif chat.state == "objective":
            if len(chat.objectives_used) >= len(generate_suggestions.objectives):
                chat.objectives_used = []

            (
                objective,
                suggestions,
            ) = await generate_suggestions.generate_message_variations(
                user,
                chat.agent,
                chat.objectives_used,
                context,
                base_message,
                user.options.feedback_mode == "on-suggestion",
            )

            chat.objectives_used.append(objective)
        elif chat.state == "objective-blunt":
            (
                objective,
                suggestions,
            ) = await generate_suggestions.generate_message_variations_blunt(
                user,
                chat.agent,
                chat.objectives_used,
                context,
                base_message,
                user.options.feedback_mode == "on-suggestion",
            )

            chat.objectives_used.append("blunt")
        else:
            raise ValueError(f"Invalid chat state: {chat.state}")

        chat.suggestions = suggestions
        chat.generating_suggestions = 0
        chat.events.append(
            ChatEvent(
                name="suggestions-generated",
                data={
                    "suggestions": suggestion_list_adapter.dump_python(suggestions),
                    "objective": objective,
                },
                created_at=datetime.now(timezone.utc),
            )
        )

    return suggestions


async def send_message(chat_state: ChatState, user: UserData, index: int):
    assert user.name
    async with chat_state.transaction() as (chat, _):
        assert chat.suggestions is not None

        suggestion = chat.suggestions[index]

        chat.state = (
            chat.state
            if not (
                not suggestion.problem is not None
                and chat.state in ("objective", "objective-blunt")
            )
            else "react"
        )

        chat.messages.append(
            ChatMessage(
                sender=user.name,
                content=suggestion.message,
                created_at=datetime.now(timezone.utc),
            )
        )
        chat.last_updated = datetime.now(timezone.utc)
        chat.best_suggestion = chat.suggestions[0]
        chat.suggestions = None
        chat.events.append(
            ChatEvent(
                name="user-message",
                data={"index": index, "content": suggestion.message},
                created_at=datetime.now(timezone.utc),
            )
        )
        chat.current_problem = suggestion.problem

    return suggestion.objective


async def mark_view_suggestion(chat_state: ChatState, index: int):
    async with chat_state.transaction() as (chat, _):
        assert chat.suggestions is not None

        suggestion = chat.suggestions[index]

        chat.events.append(
            ChatEvent(
                name="viewed-suggestion",
                data={"index": index, "suggestion": suggestion},
                created_at=datetime.now(timezone.utc),
            )
        )


async def mark_read(chat_state: ChatState):
    async with chat_state.transaction() as (chat, _):
        chat.unread = False
