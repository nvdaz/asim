from pydantic import BaseModel, ConfigDict

from api.schemas.objectid import PyObjectId

from .client import db


class AuthToken(BaseModel):
    secret: str
    user_id: PyObjectId

    model_config = ConfigDict(populate_by_name=True)


auth_tokens = db.auth_tokens


async def create(auth_token: AuthToken):
    await auth_tokens.insert_one(auth_token.model_dump())


async def get(secret: str):
    auth_token = await auth_tokens.find_one({"secret": secret})
    return AuthToken(**auth_token) if auth_token else None
