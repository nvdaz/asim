from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, RootModel
from pydantic.fields import Field
from typing_extensions import Annotated

from .objectid import PyObjectId
from .persona import Persona, PersonaUninit


class BaseUser(BaseModel):
    qa_id: UUID

    model_config = ConfigDict(populate_by_name=True)


class BaseUserUninit(BaseUser):
    init: Literal[False] = False
    persona: PersonaUninit


class BaseUserInit(BaseUser):
    init: Literal[True] = True
    name: str
    persona: Persona


class UserUninit(BaseUserUninit):
    id: Annotated[PyObjectId, Field(alias="_id")]


class UserInit(BaseUserInit):
    id: Annotated[PyObjectId, Field(alias="_id")]


class User(RootModel):
    root: Annotated[UserUninit | UserInit, Field(discriminator="init")]
