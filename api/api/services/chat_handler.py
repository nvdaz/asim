import asyncio
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
    ChatInfo,
    ChatMessage,
    chat_info_list_adapter,
)
from api.schemas.user import UserData
from api.services import message_generation
from api.services.memory_store import ConversationMemoryModule, MemoryStore

fake = faker.Faker()

user_memory_store = MemoryStore([])


async def create_chat(
    user: UserData,
) -> tuple[ChatData, MemoryStore]:
    name = fake.first_name()

    memory_store = MemoryStore([])

    base_memories = [
        f"{name} is a student at MIT studying mathematics.",
        f"{name} is taking a course in topology.",
        f"{name} spends his free time rock climbing and running.",
        f"{name} is from New York City.",
        f"{name} received a B on his last topology exam, despite studying for weeks.",
        f"{name} is currently training for a marathon.",
        f"{name} last went rock climbing at the MIT rock climbing gym with the team.",
        f"{user.persona.name} is a friend of {name}'s who is a student at Tufts.",
        f"{user.persona.name} studies computer science and works with LLMs.",
    ]

    await asyncio.gather(
        *[memory_store.remember(memory, 0) for memory in base_memories]
    )

    chat = BaseChat(
        user_id=user.id,
        agent=name,
        last_updated=datetime.now(timezone.utc),
        agent_memories=memory_store.to_data(),
    )

    return await chats.create(chat), memory_store


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
        agent_memory_store: MemoryStore,
        extra_observation: str = "",
    ):
        chat.agent_typing = True
        await ws.send_json(
            {
                "type": "sync-chat",
                "chat": json.loads(ChatApi.from_data(chat).model_dump_json()),
            }
        )
        response = await message_generation.generate_message(
            user=user,
            user_sent=False,
            agent_name=chat.agent,
            agent_memory_store=agent_memory_store,
            user_memory_store=user_memory_store,
            messages=chat.messages,
            extra_observation=extra_observation,
        )

        new_memories = await ConversationMemoryModule(
            agent_memory_store
        ).generate_memory_on_message(f"{chat.agent}: {response}", chat.agent)

        await asyncio.gather(
            *[agent_memory_store.remember(memory, 0) for memory in new_memories]
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
        chat.agent_memories = agent_memory_store.to_data()

        await update_chat(chat)

        await ws.send_json(
            {
                "type": "sync-chat",
                "chat": json.loads(ChatApi.from_data(chat).model_dump_json()),
            }
        )

    async def ev_loop():
        while True:
            new_chats = await chats.check_for_new_chats(user.id)

            for chat in new_chats:
                await generate_agent_message(
                    chat, MemoryStore.from_data(chat.agent_memories)
                )

            stale_chats = await chats.check_for_stale_chats(user.id)

            for chat in stale_chats:
                await generate_agent_message(
                    chat,
                    MemoryStore.from_data(chat.agent_memories),
                    extra_observation="Mention that the other person hasn't responded "
                    "in a while and try to re-engage the conversation.",
                )

            await asyncio.sleep(5)

    async def listen_for_events():
        while event := await ws.receive_json():
            if event["type"] == "create-chat":
                chat, _ = await create_chat(user)
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
            elif event["type"] == "send-message":
                chat = await get_chat(ObjectId(event["id"]), user)

                if not chat:
                    await ws.send_json({"error": "Chat not found"})
                    continue

                msg = ChatMessage(
                    sender=user.persona.name or "",
                    content=event["content"],
                    created_at=datetime.now(timezone.utc),
                )
                chat.messages.append(msg)
                chat.last_updated = datetime.now(timezone.utc)

                agent_memory_store = MemoryStore.from_data(chat.agent_memories)

                new_memories = await ConversationMemoryModule(
                    agent_memory_store
                ).generate_memory_on_message(
                    f'{user.persona.name}: {event["content"]}', chat.agent
                )

                await asyncio.gather(
                    *[agent_memory_store.remember(memory, 0) for memory in new_memories]
                )

                chat.agent_memories = agent_memory_store.to_data()

                await update_chat(chat)

                should_message = True
                while should_message:
                    await generate_agent_message(chat, agent_memory_store)

                    should_message = await message_generation.decide_whether_to_message(
                        chat.agent, chat.messages
                    )
            elif event["type"] == "suggest-messages":
                chat = await get_chat(ObjectId(event["id"]), user)

                if not chat:
                    await ws.send_json({"error": "Chat not found"})
                    continue

                agent_memory_store = MemoryStore.from_data(chat.agent_memories)

                responses = await asyncio.gather(
                    *[
                        message_generation.generate_message(
                            user=user,
                            agent_name=chat.agent,
                            user_memory_store=user_memory_store,
                            agent_memory_store=agent_memory_store,
                            user_sent=True,
                            messages=chat.messages,
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
                        "chat": json.loads(ChatApi.from_data(chat).model_dump_json()),
                    }
                )
            else:
                await ws.send_json({"error": "Invalid event type"})

    await asyncio.gather(ev_loop(), listen_for_events())
