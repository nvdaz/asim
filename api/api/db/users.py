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
