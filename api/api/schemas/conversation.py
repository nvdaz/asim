from typing import Literal, Union

from pydantic import BaseModel, ConfigDict, Field, RootModel, StringConstraints
from typing_extensions import Annotated

from api.services.flow_state.base import FlowStateRef

from .objectid import PyObjectId
from .persona import Persona


class Message(BaseModel):
    sender: str
    message: str


class Feedback(BaseModel):
    title: Annotated[str, StringConstraints(max_length=50)]
    body: Annotated[str, StringConstraints(max_length=600)]
    follow_up: str | None = None


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


class ConversationWaitingInternal(BaseModel):
    waiting: Literal[True] = True
    options: list[MessageOption]


class ConversationNormalInternal(BaseModel):
    waiting: Literal[False] = False
    state: FlowStateRef


class ConversationWaiting(BaseModel):
    waiting: Literal[True] = True
    options: list[str]


class ConversationNormal(BaseModel):
    waiting: Literal[False] = False
    type: Literal["ap", "np", "feedback"]


class ConversationScenario(BaseModel):
    user_scenario: str
    subject_scenario: str
    user_goal: str
    is_user_initiated: bool


class ConversationInfo(BaseModel):
    scenario: ConversationScenario
    user: Persona
    subject: Persona


class NpMessageOptionsLogEntry(BaseModel):
    type: Literal["np_options"] = "np_options"
    state: str
    options: list[MessageOption]


class NpMessageSelectedLogEntry(BaseModel):
    type: Literal["np_selected"] = "np_selected"
    message: str


class ApMessageLogEntry(BaseModel):
    type: Literal["ap"] = "ap"
    state: str
    message: str


class FeedbackLogEntry(BaseModel):
    type: Literal["feedback"] = "feedback"
    state: str
    content: Feedback


class ConversationLogEntry(RootModel):
    root: Annotated[
        Union[
            NpMessageOptionsLogEntry,
            NpMessageSelectedLogEntry,
            ApMessageLogEntry,
            FeedbackLogEntry,
        ],
        Field(discriminator="type"),
    ]


class BaseConversationData(BaseModel):
    user_id: PyObjectId
    level: int
    info: ConversationInfo
    state: Annotated[
        Union[ConversationWaitingInternal, ConversationNormalInternal],
        Field(discriminator="waiting"),
    ]
    events: list[ConversationLogEntry]
    messages: Messages
    last_feedback_received: int

    model_config = ConfigDict(populate_by_name=True)


class ConversationData(BaseConversationData):
    id: Annotated[PyObjectId, Field(alias="_id")]


class ConversationDescriptorData(BaseModel):
    id: Annotated[PyObjectId, Field(alias="_id")]
    level: int
    info: ConversationInfo


class ConversationDescriptor(BaseModel):
    id: PyObjectId
    level: int
    subject_name: str

    @staticmethod
    def from_data(data: ConversationDescriptorData):
        return ConversationDescriptor(
            id=data.id,
            level=data.level,
            subject_name=data.info.subject.name,
        )


class Conversation(BaseModel):
    id: PyObjectId
    level: int
    scenario: ConversationScenario
    state: Annotated[
        Union[ConversationWaiting, ConversationNormal],
        Field(discriminator="waiting"),
    ]
    subject_name: str
    messages: Messages

    @staticmethod
    def from_data(data: ConversationData):
        state = (
            ConversationWaiting(options=[o.response for o in data.state.options])
            if data.state.waiting
            else ConversationNormal(type=data.state.state.root.type)
        )

        return Conversation(
            id=data.id,
            level=data.level,
            scenario=data.info.scenario,
            state=state,
            subject_name=data.info.subject.name,
            messages=data.messages,
        )
