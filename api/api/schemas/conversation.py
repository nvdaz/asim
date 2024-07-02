from typing import Literal, Union

from pydantic import BaseModel, Field, RootModel
from typing_extensions import Annotated

from api.services.flow_state.base import FlowStateRef

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


class ConversationData(BaseModel):
    id: str
    level: int
    info: ConversationInfo
    state: Annotated[
        Union[ConversationWaiting, ConversationNormal],
        Field(discriminator="waiting"),
    ]
    messages: Messages
    last_feedback_received: int
