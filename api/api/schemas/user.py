from typing import Annotated
from uuid import UUID

from pydantic import BaseModel, ConfigDict
from pydantic.fields import Field

from .objectid import PyObjectId
from .persona import Persona


class BaseUserData(BaseModel):
    init: bool = False
    qa_id: UUID
    name: str | None = None
    persona: Persona
    sent_message_counts: dict[str, int] = {}
    max_unlocked_stage: str = "level-0"


class UserData(BaseUserData):
    id: Annotated[PyObjectId, Field(alias="_id")]

    model_config = ConfigDict(populate_by_name=True)


class User(BaseModel):
    id: PyObjectId
    name: str | None
    max_unlocked_stage: str


def user_from_data(data: UserData) -> User:
    return User(id=data.id, name=data.name, max_unlocked_stage=data.max_unlocked_stage)
