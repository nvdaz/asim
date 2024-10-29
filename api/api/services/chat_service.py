import asyncio
import random
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from typing import AsyncGenerator

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
from api.services import chat_generation, generate_suggestions, message_generation

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

    @asynccontextmanager
    async def modify(self) -> AsyncGenerator[ChatData, None]:
        try:
            async with self._lock:
                yield self._chat
        finally:
            self._changed.set()
            await update_chat(self._chat)


async def generate_agent_message(
    chat_state: ChatState, user: UserData, objective: str | None = None
):
    async with chat_state.modify() as chat:
        chat.agent_typing = True

    chat_data = chat_state.read()

    next_state = None

    match (chat_data.state, user.options.feedback_mode):
        case ("no-objective", _):
            next_state = "objective"
        case ("objective" | "objective-blunt", "on-suggestion"):
            next_state = "no-objective"
        case ("objective" | "objective-blunt", "on-submit"):
            next_state = "react"
        case ("react", _):
            next_state = "no-objective"

    assert next_state is not None

    if chat_data.state == "no-objective" and "blunt" not in chat_data.objectives_used:
        chance = (
            1
            if len(chat_data.objectives_used) >= len(generate_suggestions.objectives)
            else 0.3
        )
        if random.random() < chance:
            objective = "blunt-initial"
            next_state = "objective-blunt"

    response_content = await chat_generation.generate_agent_message(
        user=user, chat=chat_data, state=next_state, objective=objective
    )

    response = ChatMessage(
        sender=chat_data.agent,
        content=response_content,
        created_at=datetime.now(timezone.utc),
    )

    async with chat_state.modify() as chat:
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

    if chat.state == "react":
        if not objective:
            async with chat_state.modify() as chat:
                chat.state = "objective"
        else:
            async with chat_state.modify() as chat:
                chat.loading_feedback = True

            feedback = await generate_suggestions.explain_suggestion(
                objective,
                True,
                message_generation.format_messages_context_short(
                    chat.messages, chat.agent
                ),
            )

            async with chat_state.modify() as chat:
                chat.messages.append(
                    InChatFeedback(
                        feedback=feedback, created_at=datetime.now(timezone.utc)
                    )
                )
                chat.loading_feedback = False
                chat.generating_suggestions = 1
                chat.events.append(
                    ChatEvent(
                        name="feedback-generated",
                        data=feedback,
                        created_at=datetime.now(timezone.utc),
                    )
                )

            follow_up = await message_generation.generate_message(
                user=user,
                user_sent=True,
                agent_name=chat.agent,
                messages=chat.messages,
                objective_prompt=generate_suggestions.objective_misunderstand_follow_up_prompt(
                    objective
                ),
            )

            explanation = await generate_suggestions.explain_suggestion(
                objective, False, follow_up
            )

            suggestions = [
                Suggestion(
                    message=follow_up,
                    feedback=explanation,
                    objective=objective,
                    needs_improvement=False,
                )
            ]

            async with chat_state.modify() as chat:
                chat.suggestions = suggestions
                chat.generating_suggestions = 0
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

    return chat_data


async def suggest_messages(chat_state: ChatState, user: UserData, prompt_message: str):
    async with chat_state.modify() as chat:
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

    context = message_generation.format_messages_context_short(
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
            context, base_message
        )
    elif chat.state == "objective":
        if len(chat.objectives_used) >= len(generate_suggestions.objectives):
            chat.objectives_used = []

        (
            objective,
            suggestions,
        ) = await generate_suggestions.generate_message_variations(
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
            chat.objectives_used,
            context,
            base_message,
            user.options.feedback_mode == "on-suggestion",
        )

        chat.objectives_used.append("blunt")
    else:
        raise ValueError(f"Invalid chat state: {chat.state}")

    async with chat_state.modify() as chat:
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
    async with chat_state.modify() as chat:
        assert chat.suggestions is not None

        suggestion = chat.suggestions[index]

        chat.state = (
            chat.state
            if not (
                not suggestion.needs_improvement
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
        chat.suggestions = None
        chat.events.append(
            ChatEvent(
                name="user-message",
                data={"index": index, "content": suggestion.message},
                created_at=datetime.now(timezone.utc),
            )
        )

    return suggestion.objective


async def mark_view_suggestion(chat_state: ChatState, index: int):
    async with chat_state.modify() as chat:
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
    async with chat_state.modify() as chat:
        chat.unread = False
