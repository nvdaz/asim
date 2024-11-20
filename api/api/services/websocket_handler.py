import asyncio
import json

from bson import ObjectId
from fastapi import WebSocket

from api.schemas.chat import ChatApi, chat_info_list_adapter
from api.schemas.user import UserData
from api.services import chat_service
from api.services.connection_manager import ConnectionManager


async def handle_connection(
    ws: WebSocket, connection: ConnectionManager, connection_id: str, user: UserData
):
    all_chats = await chat_service.get_chats(user.id)

    await ws.send_json(
        {
            "type": "sync-chats",
            "chats": json.loads(chat_info_list_adapter.dump_json(all_chats)),
        }
    )

    async def get_chat_state(id: ObjectId) -> chat_service.ChatState:
        if chat_state := connection.get_state(id):
            return chat_state

        chat = await chat_service.get_chat(id, user.id)
        assert chat
        chat_state = chat_service.ChatState(chat)
        connection.add_state(chat_state)
        return chat_state

    def on_change(chat_state: chat_service.ChatState):
        def on_change_inner():
            return ws.send_json(
                {
                    "type": "sync-chat",
                    "chat": json.loads(
                        ChatApi.from_data(chat_state.read()).model_dump_json()
                    ),
                }
            )

        asyncio.create_task(on_change_inner())

    connection.add_listener(connection_id, on_change)

    while event := await ws.receive_json():
        if event["type"] == "create-chat":
            chat = await chat_service.create_chat(user)
            await ws.send_json(
                {
                    "type": "sync-chat",
                    "chat": json.loads(ChatApi.from_data(chat).model_dump_json()),
                }
            )
        elif event["type"] == "load-chat":
            chat = await get_chat_state(ObjectId(event["id"]))

            await ws.send_json(
                {
                    "type": "sync-chat",
                    "chat": json.loads(
                        ChatApi.from_data(chat.read()).model_dump_json()
                    ),
                }
            )
        elif event["type"] == "suggest-messages":
            chat_state = await get_chat_state(ObjectId(event["id"]))
            connection.add_action(
                chat_state,
                chat_service.suggest_messages(chat_state, user, event["message"]),
            )

        elif event["type"] == "send-message":
            chat_state = await get_chat_state(ObjectId(event["id"]))

            async def send_message_inner(chat_state):
                objective = await chat_service.send_message(
                    chat_state, user, event["index"]
                )
                await chat_service.generate_agent_message(chat_state, user, objective)

            connection.add_action(chat_state, send_message_inner(chat_state))

        elif event["type"] == "mark-read":
            chat_state = await get_chat_state(ObjectId(event["id"]))

            connection.add_action(chat_state, chat_service.mark_read(chat_state))
        elif event["type"] == "rate-feedback":
            chat_state = await get_chat_state(ObjectId(event["id"]))
            connection.add_action(
                chat_state,
                chat_service.rate_feedback(chat_state, event["index"], event["rating"]),
            )
        elif event["type"] == "view-suggestion":
            chat_state = await get_chat_state(ObjectId(event["id"]))
            connection.add_action(
                chat_state,
                chat_service.mark_view_suggestion(chat_state, event["index"]),
            )
        elif event["type"] == "checkpoint-rating":
            chat_state = await get_chat_state(ObjectId(event["id"]))
            connection.add_action(
                chat_state, chat_service.checkpoint_rating(chat_state, event["ratings"])
            )
        else:
            raise ValueError(f"Unknown event type: {event['type']}")
