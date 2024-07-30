from typing import Annotated, Literal, Sequence

from pydantic import (
    AfterValidator,
    BaseModel,
    ConfigDict,
    Field,
    StringConstraints,
    TypeAdapter,
)

from api.services.flow_state.base import FeedbackFlowStateRef, FlowStateRef

from .objectid import PyObjectId
from .persona import AgentPersona, PersonaName


class FailedCheck(BaseModel):
    source: FeedbackFlowStateRef
    reason: str


class Feedback(BaseModel):
    title: Annotated[str, StringConstraints(max_length=50)]
    body: Annotated[str, StringConstraints(max_length=600)]
    follow_up: str | None = None


class UserMessage(BaseModel):
    user_sent: Literal[True] = True
    message: str


class AgentMessage(BaseModel):
    user_sent: Literal[False] = False
    message: str


Message = Annotated[
    UserMessage | AgentMessage,
    Field(discriminator="user_sent"),
]


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


message_list_adapter = TypeAdapter(Sequence[Message])


class MessageOption(BaseModel):
    response: str
    next: FlowStateRef
    checks: list[FeedbackFlowStateRef]


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

LEVEL_MIN = 1
LEVEL_MAX = 2
PART_MIN = 1
PART_MAX = 5


class LevelConversationStage(BaseModel):
    type: Literal["level"] = "level"
    level: Annotated[int, Field(ge=LEVEL_MIN, le=LEVEL_MAX)]
    part: Annotated[int, Field(ge=PART_MIN, le=PART_MAX)]

    def __str__(self) -> str:
        return f"level-{self.level}p{self.part}"


ALL_LEVEL_STAGES = [
    f"level-{level}p{part}"
    for level in range(LEVEL_MIN, LEVEL_MAX + 1)
    for part in range(PART_MIN, PART_MAX + 1)
]

print(ALL_LEVEL_STAGES)


class PlaygroundConversationStage(BaseModel):
    type: Literal["playground"] = "playground"

    def __str__(self) -> str:
        return "playground"


ALL_PLAYGROUND_STAGES = ["playground"]


ConversationStage = Annotated[
    LevelConversationStage | PlaygroundConversationStage,
    Field(discriminator="type"),
]


def conversation_stage_from_str(stage: str) -> ConversationStage:
    if stage == "playground":
        return PlaygroundConversationStage()
    elif stage.startswith("level-"):
        level, part = stage.split("-")[1].split("p")
        return LevelConversationStage(level=int(level), part=int(part))
    else:
        raise ValueError(f"Invalid conversation stage: {stage}")


def validate_conversation_stage_str(stage: str) -> str:
    conversation_stage_from_str(stage)

    return stage


ConversationStageStr = Annotated[
    str,
    AfterValidator(validate_conversation_stage_str),
    Field(json_schema_extra={"enum": ALL_LEVEL_STAGES + ALL_PLAYGROUND_STAGES}),  # type: ignore
]


class BaseConversationScenario(BaseModel):
    user_perspective: str
    agent_perspective: str


class LevelConversationScenario(BaseConversationScenario):
    user_goal: str
    is_user_initiated: bool


class PlaygroundConversationScenario(BaseConversationScenario):
    topic: str | None = None


ConversationScenario = LevelConversationScenario | PlaygroundConversationScenario


class LevelConversationInfo(LevelConversationStage):
    scenario: LevelConversationScenario


class PlaygroundConversationInfo(PlaygroundConversationStage):
    scenario: PlaygroundConversationScenario


ConversationInfo = Annotated[
    LevelConversationInfo | PlaygroundConversationInfo,
    Field(discriminator="type"),
]

conversation_info_adapter = TypeAdapter(ConversationInfo)


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
    StateAwaitingUserChoiceData | StateFeedbackData | StateActiveData,
    Field(discriminator="type"),
]


class BaseConversation(BaseModel):
    init: Literal[True] = True
    user_id: PyObjectId
    info: ConversationInfo
    agent: AgentPersona
    state: ConversationStateData
    events: list[ConversationLogEntry]
    elements: list[ConversationElement]


class ConversationData(BaseConversation):
    id: Annotated[PyObjectId, Field(alias="_id")]

    model_config = ConfigDict(populate_by_name=True)


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
    stage: str
    scenario: ConversationScenario
    agent: str
    state: ConversationState | None
    elements: list[ConversationElement]

    @staticmethod
    def from_data(data: ConversationData) -> "Conversation":
        state = None
        if isinstance(data, ConversationData):
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
            stage=str(data.info),
            scenario=data.info.scenario,
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
    scenario: ConversationScenario
    agent: str

    @staticmethod
    def from_data(data: ConversationDescriptorData) -> "ConversationDescriptor":
        return ConversationDescriptor(
            id=data.id,
            scenario=data.info.scenario,
            agent=data.agent.name,
        )


class NpMessageStep(BaseModel):
    type: Literal["np"] = "np"
    options: list[str]
    allow_custom: bool
    max_unlocked_stage: ConversationStageStr


class ApMessageStep(BaseModel):
    type: Literal["ap"] = "ap"
    content: str
    max_unlocked_stage: ConversationStageStr


class FeedbackStep(BaseModel):
    type: Literal["feedback"] = "feedback"
    content: Feedback
    max_unlocked_stage: ConversationStageStr


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


class PregenerateOptions(BaseModel):
    user_id: PyObjectId
    stage: ConversationStage
