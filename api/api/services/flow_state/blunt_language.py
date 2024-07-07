from typing import Literal

from .base import ApFlowState as _ApFlowState
from .base import ApFlowStateRef as _ApFlowStateRef
from .base import FeedbackFlowState as _FeedbackFlowState
from .base import FeedbackFlowStateRef as _FeedbackFlowStateRef
from .base import FlowOption, FlowState, Level
from .base import NpFlowState as _NpFlowState
from .base import NpFlowStateRef as _NpFlowStateRef

NpFlowStateId = Literal["normal", "confrontational"]
ApFlowStateId = Literal["normal"]
FeedbackFlowStateId = Literal["normal"]

NpFlowState = _NpFlowState[NpFlowStateId]
ApFlowState = _ApFlowState[ApFlowStateId]
FeedbackFlowState = _FeedbackFlowState[FeedbackFlowStateId]

NpFlowStateRef = _NpFlowStateRef[NpFlowStateId]
ApFlowStateRef = _ApFlowStateRef[ApFlowStateId]
FeedbackFlowStateRef = _FeedbackFlowStateRef[FeedbackFlowStateId]


FLOW_STATES = [
    FlowState(
        root=NpFlowState(
            id="normal",
            options=[
                FlowOption(
                    prompt=(
                        "Do not use any confrontational language in your next message. "
                        "Keep your message neutral and non-aggressive."
                    ),
                    next=ApFlowStateRef(id="normal").as_ref(),
                ),
            ],
        )
    ),
    FlowState(
        root=NpFlowState(
            id="confrontational",
            options=[
                FlowOption(
                    prompt=(
                        "Do not use any confrontational language in your next message."
                        "Keep your message neutral and non-aggressive."
                    ),
                    next=ApFlowStateRef(id="normal").as_ref(),
                ),
                FlowOption(
                    prompt=(
                        "Your next message is confrontational. Your message is "
                        "intended to be aggressive and assertive. Example: 'I don't "
                        "appreciate your tone.'"
                    ),
                    next=FeedbackFlowStateRef(id="normal").as_ref(),
                ),
                FlowOption(
                    prompt=(
                        "Your next message is negative. You just received a blunt "
                        "message and take it personally. Example: 'How dare you say "
                        "that?'"
                    ),
                    next=FeedbackFlowStateRef(id="normal").as_ref(),
                ),
            ],
        ),
    ),
    FlowState(
        root=ApFlowState(
            id="normal",
            options=[
                FlowOption(
                    prompt=(
                        "Your next message is blunt. Your message is intended "
                        "to be direct and straightforward. Example: 'I don't have "
                        "an opinion on that.', 'Stop talking, you don't know what "
                        "you're talking about.', 'I don't care what you think.'"
                    ),
                    next=NpFlowStateRef(id="confrontational").as_ref(),
                ),
            ],
        )
    ),
    FlowState(
        root=FeedbackFlowState(
            id="normal",
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
            next_needs_improvement=ApFlowStateRef(id="normal").as_ref(),
            next_ok=ApFlowStateRef(id="normal").as_ref(),
        )
    ),
]


BLUNT_LANGUAGE_LEVEL = Level(
    flow_states=FLOW_STATES,
    initial_np_state=NpFlowStateRef(id="normal").as_ref(),
    initial_ap_state=ApFlowStateRef(id="normal").as_ref(),
)
