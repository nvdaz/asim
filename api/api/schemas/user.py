from typing import Annotated

from pydantic import BaseModel, ConfigDict
from pydantic.fields import Field

from api.schemas.chat import Options

from .objectid import PyObjectId


class UserPersonalizationOptions(BaseModel):
    name: str
    pronouns: str
    topic: str


class BaseUserData(BaseModel):
    name: str | None = None
    init_chats: list[Options] = []
    personalization: UserPersonalizationOptions | None = None


class UserData(BaseUserData):
    id: Annotated[PyObjectId, Field(alias="_id")]

    model_config = ConfigDict(populate_by_name=True)


class User(BaseUserData):
    id: PyObjectId


def user_from_data(data: UserData) -> User:
    return User(
        id=data.id,
        name=data.name,
        init_chats=data.init_chats,
    )
