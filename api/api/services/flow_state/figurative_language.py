from enum import Enum

from .base import (
    ApFlowState,
    ApFlowStateRef,
    FeedbackFlowState,
    FeedbackFlowStateRef,
    FlowOption,
    FlowState,
    FlowStateRef,
    Level,
    NpFlowState,
    NpFlowStateRef,
)


class NpFlowStateId(Enum):
    NORMAL = "normal"

    def as_ref(self) -> FlowStateRef:
        return FlowStateRef(root=NpFlowStateRef(id=self))


class ApFlowStateId(Enum):
    NORMAL = "normal"
    FIGURATIVE_MISUNDERSTOOD = "figurative_misunderstood"

    def as_ref(self) -> FlowStateRef:
        return FlowStateRef(root=ApFlowStateRef(id=self))


class FeedbackFlowStateId(Enum):
    NORMAL = "normal"

    def as_ref(self) -> FlowStateRef:
        return FlowStateRef(root=FeedbackFlowStateRef(id=self))


FLOW_STATES = [
    FlowState(
        root=NpFlowState(
            id=NpFlowStateId.NORMAL,
            options=[
                FlowOption(
                    prompt=(
                        "Do not use any figurative language in your next message. Keep "
                        "your message straightforward and literal."
                    ),
                    next=ApFlowStateId.NORMAL.as_ref(),
                ),
                FlowOption(
                    prompt=(
                        "Your next message is figurative and metaphorical. You use "
                        "language that is not literal and does not mean exactly what "
                        "it says. Your message is intended to be interpreted in a "
                        "non-literal way. Example: 'Let's hit the books.'"
                    ),
                    next=ApFlowStateId.FIGURATIVE_MISUNDERSTOOD.as_ref(),
                ),
                FlowOption(
                    prompt=(
                        "Your next message is mostly literal, but includes a hint of "
                        "figurative language. The message is mostly straightforward, "
                        "but there is also a figurative element that could be "
                        "misinterpreted. Example: 'It's so hot, it feels like 1000 "
                        "degrees outside.'"
                    ),
                    next=ApFlowStateId.FIGURATIVE_MISUNDERSTOOD.as_ref(),
                ),
            ],
        )
    ),
    FlowState(
        root=ApFlowState(
            id=ApFlowStateId.NORMAL,
            options=[
                FlowOption(
                    prompt=(
                        "Respond to the message in a normal, direct manner. Your "
                        "response correctly interprets the message and continues the "
                        "conversation. "
                    ),
                    next=NpFlowStateId.NORMAL.as_ref(),
                )
            ],
        )
    ),
    FlowState(
        root=ApFlowState(
            id=ApFlowStateId.FIGURATIVE_MISUNDERSTOOD,
            options=[
                FlowOption(
                    prompt=(
                        "You are responding to a figurative and metaphorical message. "
                        "You misunderstand the figurative language and your next "
                        "message will confidently interpret the message literally, "
                        "missing the intended meaning. The response should be literal "
                        "and direct, only addressing the figurative meaning and "
                        "ignoring the intended message. Example: NP: 'Let's hit the "
                        "books' -> AP: 'Why would you want to hit books? That would "
                        "damage them.'"
                    ),
                    next=FeedbackFlowStateId.NORMAL.as_ref(),
                )
            ],
        )
    ),
    FlowState(
        root=FeedbackFlowState(
            id=FeedbackFlowStateId.NORMAL,
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
            next_needs_improvement=ApFlowStateId.NORMAL.as_ref(),
            next_ok=NpFlowStateId.NORMAL.as_ref(),
        ),
    ),
]


FIGURATIVE_LANGUAGE_LEVEL = Level(
    flow_states=FLOW_STATES,
    initial_np_state=NpFlowStateId.NORMAL.as_ref(),
    initial_ap_state=ApFlowStateId.NORMAL.as_ref(),
)
