from typing import Literal

from .base import (
    NORMAL_AP_MAPPINGS,
    NORMAL_NP_MAPPINGS,
    ApFlowStateMapping,
    FeedbackFlowStateMapping,
    FlowOption,
    FlowStateMapping,
    Level,
    NpFlowStateMapping,
    build_mappings,
)
from .base import ApFlowState as _ApFlowState
from .base import ApFlowStateRef as _ApFlowStateRef
from .base import FeedbackFlowState as _FeedbackFlowState
from .base import FeedbackFlowStateRef as _FeedbackFlowStateRef
from .base import NpFlowState as _NpFlowState
from .base import NpFlowStateRef as _NpFlowStateRef

NpFlowStateId = Literal["normal"]
ApFlowStateId = Literal["normal", "figurative_misunderstood"]
FeedbackFlowStateId = Literal["figurative"]

NpFlowState = _NpFlowState[NpFlowStateId]
ApFlowState = _ApFlowState[ApFlowStateId]
FeedbackFlowState = _FeedbackFlowState[FeedbackFlowStateId]

NpFlowStateRef = _NpFlowStateRef[NpFlowStateId]
ApFlowStateRef = _ApFlowStateRef[ApFlowStateId]
FeedbackFlowStateRef = _FeedbackFlowStateRef[FeedbackFlowStateId]


FIGURATIVE_MAPPINGS: list[FlowStateMapping] = [
    NpFlowStateMapping(
        id=NpFlowStateRef(id="normal"),
        value=NpFlowState(
            options=[
                FlowOption(
                    prompt=(
                        "Your next message is figurative and metaphorical. You use "
                        "language that is not literal and does not mean exactly what "
                        "it says. Your message is intended to be interpreted in a "
                        "non-literal way. Example: 'Let's hit the books.'"
                    ),
                    next=ApFlowStateRef(id="figurative_misunderstood"),
                ),
                FlowOption(
                    prompt=(
                        "Your next message is mostly literal, but includes a hint of "
                        "figurative language. The message is mostly straightforward, "
                        "but there is also a figurative element that could be "
                        "misinterpreted. Example: 'It's so hot, it feels like 1000 "
                        "degrees outside.'"
                    ),
                    next=ApFlowStateRef(id="figurative_misunderstood"),
                ),
            ],
        ),
    ),
    ApFlowStateMapping(
        id=ApFlowStateRef(id="figurative_misunderstood"),
        value=ApFlowState(
            options=[
                FlowOption(
                    prompt=(
                        "Respond to the message in a way that misunderstands the "
                        "figurative language used. Your response should be literal and "
                        "direct, only addressing the literal meaning of the message "
                        "without considering the figurative nature. Example: 'Let's "
                        "hit the books.' -> 'I don't have any books to hit.'"
                    ),
                    next=FeedbackFlowStateRef(id="figurative"),
                )
            ],
        ),
    ),
    FeedbackFlowStateMapping(
        id=FeedbackFlowStateRef(id="figurative"),
        value=FeedbackFlowState(
            prompt_analysis=(
                "The conversation needs improvement if there are instances where "
                "figurative language is used, which can be misinterpreted by the "
                "autistic individual."
            ),
            prompt_ok=(
                "Point out any areas where the user avoided figurative language, which "
                "can be misinterpreted by autistic individuals."
            ),
            prompt_needs_improvement=(
                "The latest message needs improvement as it contains figurative "
                "language, which can be misinterpreted by autistic individuals. "
                "Provide feedback on how their message could have been clearer and "
                "more direct."
            ),
            prompt_misunderstanding=(
                "The latest message needs improvement as it contains figurative "
                "language, which was misinterpreted by the autistic individual. "
                "Provide feedback on how the user could have been clearer in their "
                "communication to avoid confusion."
            ),
            next_needs_improvement=ApFlowStateRef(id="normal"),
            next_ok=NpFlowStateRef(id="normal"),
        ),
    ),
]

FIGURATIVE_LANGUAGE_LEVEL = Level(
    mappings=build_mappings(
        NORMAL_NP_MAPPINGS, NORMAL_AP_MAPPINGS, FIGURATIVE_MAPPINGS
    ),
)
