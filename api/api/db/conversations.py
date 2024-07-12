from bson import ObjectId

from api.schemas.conversation import (
    BaseConversationUninitData,
    ConversationData,
    ConversationDescriptorData,
    ConversationUninitData,
)

from .client import db

conversations = db.conversations


async def get(conversation_id: ObjectId, user_id: ObjectId) -> ConversationData:
    conversation = await conversations.find_one(
        {"_id": conversation_id, "user_id": user_id}
    )
    return ConversationData(**conversation) if conversation else None


async def insert(conversation: BaseConversationUninitData) -> ConversationUninitData:
    res = await conversations.insert_one(conversation.model_dump())

    return ConversationData(
        id=res.inserted_id,
        **conversation.model_dump(),
    )


async def update(conversation: ConversationData):
    await conversations.update_one(
        {
            "_id": conversation.root.id,
            "user_id": conversation.root.user_id,
        },
        {"$set": conversation.model_dump(exclude={"id"})},
    )


async def list(
    user_id: ObjectId, level: int | None = None
) -> list[ConversationDescriptorData]:
    cursor = conversations.find(
        {"user_id": user_id, "level": level} if level else {"user_id": user_id},
        {"_id": 1, "level": 1, "info": 1},
    )
    return [ConversationDescriptorData(**conversation) async for conversation in cursor]


async def get_previous_scenarios(user_id: ObjectId):
    cursor = conversations.find(
        {"user_id": user_id},
        {"info.scenario.user_perspective": 1},
    )
    return [
        conversation["info"]["scenario"]["user_perspective"]
        async for conversation in cursor
    ]
