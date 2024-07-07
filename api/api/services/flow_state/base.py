from typing import Generic, Literal, TypeVar, Union

from pydantic import BaseModel, Field, RootModel
from typing_extensions import Annotated

NpFlowStateId = TypeVar("NpFlowStateId")
ApFlowStateId = TypeVar("ApFlowStateId")
FeedbackFlowStateId = TypeVar("FeedbackFlowStateId")


class NpFlowStateRef(BaseModel, Generic[NpFlowStateId]):
    type: Literal["np"] = "np"
    id: NpFlowStateId

    def as_ref(self) -> "FlowStateRef":
        return FlowStateRef(root=self)


class ApFlowStateRef(BaseModel, Generic[ApFlowStateId]):
    type: Literal["ap"] = "ap"
    id: ApFlowStateId

    def as_ref(self) -> "FlowStateRef":
        return FlowStateRef(root=self)


class FeedbackFlowStateRef(BaseModel, Generic[FeedbackFlowStateId]):
    type: Literal["feedback"] = "feedback"
    id: FeedbackFlowStateId

    def as_ref(self) -> "FlowStateRef":
        return FlowStateRef(root=self)


class FlowStateRef(RootModel):
    root: Annotated[
        Union[NpFlowStateRef, ApFlowStateRef, FeedbackFlowStateRef],
        Field(discriminator="type"),
    ]


class FlowOption(BaseModel):
    prompt: str
    next: FlowStateRef


class NpFlowState(BaseModel, Generic[NpFlowStateId]):
    type: Literal["np"] = "np"
    id: NpFlowStateId
    options: list[FlowOption]


class ApFlowState(BaseModel, Generic[ApFlowStateId]):
    type: Literal["ap"] = "ap"
    id: ApFlowStateId
    options: list[FlowOption]


class FeedbackFlowState(BaseModel, Generic[FeedbackFlowStateId]):
    type: Literal["feedback"] = "feedback"
    id: FeedbackFlowStateId
    prompt_analysis: str
    prompt_misunderstanding: str
    prompt_needs_improvement: str
    prompt_ok: str
    next_needs_improvement: FlowStateRef
    next_ok: FlowStateRef


class FlowState(RootModel):
    root: Annotated[
        Union[NpFlowState, ApFlowState, FeedbackFlowState],
        Field(discriminator="type"),
    ]


class Level(BaseModel):
    flow_states: list[FlowState]
    initial_np_state: FlowStateRef
    initial_ap_state: FlowStateRef

    def get_flow_state(self, ref: FlowStateRef) -> FlowState:
        return next(
            state
            for state in self.flow_states
            if state.root.type == ref.root.type and state.root.id == ref.root.id
        )
