import asyncio
import random
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from typing import Callable

import faker
from bson import ObjectId

from api.db import chats, users
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
    base_chat = BaseChat(
        user_id=user.id,
        agent=_fake.first_name(),
        last_updated=datetime.now(timezone.utc),
        suggestion_generation=user.options.suggestion_generation,
        objectives_used=[
            objective
            for objective in generate_suggestions.ALL_OBJECTIVES + ["blunt"]
            if objective not in user.options.enabled_objectives
        ],
    )

    chat = await chats.create(base_chat)

    if user.options.suggestion_generation == "random":
        chat.suggestions = [
            Suggestion(message="Hello!", objective=None),
            Suggestion(message=f"Hi {chat.agent}, how are you?", objective=None),
            Suggestion(message="Hey!", objective=None),
        ]

    await chats.update_chat(chat)

    user.options.suggestion_generation = (
        "content-inspired"
        if user.options.suggestion_generation == "random"
        else "random"
    )

    await users.update(user.id, user)

    return chat


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

    async def commit(self):
        await update_chat(self._chat)


async def _generate_agent_message(
    chat_state: ChatState,
    user: UserData,
    objective: str | None = None,
    problem: str | None = None,
):
    async with chat_state.transaction() as (chat, mark_changed):
        assert user.personalization
        pers = message_generation.get_personalization_options(
            user.personalization, chat.suggestion_generation == "content-inspired"
        )
        chat.agent_typing = True
        mark_changed()

        next_state = None
        match (chat.state, user.options.feedback_mode):
            case ("no-objective", _):
                next_state = (
                    "objective"
                    if len(chat.messages) > 2
                    and len(generate_suggestions.ALL_OBJECTIVES) > 0
                    else "no-objective"
                )
            case ("objective" | "objective-blunt", "on-suggestion"):
                next_state = "no-objective"
            case ("objective" | "objective-blunt", "on-submit"):
                next_state = "react"
            case ("react", _):
                next_state = "no-objective"

        assert next_state is not None

        if (
            chat.state == "no-objective"
            and "blunt" not in chat.objectives_used
            and len(chat.messages) > 3
            and len(chat.objectives_used) >= len(generate_suggestions.ALL_OBJECTIVES)
        ):
            objective = "blunt-initial"
            next_state = "objective-blunt"

        response_content = await chat_generation.generate_agent_message(
            pers=pers,
            chat=chat,
            state=next_state,
            objective=objective,
            problem=problem,
            bypass_objective_prompt_check=(objective == "blunt-initial"),
        )

        await asyncio.sleep(3)

        response = ChatMessage(
            sender=chat.agent,
            content=response_content,
            created_at=datetime.now(timezone.utc),
        )

        chat.messages.append(response)
        chat.last_updated = datetime.now(timezone.utc)
        chat.agent_typing = False
        chat.unread = True

        chat.state = next_state
        chat.loading_feedback = chat.state == "react"
        chat.events.append(
            ChatEvent(
                name="agent-message",
                data={"content": response_content, "objective": objective},
                created_at=datetime.now(timezone.utc),
            )
        )
        mark_changed()

        if chat.state == "react":
            assert isinstance(chat.messages[-2], ChatMessage)
            assert isinstance(chat.messages[-1], ChatMessage)
            assert chat.last_suggestions is not None
            assert objective is not None

            context = message_generation.format_messages_context_long(
                chat.messages, chat.agent
            )

            if not problem:
                chat.state = "objective"

                feedback = await generate_feedback.explain_message(
                    pers,
                    chat.agent,
                    objective,
                    problem,
                    chat.messages[-2].content,
                    context,
                    chat.messages[-1].content,
                    chat.messages[-3].content
                    if len(chat.messages) > 2
                    and isinstance(chat.messages[-3], ChatMessage)
                    else None,
                    chat.last_suggestions,
                )

                chat.messages.append(
                    InChatFeedback(
                        feedback=feedback,
                        created_at=datetime.now(timezone.utc),
                    )
                )
                chat.events.append(
                    ChatEvent(
                        name="feedback-generated",
                        data=feedback,
                        created_at=datetime.now(timezone.utc),
                    )
                )
                chat.loading_feedback = False
                chat.state = "react"
                mark_changed()
            else:
                alternative = next(
                    filter(lambda s: s.problem is None, chat.last_suggestions)
                )

                async def generate_feedback_suggestions():
                    follow_up = await message_generation.generate_message(
                        pers=pers,
                        user_sent=True,
                        agent_name=chat.agent,
                        messages=chat.messages,
                        objective_prompt=generate_suggestions.objective_misunderstand_follow_up_prompt(
                            objective, problem
                        ),
                    )

                    return [
                        Suggestion(
                            message=follow_up,
                            objective=objective,
                            problem=problem,
                        )
                    ]

                (
                    feedback_original,
                    suggestions,
                ) = await asyncio.gather(
                    generate_feedback.explain_message(
                        pers,
                        chat.agent,
                        objective,
                        problem,
                        chat.messages[-2].content,
                        context,
                        chat.messages[-1].content,
                        chat.messages[-3].content
                        if len(chat.messages) > 2
                        and isinstance(chat.messages[-3], ChatMessage)
                        else None,
                        chat.last_suggestions,
                    ),
                    generate_feedback_suggestions(),
                )

                feedback_alternative = (
                    await generate_feedback.explain_message_alternative(
                        pers,
                        chat.agent,
                        objective,
                        alternative.message,
                        context,
                        original=chat.messages[-2].content,
                        feedback_original=feedback_original.body,
                    )
                )

                chat.messages.append(
                    InChatFeedback(
                        feedback=feedback_original,
                        alternative=alternative.message,
                        alternative_feedback=feedback_alternative,
                        created_at=datetime.now(timezone.utc),
                    )
                )
                random.shuffle(suggestions)
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
                mark_changed()

                return

    if chat.suggestion_generation == "random":
        await _suggest_messages(chat_state, user, response_content)


async def _suggest_messages(chat_state: ChatState, user: UserData, prompt_message: str):
    async with chat_state.transaction() as (chat, mark_changed):
        assert user.personalization
        pers = message_generation.get_personalization_options(
            user.personalization, chat.suggestion_generation == "content-inspired"
        )
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

        objective = None

        if chat.suggestion_generation == "random":
            base_message = await message_generation.generate_message(
                pers=pers,
                agent_name=chat.agent,
                user_sent=True,
                messages=chat.messages,
            )
        else:
            base_message = prompt_message

        if chat.state == "objective":
            (
                objective,
                suggestions,
            ) = await generate_suggestions.generate_message_variations(
                pers,
                chat.agent,
                chat.objectives_used,
                message_generation.format_messages_context_m(chat.messages, chat.agent),
                base_message,
                user.options.feedback_mode == "on-suggestion",
            )

            chat.objectives_used.append(objective)
        elif chat.state == "objective-blunt":
            (
                objective,
                suggestions,
            ) = await generate_suggestions.generate_message_variations_blunt(
                pers,
                chat.agent,
                chat.objectives_used,
                message_generation.format_messages_context_m(chat.messages, chat.agent),
                base_message,
                user.options.feedback_mode == "on-suggestion",
            )

            chat.objectives_used.append("blunt")
        else:
            suggestions = await generate_suggestions.generate_message_variations_ok(
                pers,
                chat.agent,
                message_generation.format_messages_context_m(chat.messages, chat.agent),
                base_message,
                user.options.feedback_mode == "on-suggestion",
            )

        random.shuffle(suggestions)
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


async def suggest_messages(chat_state: ChatState, user: UserData, prompt_message: str):
    suggestions = await _suggest_messages(chat_state, user, prompt_message)
    await chat_state.commit()
    return suggestions


async def _send_message(chat_state: ChatState, user: UserData, index: int):
    assert user.personalization
    async with chat_state.transaction() as (chat, _):
        assert chat.suggestions is not None

        pers = message_generation.get_personalization_options(
            user.personalization, chat.suggestion_generation == "content-inspired"
        )

        suggestion = chat.suggestions[index]

        if (
            suggestion.problem is None
            and chat.state != "objective"
            and len(chat.objectives_used) > len(generate_suggestions.ALL_OBJECTIVES)
        ):
            chat.checkpoint_rate = True
            chat.objectives_used = [
                objective
                for objective in generate_suggestions.ALL_OBJECTIVES + ["blunt"]
                if objective not in user.options.enabled_objectives
            ]

        chat.messages.append(
            ChatMessage(
                sender=pers.name,
                content=suggestion.message,
                created_at=datetime.now(timezone.utc),
            )
        )
        chat.last_updated = datetime.now(timezone.utc)
        chat.last_suggestions = chat.suggestions
        chat.suggestions = None
        chat.events.append(
            ChatEvent(
                name="user-message",
                data={"index": index, "content": suggestion.message},
                created_at=datetime.now(timezone.utc),
            )
        )

    return suggestion.objective, suggestion.problem


async def send_message(chat_state: ChatState, user: UserData, index: int):
    objective, problem = await _send_message(chat_state, user, index)
    await _generate_agent_message(chat_state, user, objective, problem)
    await chat_state.commit()


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
    await chat_state.commit()


async def rate_feedback(chat_state: ChatState, index: int, rating: int):
    async with chat_state.transaction() as (chat, mark_changed):
        chat.events.append(
            ChatEvent(
                name="feedback-rated",
                created_at=datetime.now(timezone.utc),
                data={"index": index, "rating": rating},
            )
        )

        feedback = chat.messages[index]
        assert isinstance(feedback, InChatFeedback)

        feedback.rating = rating
    await chat_state.commit()


async def checkpoint_rating(chat_state: ChatState, ratings: dict[str, int]):
    async with chat_state.transaction() as (chat, mark_changed):
        chat.events.append(
            ChatEvent(
                name="overall-rating",
                created_at=datetime.now(timezone.utc),
                data=ratings,
            )
        )
        chat.checkpoint_rate = False

        mark_changed()
    await chat_state.commit()
