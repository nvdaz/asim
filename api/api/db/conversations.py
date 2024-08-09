from typing import Any, Literal, overload

from bson import ObjectId

from api.schemas.conversation import (
    BaseConversation,
    ConversationData,
    ConversationDescriptorData,
    ConversationStage,
    LevelConversationScenario,
    LevelConversationStage,
    PlaygroundConversationScenario,
    PlaygroundConversationStage,
    conversation_info_adapter,
)

from .client import db

conversations = db.conversations


async def get(conversation_id: ObjectId, user_id: ObjectId) -> ConversationData | None:
    conversation = await conversations.find_one(
        {"_id": conversation_id, "user_id": user_id}
    )

    return ConversationData(**conversation) if conversation else None


async def insert(
    conversation: BaseConversation,
) -> ConversationData:
    res = await conversations.insert_one(conversation.model_dump())

    return ConversationData(id=res.inserted_id, **conversation.model_dump())


async def update(conversation: ConversationData):
    await conversations.update_one(
        {
            "_id": conversation.id,
            "user_id": conversation.user_id,
        },
        {"$set": conversation.model_dump(exclude={"id"})},
    )


async def query(user_id: ObjectId, stage: ConversationStage):
    match stage:
        case LevelConversationStage(level=level):
            query = {
                "user_id": user_id,
                "info.type": "level",
                "info.level": level,
            }
        case PlaygroundConversationStage():
            query = {"user_id": user_id, "info.type": "playground"}
        case _:
            raise ValueError("Invalid stage")

    cursor = conversations.find(query, {"_id": 1, "info": 1, "agent": 1})
    return [ConversationDescriptorData(**conversation) async for conversation in cursor]


async def query_one(
    user_id: ObjectId, stage: ConversationStage
) -> ConversationData | None:
    match stage:
        case LevelConversationStage(level=level):
            query = {
                "user_id": user_id,
                "info.type": "level",
                "info.level": level,
            }
        case PlaygroundConversationStage():
            query = {"user_id": user_id, "info.type": "playground"}
        case _:
            raise ValueError("Invalid stage")

    conversation = await conversations.find_one(query)

    return ConversationData(**conversation) if conversation else None


@overload
async def get_previous_info(
    user_id: ObjectId, type: Literal["level"]
) -> list[LevelConversationScenario]: ...


@overload
async def get_previous_info(
    user_id: ObjectId, type: Literal["playground"]
) -> list[PlaygroundConversationScenario]: ...


async def get_previous_info(
    user_id: ObjectId, type: Literal["level", "playground"]
) -> Any:
    cursor = conversations.find(
        {"user_id": user_id, "scenario.type": type},
        {"scenario": 1},
    )

    return [
        conversation_info_adapter.validate_python(conversation["stage"])
        async for conversation in cursor
    ]
