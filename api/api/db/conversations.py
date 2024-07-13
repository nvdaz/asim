from bson import ObjectId

from api.schemas.conversation import (
    BaseConversationUninitData,
    ConversationData,
    ConversationUninitData,
    LevelConversationData,
    LevelConversationDescriptorData,
    conversation_data_adapter,
    conversation_uninit_data_adapter,
)

from .client import db

conversations = db.conversations


async def get(conversation_id: ObjectId, user_id: ObjectId) -> ConversationData:
    conversation = await conversations.find_one(
        {"_id": conversation_id, "user_id": user_id}
    )

    return (
        conversation_data_adapter.validate_python(conversation)
        if conversation
        else None
    )


async def insert(
    conversation: BaseConversationUninitData,
) -> ConversationUninitData:
    res = await conversations.insert_one(conversation.model_dump())

    return conversation_uninit_data_adapter.validate_python(
        {"_id": res.inserted_id, **conversation.model_dump()}
    )


async def update(conversation: LevelConversationData):
    await conversations.update_one(
        {
            "_id": conversation.id,
            "user_id": conversation.user_id,
        },
        {"$set": conversation.model_dump(exclude={"id"})},
    )


async def list(
    user_id: ObjectId, level: int | None = None
) -> list[LevelConversationDescriptorData]:
    cursor = conversations.find(
        {"user_id": user_id, "level": level} if level else {"user_id": user_id},
        {"_id": 1, "level": 1, "info": 1},
    )
    return [
        LevelConversationDescriptorData(**conversation) async for conversation in cursor
    ]


async def get_previous_level_scenarios(user_id: ObjectId):
    return []  # TODO: implement
    # cursor = conversations.find(
    #     {"user_id": user_id, "type": "level"},
    #     {"info.scenario.user_perspective": 1},
    # )

    # return [
    #     conversation["info"]["scenario"]["user_perspective"]
    #     async for conversation in cursor
    # ]
