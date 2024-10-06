import asyncio
import json
from datetime import datetime

from bson import ObjectId
from fastapi import WebSocket

from api.db import chats
from api.schemas.chat import (
    BaseChat,
    Chat,
    ChatData,
    ChatInfo,
    ChatMessage,
    chat_info_list_adapter,
)
from api.schemas.user import UserData
from api.services import message_generation


async def create_chat(
    user: UserData,
) -> ChatData:
    chat = BaseChat(user_id=user.id, agent="Bob", last_updated=datetime.now())

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

    async def generate_agent_message(chat: ChatData):
        chat.agent_typing = True
        await ws.send_json(
            {
                "type": "sync-chat",
                "chat": json.loads(Chat.from_data(chat).model_dump_json()),
            }
        )
        response = await message_generation.generate_message(
            False,
            chat.messages,
        )

        msg = ChatMessage(sender="Bob", content=response, created_at=datetime.now())
        chat.messages.append(msg)
        chat.last_updated = datetime.now()
        chat.agent_typing = False
        chat.unread = True

        await update_chat(chat)

        await ws.send_json(
            {
                "type": "sync-chat",
                "chat": json.loads(Chat.from_data(chat).model_dump_json()),
            }
        )

    async def ev_loop():
        while True:
            new_chats = await chats.check_for_new_chats(user.id)

            for chat in new_chats:
                await generate_agent_message(chat)

            # stale_chats = await chats.check_for_stale_chats(user.id)

            await asyncio.sleep(5)

    async def listen_for_events():
        while event := await ws.receive_json():
            if event["type"] == "create-chat":
                chat = await create_chat(user)
                await ws.send_json(
                    {
                        "type": "sync-chat",
                        "chat": json.loads(Chat.from_data(chat).model_dump_json()),
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
                        "chat": json.loads(Chat.from_data(chat).model_dump_json()),
                    }
                )
            elif event["type"] == "send-message":
                chat = await get_chat(ObjectId(event["id"]), user)

                if not chat:
                    await ws.send_json({"error": "Chat not found"})
                    continue

                msg = ChatMessage(
                    sender=user.persona.name or "",
                    content=event["content"],
                    created_at=datetime.now(),
                )
                chat.messages.append(msg)
                chat.last_updated = datetime.now()
                await update_chat(chat)

                should_message = True
                while should_message:
                    await generate_agent_message(chat)

                    should_message = await message_generation.decide_whether_to_message(
                        "Bob", chat.messages
                    )
            elif event["type"] == "suggest-messages":
                chat = await get_chat(ObjectId(event["id"]), user)

                if not chat:
                    await ws.send_json({"error": "Chat not found"})
                    continue

                responses = await asyncio.gather(
                    *[
                        message_generation.generate_message(
                            True,
                            chat.messages,
                        )
                        for _ in range(3)
                    ]
                )

                await ws.send_json(
                    {
                        "type": "suggested-messages",
                        "messages": responses,
                        "id": event["id"],
                    }
                )
            elif event["type"] == "mark-read":
                chat = await get_chat(ObjectId(event["id"]), user)

                if not chat:
                    await ws.send_json({"error": "Chat not found"})
                    continue

                chat.unread = False
                await update_chat(chat)

                await ws.send_json(
                    {
                        "type": "sync-chat",
                        "chat": json.loads(Chat.from_data(chat).model_dump_json()),
                    }
                )
            else:
                await ws.send_json({"error": "Invalid event type"})

    await asyncio.gather(ev_loop(), listen_for_events())
