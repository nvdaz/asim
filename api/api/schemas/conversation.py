from typing import Annotated, Generic, Literal, Sequence, TypeVar

from pydantic import (
    AfterValidator,
    BaseModel,
    ConfigDict,
    Field,
    SerializeAsAny,
    StringConstraints,
    TypeAdapter,
)

from api.levels.states import BaseData

from .objectid import PyObjectId
from .persona import AgentPersona, PersonaName

StateData = TypeVar("StateData", bound=BaseData)


class Feedback(BaseModel):
    title: Annotated[str, StringConstraints(max_length=50)]
    body: Annotated[str, StringConstraints(max_length=600)]
    follow_up: str


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


def dump_message_list(
    messages: Sequence[Message], user: str | None, agent: str | None
) -> str:
    return "\n".join(
        [
            f"{(user or 'User') if message.user_sent else agent}: {message.message}"
            for message in messages
        ]
    )


class MessageOption(BaseModel, Generic[StateData]):
    response: str
    next: SerializeAsAny[StateData] | None


class NpMessageOptionsLogEntry(BaseModel):
    type: Literal["np_options"] = "np_options"
    options: list[MessageOption]


class NpMessageSelectedLogEntry(BaseModel):
    type: Literal["np_selected"] = "np_selected"
    message: str


class ApMessageLogEntry(BaseModel):
    type: Literal["ap"] = "ap"
    message: str


class FeedbackLogEntry(BaseModel):
    type: Literal["feedback"] = "feedback"
    content: Feedback


ConversationLogEntry = Annotated[
    NpMessageOptionsLogEntry
    | NpMessageSelectedLogEntry
    | ApMessageLogEntry
    | FeedbackLogEntry,
    Field(discriminator="type"),
]

LEVEL_MIN = 1
LEVEL_MAX = 3


class LevelConversationStage(BaseModel):
    type: Literal["level"] = "level"
    level: Annotated[int, Field(ge=LEVEL_MIN, le=LEVEL_MAX)]

    def __str__(self) -> str:
        return f"level-{self.level}"


ALL_LEVEL_STAGES = [f"level-{level}" for level in range(LEVEL_MIN, LEVEL_MAX + 1)]


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
        level = stage.split("-")[1]
        return LevelConversationStage(level=int(level))
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


class StateActiveData(BaseModel, Generic[StateData]):
    type: Literal["active"] = "active"
    data: SerializeAsAny[StateData] | None


class StateCompletedData(BaseModel):
    type: Literal["completed"] = "completed"


ConversationStateData = Annotated[
    StateAwaitingUserChoiceData | StateActiveData | StateCompletedData,
    Field(discriminator="type"),
]


class BaseConversation(BaseModel):
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
    type: Literal["np", "ap", "feedback", "completed"]


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
        match data.state:
            case StateAwaitingUserChoiceData(
                options=options, allow_custom=allow_custom
            ):
                state = StateAwaitingUserChoice(
                    options=[o.response for o in options],
                    allow_custom=allow_custom,
                )
            case StateActiveData():
                state = StateActive(type="np")
                # TODO: this isn't always np
            case StateCompletedData():
                state = StateActive(type="completed")
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


class CompletedStep(BaseModel):
    type: Literal["complete"] = "complete"
    max_unlocked_stage: ConversationStageStr


ConversationStep = Annotated[
    NpMessageStep | ApMessageStep | FeedbackStep | CompletedStep,
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
