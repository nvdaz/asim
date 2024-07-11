from uuid import UUID

from bson import ObjectId

from api.schemas.user import BaseUserUninit, User

from .client import db

users = db.users


async def get(id: ObjectId):
    user = await users.find_one({"_id": id})
    return User(**user) if user else None


async def get_by_qa_id(qa_id: UUID):
    user = await users.find_one({"qa_id": qa_id})
    return User(**user) if user else None


async def create(user: BaseUserUninit) -> User:
    res = await users.insert_one(user.model_dump())

    return User(id=res.inserted_id, **user.model_dump())


async def update(user_id: ObjectId, user: User):
    raw_user = await users.find_one_and_update(
        {"_id": user_id}, {"$set": user.model_dump()}, return_document=True
    )

    return User(**raw_user)
