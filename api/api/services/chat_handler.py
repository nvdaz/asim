import json
from datetime import datetime, timezone

import faker
from bson import ObjectId
from fastapi import WebSocket

from api.db import chats
from api.schemas.chat import (
    BaseChat,
    ChatApi,
    ChatData,
    ChatEvent,
    ChatInfo,
    ChatMessage,
    InChatFeedback,
    Suggestion,
    chat_info_list_adapter,
    suggestion_list_adapter,
)
from api.schemas.user import UserData
from api.services import generate_suggestions, message_generation

fake = faker.Faker()


async def create_chat(
    user: UserData,
) -> ChatData:
    name = fake.first_name()

    chat = BaseChat(
        user_id=user.id,
        agent=name,
        last_updated=datetime.now(timezone.utc),
    )

    return await chats.create(chat)


async def get_chat(
    id: ObjectId,
    user: UserData,
) -> ChatData | None:
    return await chats.get(id, user.id)


async def update_chat(
    chat: ChatData,
) -> ChatData:
    return await chats.update_chat(chat)


async def get_chats(user: UserData) -> list[ChatInfo]:
    return [ChatInfo.from_data(chat) for chat in await chats.get_chats(user.id)]


async def handle_connection(
    ws: WebSocket,
    user: UserData,
):
    all_chats = await get_chats(user)

    await ws.send_json(
        {
            "type": "sync-chats",
            "chats": json.loads(chat_info_list_adapter.dump_json(all_chats)),
        }
    )

    async def generate_agent_message(
        chat: ChatData,
        objective: str | None = None,
    ):
        chat.agent_typing = True

        if chat.state == "no-objective":
            chat.state = "objective"
        elif chat.state == "objective":
            if user.options.feedback_mode == "on-suggestion":
                chat.state = "no-objective"
            elif user.options.feedback_mode == "on-submit":
                chat.state = "react"
            else:
                raise ValueError(f"Invalid feedback mode: {user.options.feedback_mode}")
        elif chat.state == "react":
            chat.state = "no-objective"
        else:
            raise ValueError(f"Invalid chat state: {chat.state}")

        await ws.send_json(
            {
                "type": "sync-chat",
                "chat": json.loads(ChatApi.from_data(chat).model_dump_json()),
            }
        )

        objective_prompt = None

        if chat.state == "react":
            objective_prompt = (
                (
                    generate_suggestions.objective_misunderstand_reaction_prompt(
                        objective, chat.current_problem
                    )
                )
                if objective
                else None
            )

        response = await message_generation.generate_message(
            user=user,
            user_sent=False,
            agent_name=chat.agent,
            messages=chat.messages,
            objective_prompt=objective_prompt,
        )

        msg = ChatMessage(
            sender=chat.agent,
            content=response,
            created_at=datetime.now(timezone.utc),
        )
        chat.messages.append(msg)
        chat.last_updated = datetime.now(timezone.utc)
        chat.agent_typing = False
        chat.unread = True
        chat.loading_feedback = chat.state == "react" and objective is not None

        chat.events.append(
            ChatEvent(
                name="recv-message",
                data={
                    "message": msg.content,
                },
                created_at=datetime.now(timezone.utc),
            )
        )

        await update_chat(chat)

        await ws.send_json(
            {
                "type": "sync-chat",
                "chat": json.loads(ChatApi.from_data(chat).model_dump_json()),
            }
        )

        if chat.state == "react" and objective:
            chat.loading_feedback = True

            await update_chat(chat)

            await ws.send_json(
                {
                    "type": "sync-chat",
                    "chat": json.loads(ChatApi.from_data(chat).model_dump_json()),
                }
            )

            feedback = await generate_suggestions.explain_suggestion(
                user,
                chat.agent,
                objective,
                chat.current_problem,
                message_generation.format_messages_context_short(
                    chat.messages, chat.agent
                ),
            )

            chat.messages.append(
                InChatFeedback(feedback=feedback, created_at=datetime.now(timezone.utc))
            )
            chat.loading_feedback = False

            chat.events.append(
                ChatEvent(
                    name="recv-feedback",
                    data={
                        "feedback": feedback,
                    },
                    created_at=datetime.now(timezone.utc),
                )
            )

            chat.generating_suggestions = True

            await update_chat(chat)

            await ws.send_json(
                {
                    "type": "sync-chat",
                    "chat": json.loads(ChatApi.from_data(chat).model_dump_json()),
                }
            )

            follow_up = await message_generation.generate_message(
                user=user,
                user_sent=True,
                agent_name=chat.agent,
                messages=chat.messages,
                objective_prompt=generate_suggestions.objective_misunderstand_follow_up_prompt(
                    objective, chat.current_problem
                ),
            )

            explanation = await generate_suggestions.explain_suggestion(
                user, chat.agent, objective, None, follow_up
            )

            suggestions = [
                Suggestion(
                    message=follow_up,
                    feedback=explanation,
                    objective=objective,
                    problem=None,
                )
            ]

            chat.suggestions = suggestions
            chat.generating_suggestions = False

            chat.events.append(
                ChatEvent(
                    name="suggested-messages",
                    data={
                        "suggestions": suggestion_list_adapter.dump_python(suggestions),
                    },
                    created_at=datetime.now(timezone.utc),
                )
            )

            await update_chat(chat)

    while event := await ws.receive_json():
        if event["type"] == "create-chat":
            chat = await create_chat(user)
            await ws.send_json(
                {
                    "type": "sync-chat",
                    "chat": json.loads(ChatApi.from_data(chat).model_dump_json()),
                }
            )

        elif event["type"] == "load-chat":
            chat = await get_chat(ObjectId(event["id"]), user)

            if not chat:
                await ws.send_json({"error": "Chat not found"})
                continue

            await ws.send_json(
                {
                    "type": "sync-chat",
                    "chat": json.loads(ChatApi.from_data(chat).model_dump_json()),
                }
            )
        elif event["type"] == "suggest-messages":
            chat = await get_chat(ObjectId(event["id"]), user)

            if not chat:
                await ws.send_json({"error": "Chat not found"})
                continue

            chat.events.append(
                ChatEvent(
                    name="suggest-messages",
                    data={
                        "input": event["message"],
                    },
                    created_at=datetime.now(timezone.utc),
                )
            )
            chat.generating_suggestions = True

            context = message_generation.format_messages_context_short(
                chat.messages, chat.agent
            )

            objective = None

            message = (
                event["message"]
                if user.options.suggestion_generation == "content-inspired"
                else await message_generation.generate_message(
                    user, chat.agent, True, chat.messages
                )
            )

            if chat.state == "no-objective" or chat.state == "react":
                suggestions = await generate_suggestions.generate_message_variations_ok(
                    context, message
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
                    message,
                    user.options.feedback_mode == "on-suggestion",
                )

                chat.objectives_used.append(objective)
            else:
                raise ValueError(f"Invalid chat state: {chat.state}")

            chat.suggestions = suggestions
            chat.generating_suggestions = False

            chat.events.append(
                ChatEvent(
                    name="suggested-messages",
                    data={
                        "suggestions": suggestion_list_adapter.dump_python(suggestions),
                        "objective": objective,
                    },
                    created_at=datetime.now(timezone.utc),
                )
            )

            await update_chat(chat)

            await ws.send_json(
                {
                    "type": "suggested-messages",
                    "messages": suggestion_list_adapter.dump_python(chat.suggestions),
                    "id": event["id"],
                }
            )
        elif event["type"] == "send-message":
            chat = await get_chat(ObjectId(event["id"]), user)

            if not chat:
                await ws.send_json({"error": "Chat not found"})
                continue

            if not chat.suggestions:
                await ws.send_json({"error": "No suggestions available"})
                continue

            index: int = event["index"]
            suggestion = chat.suggestions[index]

            chat.events.append(
                ChatEvent(
                    name="send-message",
                    data={
                        "index": index,
                        "message": suggestion.message,
                    },
                    created_at=datetime.now(timezone.utc),
                )
            )

            msg = ChatMessage(
                sender=user.name,
                content=suggestion.message,
                created_at=datetime.now(timezone.utc),
            )
            chat.messages.append(msg)
            chat.last_updated = datetime.now(timezone.utc)
            chat.suggestions = None

            await update_chat(chat)

            await generate_agent_message(chat, suggestion.objective)
        elif event["type"] == "mark-read":
            chat = await get_chat(ObjectId(event["id"]), user)

            if not chat:
                await ws.send_json({"error": "Chat not found"})
                continue

            chat.unread = False

            chat.events.append(
                ChatEvent(
                    name="mark-read",
                    data=None,
                    created_at=datetime.now(timezone.utc),
                )
            )

            await update_chat(chat)

            await ws.send_json(
                {
                    "type": "sync-chat",
                    "chat": json.loads(ChatApi.from_data(chat).model_dump_json()),
                }
            )
        elif event["type"] == "view-suggestion":
            chat = await get_chat(ObjectId(event["id"]), user)

            if not chat:
                await ws.send_json({"error": "Chat not found"})
                continue

            if not chat.suggestions:
                await ws.send_json({"error": "No suggestions available"})
                continue

            index: int = event["index"]
            suggestion = chat.suggestions[index]

            chat.events.append(
                ChatEvent(
                    name="view-suggestion",
                    data={
                        "index": index,
                    },
                    created_at=datetime.now(timezone.utc),
                )
            )

            await update_chat(chat)
        else:
            await ws.send_json({"error": "Invalid event type"})
