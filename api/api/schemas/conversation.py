from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, StringConstraints, TypeAdapter

from api.services.flow_state.base import FlowStateRef

from .objectid import PyObjectId
from .persona import Persona, PersonaName


class Feedback(BaseModel):
    title: Annotated[str, StringConstraints(max_length=50)]
    body: Annotated[str, StringConstraints(max_length=600)]
    follow_up: str | None = None


class Message(BaseModel):
    sender: str
    message: str


class MessageElement(BaseModel):
    type: Literal["message"] = "message"
    content: Message


class FeedbackElement(BaseModel):
    type: Literal["feedback"] = "feedback"
    content: Feedback


ConversationElement = Annotated[
    MessageElement | FeedbackElement,
    Field(discriminator="type"),
]


message_list_adapter = TypeAdapter(list[Message])


class MessageOption(BaseModel):
    response: str
    next: FlowStateRef


class ConversationScenario(BaseModel):
    user_perspective: str
    agent_perspective: str
    user_goal: str
    is_user_initiated: bool


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


ConversationLogEntry = Annotated[
    NpMessageOptionsLogEntry
    | NpMessageSelectedLogEntry
    | ApMessageLogEntry
    | FeedbackLogEntry,
    Field(discriminator="type"),
]


class LevelConversationOptions(BaseModel):
    type: Literal["level"] = "level"
    level: int


class PlaygroundConversationOptions(BaseModel):
    type: Literal["playground"] = "playground"


ConversationOptions = Annotated[
    LevelConversationOptions | PlaygroundConversationOptions,
    Field(discriminator="type"),
]


class StateAwaitingUserChoiceData(BaseModel):
    waiting: Literal[True] = True
    options: list[MessageOption]
    allow_custom: bool


class StateActiveData(BaseModel):
    waiting: Literal[False] = False
    id: FlowStateRef


ConversationStateData = Annotated[
    StateAwaitingUserChoiceData | StateActiveData,
    Field(discriminator="waiting"),
]


class PlaygroundConversationInfo(BaseModel):
    type: Literal["playground"] = "playground"
    topic: str


class LevelConversationInfo(BaseModel):
    type: Literal["level"] = "level"
    scenario: ConversationScenario
    level: Annotated[int, Field(ge=0, le=1)]


ConversationInfo = Annotated[
    PlaygroundConversationInfo | LevelConversationInfo,
    Field(discriminator="type"),
]

conversation_info_adapter = TypeAdapter(ConversationInfo)


class BaseConversationUninit(BaseModel):
    init: Literal[False] = False
    user_id: PyObjectId
    info: ConversationInfo
    agent: PersonaName
    elements: list[ConversationElement]


class BaseConversationInit(BaseModel):
    init: Literal[True] = True
    user_id: PyObjectId
    info: ConversationInfo
    agent: Persona
    state: ConversationStateData
    events: list[ConversationLogEntry]
    elements: list[ConversationElement]
    last_feedback_received: int


class ConversationDataUninit(BaseConversationUninit):
    id: Annotated[PyObjectId, Field(alias="_id")]

    model_config = ConfigDict(populate_by_name=True)


class ConversationDataInit(BaseConversationInit):
    id: Annotated[PyObjectId, Field(alias="_id")]

    model_config = ConfigDict(populate_by_name=True)


ConversationData = Annotated[
    ConversationDataInit | ConversationDataUninit,
    Field(discriminator="init"),
]

conversation_data_adapter = TypeAdapter(ConversationData)


class StateAwaitingUserChoice(BaseModel):
    waiting: Literal[True] = True
    options: list[str]
    allow_custom: bool


class StateActive(BaseModel):
    waiting: Literal[False] = False
    type: Literal["np", "ap", "feedback"]


ConversationState = Annotated[
    StateAwaitingUserChoice | StateActive,
    Field(discriminator="waiting"),
]


class Conversation(BaseModel):
    id: PyObjectId
    info: ConversationInfo
    agent: str
    state: ConversationState | None
    elements: list[ConversationElement]

    @staticmethod
    def from_data(data: ConversationData) -> "Conversation":
        state = (
            (
                StateAwaitingUserChoice(
                    options=[o.response for o in data.state.options],
                    allow_custom=data.state.allow_custom,
                )
                if isinstance(data.state, StateAwaitingUserChoiceData)
                else StateActive(type=data.state.id.type)
            )
            if isinstance(data, ConversationDataInit)
            else None
        )

        return Conversation(
            id=data.id,
            info=data.info,
            agent=data.agent.name,
            state=state,
            elements=data.elements,
        )


class ConversationDescriptorData(BaseModel):
    id: Annotated[PyObjectId, Field(alias="_id")]
    info: ConversationInfo
    agent: PersonaName

    model_config = ConfigDict(populate_by_name=True)


class ConversationDescriptor(BaseModel):
    id: PyObjectId
    info: ConversationInfo
    agent: str

    @staticmethod
    def from_data(data: ConversationDescriptorData) -> "ConversationDescriptor":
        return ConversationDescriptor(
            id=data.id,
            info=data.info,
            agent=data.agent.name,
        )


class NpMessageStep(BaseModel):
    type: Literal["np"] = "np"
    options: list[str]
    allow_custom: bool


class ApMessageStep(BaseModel):
    type: Literal["ap"] = "ap"
    content: str


class FeedbackStep(BaseModel):
    type: Literal["feedback"] = "feedback"
    content: Feedback


ConversationStep = Annotated[
    NpMessageStep | ApMessageStep | FeedbackStep,
    Field(discriminator="type"),
]


class SelectOptionNone(BaseModel):
    option: Literal["none"] = "none"


class SelectOptionCustom(BaseModel):
    option: Literal["custom"] = "custom"
    message: Annotated[str, StringConstraints(max_length=600)]


class SelectOptionIndex(BaseModel):
    option: Literal["index"] = "index"
    index: int


SelectOption = Annotated[
    SelectOptionNone | SelectOptionCustom | SelectOptionIndex,
    Field(discriminator="option"),
]
