from uuid import UUID

from api.schemas.user import User

from .client import db

users = db.users


async def get(user_id: UUID):
    user = await users.find_one({"user_id": user_id})
    return User(**user) if user else None


async def upsert(user: User):
    return await users.update_one(
        {"user_id": user.user_id}, {"$set": user.model_dump()}, upsert=True
    )
