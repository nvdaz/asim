from uuid import UUID

from bson import ObjectId

from api.schemas.conversation import BaseConversationData, ConversationData

from .client import db

conversations = db.conversations


async def get(conversation_id: str, user_id: UUID) -> ConversationData:
    conversation = await conversations.find_one(
        {"_id": ObjectId(conversation_id), "user_id": user_id}
    )
    return ConversationData(**conversation) if conversation else None


async def insert(conversation: BaseConversationData) -> ConversationData:
    res = await conversations.insert_one(conversation.model_dump())

    id = str(res.inserted_id)

    data = ConversationData(
        _id=id,
        **conversation.model_dump(),
    )

    return data


async def update(conversation: ConversationData):
    await conversations.update_one(
        {
            "_id": ObjectId(conversation.id),
            "user_id": conversation.user_id,
        },
        {"$set": conversation.model_dump()},
    )
