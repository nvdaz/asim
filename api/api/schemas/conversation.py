from typing import Literal, Union

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    RootModel,
    StringConstraints,
    TypeAdapter,
)
from typing_extensions import Annotated

from api.services.flow_state.base import FlowStateRef

from .objectid import PyObjectId
from .persona import Persona


class Message(BaseModel):
    sender: str
    message: str


message_list_adapter = TypeAdapter(list[Message])


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
    user_perspective: str
    subject_perspective: str
    user_goal: str
    is_user_initiated: bool


class LevelConversationInfo(BaseModel):
    scenario: ConversationScenario
    user: Persona
    subject: Persona


class PlaygroundConversationInfo(BaseModel):
    topic: str
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


class LevelConversationInfoUninit(BaseModel):
    scenario: ConversationScenario


class BaseLevelConversationUninitData(BaseModel):
    init: Literal[False] = False
    type: Literal["level"] = "level"
    user_id: PyObjectId
    level: int
    subject_name: str
    info: LevelConversationInfoUninit
    user_persona: Persona


class BasePlaygroundConversationUninitData(BaseModel):
    init: Literal[False] = False
    type: Literal["playground"] = "playground"
    user_id: PyObjectId
    subject_name: str
    info: PlaygroundConversationInfo
    user_persona: Persona


BaseConversationUninitData = Annotated[
    BaseLevelConversationUninitData | BasePlaygroundConversationUninitData,
    Field(discriminator="type"),
]


class BaseLevelConversationInitData(BaseModel):
    init: Literal[True] = True
    type: Literal["level"] = "level"
    user_id: PyObjectId
    level: int
    info: LevelConversationInfo
    state: Annotated[
        Union[ConversationWaitingInternal, ConversationNormalInternal],
        Field(discriminator="waiting"),
    ]
    events: list[ConversationLogEntry]
    messages: list[Message]
    last_feedback_received: int


class BasePlaygroundConversationInitData(BaseModel):
    init: Literal[True] = True
    type: Literal["playground"] = "playground"
    user_id: PyObjectId
    info: PlaygroundConversationInfo
    level: int = 0
    state: Annotated[
        Union[ConversationWaitingInternal, ConversationNormalInternal],
        Field(discriminator="waiting"),
    ]
    events: list[ConversationLogEntry]
    messages: list[Message]
    last_feedback_received: int


class LevelConversationInitData(BaseLevelConversationInitData):
    id: Annotated[PyObjectId, Field(alias="_id")]

    model_config = ConfigDict(populate_by_name=True)


class LevelConversationUninitData(BaseLevelConversationUninitData):
    id: Annotated[PyObjectId, Field(alias="_id")]

    model_config = ConfigDict(populate_by_name=True)


class PlaygroundConversationInitData(BasePlaygroundConversationInitData):
    id: Annotated[PyObjectId, Field(alias="_id")]

    model_config = ConfigDict(populate_by_name=True)


class PlaygroundConversationUninitData(BasePlaygroundConversationUninitData):
    id: Annotated[PyObjectId, Field(alias="_id")]

    model_config = ConfigDict(populate_by_name=True)


ConversationUninitData = Annotated[
    LevelConversationUninitData | PlaygroundConversationUninitData,
    Field(discriminator="type"),
]

conversation_uninit_data_adapter = TypeAdapter(ConversationUninitData)


PlaygroundConversationData = Annotated[
    Union[PlaygroundConversationInitData, PlaygroundConversationUninitData],
    Field(discriminator="init"),
]


LevelConversationData = Annotated[
    Union[LevelConversationInitData, LevelConversationUninitData],
    Field(discriminator="init"),
]


class LevelConversationDescriptorData(BaseModel):
    id: Annotated[PyObjectId, Field(alias="_id")]
    level: int
    info: LevelConversationInfo


class LevelConversationDescriptor(BaseModel):
    id: PyObjectId
    level: int
    subject_name: str

    @staticmethod
    def from_data(data: LevelConversationDescriptorData):
        return LevelConversationDescriptor(
            id=data.id,
            level=data.level,
            subject_name=data.info.subject.name,
        )


class LevelConversationInit(BaseModel):
    id: PyObjectId
    type: Literal["level"] = "level"
    init: Literal[True] = True
    level: int
    scenario: ConversationScenario
    state: Annotated[
        Union[ConversationWaiting, ConversationNormal],
        Field(discriminator="waiting"),
    ]
    subject_name: str
    messages: Messages

    @staticmethod
    def from_data(data: LevelConversationInitData):
        state = (
            ConversationWaiting(options=[o.response for o in data.state.options])
            if data.state.waiting
            else ConversationNormal(type=data.state.state.root.type)
        )

        return LevelConversationInit(
            id=data.id,
            level=data.level,
            scenario=data.info.scenario,
            state=state,
            subject_name=data.info.subject.name,
            messages=data.messages,
        )


class LevelConversationUninit(BaseModel):
    id: PyObjectId
    type: Literal["level"] = "level"
    init: Literal[False] = False
    level: int
    scenario: ConversationScenario
    subject_name: str
    messages: Annotated[list[Message], Field(min_length=0, max_length=0)] = []

    @staticmethod
    def from_data(data: LevelConversationUninitData):
        return LevelConversationUninit(
            id=data.id,
            level=data.level,
            scenario=data.info.scenario,
            subject_name=data.subject_name,
        )


LevelConversation = Annotated[
    Union[LevelConversationInit, LevelConversationUninit],
    Field(discriminator="init"),
]


def level_conversation_from_data(data: LevelConversationData) -> LevelConversation:
    return (
        LevelConversationInit.from_data(data)
        if data.init
        else LevelConversationUninit.from_data(data)
    )


class PlaygroundConversationInit(BaseModel):
    id: PyObjectId
    type: Literal["playground"] = "playground"
    init: Literal[True] = True
    topic: str
    state: Annotated[
        Union[ConversationWaiting, ConversationNormal],
        Field(discriminator="waiting"),
    ]
    messages: Messages

    @staticmethod
    def from_data(data: PlaygroundConversationInitData):
        state = (
            ConversationWaiting(options=[o.response for o in data.state.options])
            if data.state.waiting
            else ConversationNormal(type=data.state.state.type)
        )

        return PlaygroundConversationInit(
            id=data.id,
            topic=data.info.topic,
            state=state,
            messages=data.messages,
        )


class PlaygroundConversationUninit(BaseModel):
    id: PyObjectId
    type: Literal["playground"] = "playground"
    init: Literal[False] = False
    topic: str
    messages: Annotated[list[Message], Field(min_length=0, max_length=0)] = []

    @staticmethod
    def from_data(data: PlaygroundConversationUninitData):
        return PlaygroundConversationUninit(
            id=data.id,
            topic=data.info.topic,
        )


PlaygroundConversation = Annotated[
    Union[PlaygroundConversationInit, PlaygroundConversationUninit],
    Field(discriminator="init"),
]


def playground_conversation_from_data(
    data: PlaygroundConversationData,
) -> PlaygroundConversation:
    return (
        PlaygroundConversationInit.from_data(data)
        if data.init
        else PlaygroundConversationUninit.from_data(data)
    )


ConversationData = Annotated[
    Union[LevelConversationData, PlaygroundConversationData],
    Field(discriminator="type"),
]

conversation_data_adapter = TypeAdapter(ConversationData)

Conversation = Annotated[
    Union[LevelConversation, PlaygroundConversation],
    Field(discriminator="type"),
]


def conversation_from_data(data: ConversationData) -> Conversation:
    return (
        level_conversation_from_data(data)
        if data.type == "level"
        else playground_conversation_from_data(data)
    )
