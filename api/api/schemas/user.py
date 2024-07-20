from typing import Annotated, Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, TypeAdapter
from pydantic.fields import Field

from .objectid import PyObjectId
from .persona import Persona, PersonaUninit


class BaseUserData(BaseModel):
    qa_id: UUID


class BaseUserUninitData(BaseUserData):
    init: Literal[False] = False
    persona: PersonaUninit


class BaseUserInitData(BaseUserData):
    init: Literal[True] = True
    name: str
    persona: Persona
    sent_message_counts: dict[str, int] = {}
    max_unlocked_stage: str = "level-0"


class UserUninitData(BaseUserUninitData):
    id: Annotated[PyObjectId, Field(alias="_id")]

    model_config = ConfigDict(populate_by_name=True)


class UserInitData(BaseUserInitData):
    id: Annotated[PyObjectId, Field(alias="_id")]

    model_config = ConfigDict(populate_by_name=True)


UserData = Annotated[UserUninitData | UserInitData, Field(discriminator="init")]

user_data_adapter: TypeAdapter[UserData] = TypeAdapter(UserData)


class UserUninit(BaseModel):
    id: PyObjectId
    init: Literal[False] = False


class UserInit(BaseModel):
    id: PyObjectId
    init: Literal[True] = True
    name: str
    max_unlocked_stage: str


User = Annotated[UserInit | UserUninit, Field(discriminator="init")]


def user_from_data(data: UserData) -> User:
    return (
        UserInit(id=data.id, name=data.name, max_unlocked_stage=data.max_unlocked_stage)
        if data.init
        else UserUninit(id=data.id)
    )
