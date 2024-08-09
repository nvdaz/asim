from typing import Annotated
from uuid import UUID

from pydantic import BaseModel, ConfigDict
from pydantic.fields import Field

from api.schemas.conversation import (
    ConversationStage,
    ConversationStageStr,
    LevelConversationStage,
)

from .objectid import PyObjectId
from .persona import UserPersona


class BaseUserData(BaseModel):
    init: bool = False
    qa_id: UUID
    persona: UserPersona
    sent_message_counts: dict[str, int] = {}
    max_unlocked_stage: ConversationStage = LevelConversationStage(level=1, part=1)


class UserData(BaseUserData):
    id: Annotated[PyObjectId, Field(alias="_id")]

    model_config = ConfigDict(populate_by_name=True)


class User(BaseModel):
    id: PyObjectId
    init: bool
    name: str | None
    max_unlocked_stage: ConversationStageStr


def user_from_data(data: UserData) -> User:
    return User(
        id=data.id,
        init=data.init,
        name=data.persona.name,
        max_unlocked_stage=str(data.max_unlocked_stage),
    )
