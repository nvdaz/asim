from typing import Literal

from .base import (
    NORMAL_AP_MAPPINGS,
    NORMAL_NP_MAPPINGS,
    ConversationContext,
    FeedbackFlowStateMapping,
    FlowStateMapping,
    NpFlowStateMapping,
    UserFlowOption,
)
from .base import ApFlowState as _ApFlowState
from .base import ApFlowStateRef as _ApFlowStateRef
from .base import FeedbackFlowState as _FeedbackFlowState
from .base import FeedbackFlowStateRef as _FeedbackFlowStateRef
from .base import NpFlowState as _NpFlowState
from .base import NpFlowStateRef as _NpFlowStateRef

NpFlowStateId = Literal["normal"]
ApFlowStateId = Literal["normal", "ambiguous_misunderstood"]
FeedbackFlowStateId = Literal["ambiguous"]

NpFlowState = _NpFlowState[NpFlowStateId]
ApFlowState = _ApFlowState[ApFlowStateId]
FeedbackFlowState = _FeedbackFlowState[FeedbackFlowStateId]

NpFlowStateRef = _NpFlowStateRef[NpFlowStateId]
ApFlowStateRef = _ApFlowStateRef[ApFlowStateId]
FeedbackFlowStateRef = _FeedbackFlowStateRef[FeedbackFlowStateId]


AMBIGUOUS_MAPPINGS: list[FlowStateMapping] = [
    NpFlowStateMapping(
        id=NpFlowStateRef(id="normal"),
        value=NpFlowState(
            options=[
                UserFlowOption(
                    prompt=(
                        "Your next message is figurative and metaphorical. You use "
                        "language that is not literal and does not mean exactly what "
                        "it says. Your message is intended to be interpreted in a "
                        "non-literal way. Example: 'Let's hit the books.'"
                    ),
                    next=ApFlowStateRef(id="normal"),
                    checks=[FeedbackFlowStateRef(id="ambiguous")],
                ),
                UserFlowOption(
                    prompt=(
                        "Your next message is mostly literal, but includes a hint of "
                        "ambiguous language. The message is mostly straightforward, "
                        "but there is also a ambiguous element that could be "
                        "misinterpreted."
                    ),
                    next=ApFlowStateRef(id="normal"),
                    checks=[FeedbackFlowStateRef(id="ambiguous")],
                ),
            ],
        ),
    ),
    FeedbackFlowStateMapping(
        id=FeedbackFlowStateRef(id="ambiguous"),
        value=FeedbackFlowState(
            check=(
                "The user does not use ambiguous language in their message, i.e., "
                "they use language that is meant to be interpreted in a non-literal "
                "way."
            ),
            prompt=(
                "The latest message needs improvement as it contains ambiguous "
                "language, which can be misinterpreted by autistic individuals. "
                "Provide feedback on how their message could have been clearer and "
                "more direct."
            ),
        ),
    ),
]


AMBIGUOUS_LANGUAGE_LEVEL_CONTEXT = ConversationContext(
    flow_states=[NORMAL_NP_MAPPINGS, NORMAL_AP_MAPPINGS, AMBIGUOUS_MAPPINGS],
)
