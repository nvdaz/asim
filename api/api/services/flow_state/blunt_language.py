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
    CONFRONTATIONAL = "confrontational"

    def as_ref(self) -> FlowStateRef:
        return FlowStateRef(root=NpFlowStateRef(id=self))


class ApFlowStateId(Enum):
    NORMAL = "normal"

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
                        "Do not use any confrontational language in your next message. "
                        "Keep your message neutral and non-aggressive."
                    ),
                    next=ApFlowStateId.NORMAL.as_ref(),
                ),
            ],
        )
    ),
    FlowState(
        root=NpFlowState(
            id=NpFlowStateId.CONFRONTATIONAL,
            options=[
                FlowOption(
                    prompt=(
                        "Do not use any confrontational language in your next message."
                        "Keep your message neutral and non-aggressive."
                    ),
                    next=ApFlowStateId.NORMAL.as_ref(),
                ),
                FlowOption(
                    prompt=(
                        "Your next message is confrontational. Your message is intended"
                        "to be aggressive and assertive. Example: 'I don't appreciate"
                        "your tone.'"
                    ),
                    next=FeedbackFlowStateId.NORMAL.as_ref(),
                ),
                FlowOption(
                    prompt=(
                        "Your next message is negative. You just received a blunt "
                        "message and take it personally. Example: 'How dare you say "
                        "that?'"
                    ),
                    next=FeedbackFlowStateId.NORMAL.as_ref(),
                ),
            ],
        ),
    ),
    FlowState(
        root=ApFlowState(
            id=ApFlowStateId.NORMAL,
            options=[
                FlowOption(
                    prompt=(
                        "Your next message is blunt. Your message is intended "
                        "to be direct and straightforward. Example: 'I don't have "
                        "an opinion on that.', 'Stop talking, you don't know what "
                        "you're talking about.', 'I don't care what you think.'"
                    ),
                    next=NpFlowStateId.CONFRONTATIONAL.as_ref(),
                ),
            ],
        )
    ),
    FlowState(
        root=FeedbackFlowState(
            id=FeedbackFlowStateId.NORMAL,
            prompt_analysis=(
                "The conversation needs improvement if there are instances "
                "where the user is confrontational or negative in response to a "
                "blunt message."
            ),
            prompt_ok=(
                "Point out any areas where the user avoided confrontational language "
                "and used neutral language instead despite a blunt message."
            ),
            prompt_needs_improvement=(
                "The latest message was confrontational and aggressive. The user "
                "overreacted to a blunt message and needs to use neutral language "
                "instead. Provide feedback on how the user could have been more "
                "patient and understanding."
            ),
            prompt_misunderstanding=(
                "The latest message was confrontational and aggressive. The user "
                "overreacted to a blunt message and needs to use neutral language "
                "instead. Provide feedback on how the user could have been more "
                "patient and understanding."
            ),
            next_needs_improvement=ApFlowStateId.NORMAL.as_ref(),
            next_ok=ApFlowStateId.NORMAL.as_ref(),
        )
    ),
]


BLUNT_LANGUAGE_LEVEL = Level(
    flow_states=FLOW_STATES,
    initial_np_state=NpFlowStateId.NORMAL.as_ref(),
    initial_ap_state=ApFlowStateId.NORMAL.as_ref(),
)
