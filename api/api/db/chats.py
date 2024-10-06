from datetime import datetime, timedelta

from bson import ObjectId

from api.schemas.chat import BaseChat, ChatData, ChatInfoData

from .client import db

chats = db.chats


async def create(chat: BaseChat) -> ChatData:
    res = await chats.insert_one(chat.model_dump())

    return ChatData(id=res.inserted_id, **chat.model_dump())


async def get(id: ObjectId, user_id: ObjectId) -> ChatData | None:
    chat = await chats.find_one({"_id": id, "user_id": user_id})

    return ChatData(**chat) if chat else None


async def update_chat(chat: ChatData) -> ChatData:
    await chats.update_one(
        {"_id": chat.id}, {"$set": chat.model_dump(exclude=set("id"))}
    )

    return chat


async def get_chats(user_id: ObjectId) -> list[ChatInfoData]:
    cursor = chats.find({"user_id": user_id})

    return [ChatInfoData(**chat) async for chat in cursor]


async def check_for_new_chats(user_id: ObjectId):
    cursor = chats.find(
        {
            "user_id": user_id,
            "messages": {"$size": 0},
            "last_updated": {"$lt": datetime.now() - timedelta(seconds=5)},
        }
    )

    return [ChatData(**chat) async for chat in cursor]


async def check_for_stale_chats(user_id: ObjectId):
    cursor = chats.find(
        {
            "user_id": user_id,
            "last_updated": {"$lt": datetime.now() - timedelta(hours=12)},
        }
    )

    return [ChatData(**chat) async for chat in cursor]
