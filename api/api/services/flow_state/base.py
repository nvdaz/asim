from typing import Annotated, Generic, Literal, TypeVar

from pydantic import BaseModel, Field

BaseNpFlowStateId = Literal["normal"]
BaseApFlowStateId = Literal["normal"]

NpFlowStateId = TypeVar("NpFlowStateId", bound=str)
ApFlowStateId = TypeVar("ApFlowStateId", bound=str)
FeedbackFlowStateId = TypeVar("FeedbackFlowStateId", bound=str)


class _BaseFlowStateRef(BaseModel):
    type: str
    id: str

    def __hash__(self) -> int:
        return hash((self.type, self.id))


class NpFlowStateRef(_BaseFlowStateRef, Generic[NpFlowStateId]):
    type: Literal["np"] = "np"
    id: NpFlowStateId


class ApFlowStateRef(_BaseFlowStateRef, Generic[ApFlowStateId]):
    type: Literal["ap"] = "ap"
    id: ApFlowStateId


class FeedbackFlowStateRef(_BaseFlowStateRef, Generic[FeedbackFlowStateId]):
    type: Literal["feedback"] = "feedback"
    id: FeedbackFlowStateId


FlowStateRef = Annotated[
    NpFlowStateRef | ApFlowStateRef | FeedbackFlowStateRef,
    Field(discriminator="type"),
]


NormalNpFlowStateRef = NpFlowStateRef(id="normal")
NormalApFlowStateRef = ApFlowStateRef(id="normal")


class FlowOption(BaseModel):
    prompt: str
    next: FlowStateRef


class UserFlowOption(BaseModel):
    prompt: str
    next: FlowStateRef
    checks: list[FeedbackFlowStateRef] = []


class NpFlowState(BaseModel, Generic[NpFlowStateId]):
    type: Literal["np"] = "np"
    extends: NpFlowStateRef | None = None
    options: list[UserFlowOption] = []
    allow_custom: bool = False


class ApFlowState(BaseModel, Generic[ApFlowStateId]):
    type: Literal["ap"] = "ap"
    options: list[FlowOption]


class FeedbackFlowState(BaseModel, Generic[FeedbackFlowStateId]):
    type: Literal["feedback"] = "feedback"
    check: str
    prompt: str


FlowState = Annotated[
    NpFlowState | ApFlowState | FeedbackFlowState,
    Field(discriminator="type"),
]


class NpFlowStateMapping(BaseModel):
    id: NpFlowStateRef
    value: NpFlowState


class ApFlowStateMapping(BaseModel):
    id: ApFlowStateRef
    value: ApFlowState


class FeedbackFlowStateMapping(BaseModel):
    id: FeedbackFlowStateRef
    value: FeedbackFlowState


FlowStateMapping = Annotated[
    NpFlowStateMapping | ApFlowStateMapping | FeedbackFlowStateMapping,
    Field(discriminator="type"),
]


NORMAL_NP_MAPPINGS: list[FlowStateMapping] = [
    NpFlowStateMapping(
        id=NpFlowStateRef(id="normal"),
        value=NpFlowState(
            options=[
                UserFlowOption(
                    prompt=(
                        "Use clear, direct language in your next message. Avoid using "
                        "any language that could be misinterpreted."
                    ),
                    next=ApFlowStateRef(id="normal"),
                )
            ]
        ),
    ),
]
NORMAL_AP_MAPPINGS: list[FlowStateMapping] = [
    ApFlowStateMapping(
        id=ApFlowStateRef(id="normal"),
        value=ApFlowState(
            options=[
                FlowOption(
                    prompt=(
                        "Respond to the message in a normal, direct manner. Your "
                        "response correctly interprets the message and continues the "
                        "conversation. DO NOT use figurative language."
                    ),
                    next=NpFlowStateRef(id="normal"),
                )
            ]
        ),
    ),
]


def _build_mappings(*mappings: list[FlowStateMapping]) -> dict[FlowStateRef, FlowState]:
    # combine options of mappings with the same id
    combined: dict[FlowStateRef, FlowState] = {}

    for mapping in mappings:
        for item in mapping:
            if item.id in combined:
                if item.value.type == "feedback":
                    raise ValueError("Cannot merge mappings with FeedbackFlowState")
                elif item.value.type == "np":
                    combined[item.id].allow_custom |= item.value.allow_custom

                combined[item.id].options.extend(item.value.options)
            else:
                combined[item.id] = item.value.model_copy(deep=True)

    # resolve extends after combining options
    for ref, state in combined.items():
        if isinstance(state, NpFlowState) and state.extends is not None:
            combined[ref].options.extend(combined[state.extends].options)

    return combined


class ConversationContext:
    _flow_states: dict[FlowStateRef, FlowState]
    _feedback_refs: list[FeedbackFlowStateRef]

    def __init__(
        self,
        flow_states: list[list[FlowStateMapping]],
    ):
        self._flow_states = _build_mappings(*flow_states)

        self._feedback_refs = [
            ref for ref, state in self._flow_states.items() if state.type == "feedback"
        ]

    def get_state(self, ref: FlowStateRef) -> FlowState:
        return self._flow_states[ref]

    def get_feedback_refs(self) -> list[FeedbackFlowStateRef]:
        return self._feedback_refs
