from uuid import UUID

from bson import ObjectId

from api.schemas.user import (
    BaseUserUninitData,
    UserData,
    UserUninitData,
    user_data_adapter,
)

from .client import db

users = db.users


async def get(id: ObjectId):
    user = await users.find_one({"_id": id})
    return user_data_adapter.validate_python(user) if user else None


async def get_by_qa_id(qa_id: UUID):
    user = await users.find_one({"qa_id": qa_id})
    return user_data_adapter.validate_python(user) if user else None


async def create(user: BaseUserUninitData) -> UserData:
    res = await users.insert_one(user.model_dump())

    return UserUninitData(id=res.inserted_id, **user.model_dump())


async def update(user_id: ObjectId, user: UserData):
    raw_user = await users.find_one_and_update(
        {"_id": user_id}, {"$set": user.model_dump()}, return_document=True
    )

    return user_data_adapter.validate_python(raw_user) if raw_user else None


async def increment_message_count(user_id: ObjectId, stage: str) -> dict[str, int]:
    res = await users.find_one_and_update(
        {"_id": user_id},
        {"$inc": {f"sent_message_counts.{stage}": 1}},
        {"sent_message_counts": 1},
        return_document=True,
    )

    return res["sent_message_counts"]

async def unlock_stage(user_id: ObjectId, stage: str) :
    await users.update_one(
        {"_id": user_id},
        {"$set": {"max_unlocked_stage": stage}}
    )
