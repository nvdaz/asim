from typing import Literal, overload

from bson import ObjectId

from api.schemas.conversation import (
    BaseConversationUninit,
    ConversationData,
    ConversationDataUninit,
    ConversationDescriptorData,
    ConversationInfo,
    ConversationOptions,
    LevelConversationInfo,
    LevelConversationOptions,
    PlaygroundConversationInfo,
    PlaygroundConversationOptions,
    conversation_data_adapter,
    conversation_info_adapter,
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
    conversation: BaseConversationUninit,
) -> ConversationDataUninit:
    res = await conversations.insert_one(conversation.model_dump())

    return conversation_data_adapter.validate_python(
        {"_id": res.inserted_id, **conversation.model_dump()}
    )


async def update(conversation: ConversationData):
    await conversations.update_one(
        {
            "_id": conversation.id,
            "user_id": conversation.user_id,
        },
        {"$set": conversation.model_dump(exclude={"id"})},
    )


async def query(user_id: ObjectId, options: ConversationOptions):
    match options:
        case LevelConversationOptions(level=level):
            query = {"user_id": user_id, "info.type": "level", "info.level": level}
        case PlaygroundConversationOptions():
            query = {"user_id": user_id, "info.type": "playground"}

    cursor = conversations.find(query, {"_id": 1, "info": 1, "agent": 1})
    return [ConversationDescriptorData(**conversation) async for conversation in cursor]


@overload
async def get_previous_info(
    user_id: ObjectId, type: Literal["level"]
) -> list[LevelConversationInfo]: ...


@overload
async def get_previous_info(
    user_id: ObjectId, type: Literal["playground"]
) -> list[PlaygroundConversationInfo]: ...


async def get_previous_info(
    user_id: ObjectId, type: Literal["level", "playground"]
) -> list[ConversationInfo]:
    cursor = conversations.find(
        {"user_id": user_id, "info.type": type},
        {"info": 1},
    )

    return [
        conversation_info_adapter.validate_python(conversation["info"])
        async for conversation in cursor
    ]
