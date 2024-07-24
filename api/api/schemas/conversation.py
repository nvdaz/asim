from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, StringConstraints, TypeAdapter

from api.services.flow_state.base import FeedbackFlowStateRef, FlowStateRef

from .objectid import PyObjectId
from .persona import Persona, PersonaName


class FailedCheck(BaseModel):
    source: FeedbackFlowStateRef
    reason: str


class Feedback(BaseModel):
    title: Annotated[str, StringConstraints(max_length=50)]
    body: Annotated[str, StringConstraints(max_length=600)]
    follow_up: str | None = None


class Message(BaseModel):
    user_sent: bool
    message: str


class UserMessage(Message):
    user_sent: Literal[True] = True


class AgentMessage(Message):
    user_sent: Literal[False] = False


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


message_list_adapter: TypeAdapter[list[Message]] = TypeAdapter(list[Message])


class MessageOption(BaseModel):
    response: str
    next: FlowStateRef
    checks: list[FeedbackFlowStateRef]


class ConversationScenario(BaseModel):
    user_perspective: str
    agent_perspective: str
    user_goal: str | None
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
    failed_checks: list[FailedCheck]
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

    def stage_name(self) -> str:
        return f"level-{self.level}"


class PlaygroundConversationOptions(BaseModel):
    type: Literal["playground"] = "playground"

    def stage_name(self) -> str:
        return "playground"


ConversationOptions = Annotated[
    LevelConversationOptions | PlaygroundConversationOptions,
    Field(discriminator="type"),
]


class StateAwaitingUserChoiceData(BaseModel):
    type: Literal["waiting"] = "waiting"
    options: list[MessageOption]
    allow_custom: bool


class StateFeedbackData(BaseModel):
    type: Literal["feedback"] = "feedback"
    failed_checks: list[FailedCheck]
    next: FlowStateRef


class StateActiveData(BaseModel):
    type: Literal["active"] = "active"
    id: FlowStateRef


ConversationStateData = Annotated[
    StateAwaitingUserChoiceData | StateActiveData,
    Field(discriminator="type"),
]


class PlaygroundConversationInfo(BaseModel):
    type: Literal["playground"] = "playground"
    scenario: ConversationScenario
    topic: str | None

    def stage_name(self) -> str:
        return "playground"


class LevelConversationInfo(BaseModel):
    type: Literal["level"] = "level"
    scenario: ConversationScenario
    level: Annotated[int, Field(ge=0, le=1)]

    def stage_name(self) -> str:
        return f"level-{self.level}"


ConversationInfo = Annotated[
    PlaygroundConversationInfo | LevelConversationInfo,
    Field(discriminator="type"),
]

conversation_info_adapter: TypeAdapter[ConversationInfo] = TypeAdapter(ConversationInfo)


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

conversation_data_adapter: TypeAdapter[ConversationData] = TypeAdapter(ConversationData)


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
        state = None
        if isinstance(data, ConversationDataInit):
            match data.state:
                case StateAwaitingUserChoiceData(
                    options=options, allow_custom=allow_custom
                ):
                    state = StateAwaitingUserChoice(
                        options=[o.response for o in options],
                        allow_custom=allow_custom,
                    )
                case StateActiveData(id=id):
                    state = StateActive(type=id.type)
                case StateFeedbackData():
                    state = StateActive(type="feedback")
                case _:
                    raise ValueError(f"Unknown state type: {data.state}")

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
    max_unlocked_stage: str | None


class ApMessageStep(BaseModel):
    type: Literal["ap"] = "ap"
    content: str
    max_unlocked_stage: str | None


class FeedbackStep(BaseModel):
    type: Literal["feedback"] = "feedback"
    content: Feedback
    max_unlocked_stage: str | None


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
