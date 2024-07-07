from typing import Literal, Union
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, RootModel
from typing_extensions import Annotated

from api.services.flow_state.base import FlowStateRef

from .objectid import ObjectIdField
from .persona import Persona


class Message(BaseModel):
    sender: str
    message: str


class Messages(RootModel):
    root: list[Message]

    def __getitem__(self, index: Union[int, slice]):
        if isinstance(index, slice):
            return Messages(root=self.root[index])
        else:
            return self.root[index]


class MessageOption(BaseModel):
    response: str
    next: FlowStateRef


class ConversationWaiting(BaseModel):
    waiting: Literal[True] = True
    options: list[MessageOption]


class ConversationNormal(BaseModel):
    waiting: Literal[False] = False
    state: FlowStateRef


class ConversationScenario(BaseModel):
    user_scenario: str
    subject_scenario: str
    user_goal: str
    is_user_initiated: bool


class ConversationInfo(BaseModel):
    scenario: ConversationScenario
    user: Persona
    subject: Persona


class BaseConversationData(BaseModel):
    user_id: UUID
    level: int
    info: ConversationInfo
    state: Annotated[
        Union[ConversationWaiting, ConversationNormal],
        Field(discriminator="waiting"),
    ]
    messages: Messages
    last_feedback_received: int


class ConversationData(BaseConversationData):
    id: Annotated[str, Field(alias="_id"), ObjectIdField()]

    model_config = ConfigDict(populate_by_name=True)
