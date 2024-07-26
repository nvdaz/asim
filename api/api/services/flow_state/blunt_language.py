from typing import Literal

from .base import (
    NORMAL_NP_MAPPINGS,
    ApFlowStateMapping,
    ConversationContext,
    FeedbackFlowStateMapping,
    FlowOption,
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

NpFlowStateId = Literal["normal", "confrontational"]
ApFlowStateId = Literal["normal"]
FeedbackFlowStateId = Literal["confrontational"]

NpFlowState = _NpFlowState[NpFlowStateId]
ApFlowState = _ApFlowState[ApFlowStateId]
FeedbackFlowState = _FeedbackFlowState[FeedbackFlowStateId]

NpFlowStateRef = _NpFlowStateRef[NpFlowStateId]
ApFlowStateRef = _ApFlowStateRef[ApFlowStateId]
FeedbackFlowStateRef = _FeedbackFlowStateRef[FeedbackFlowStateId]


BLUNT_MAPPINGS: list[FlowStateMapping] = [
    NpFlowStateMapping(
        id=NpFlowStateRef(id="confrontational"),
        value=NpFlowState(
            extends=NpFlowStateRef(id="normal"),
            options=[
                UserFlowOption(
                    prompt=(
                        "Your next message is confrontational. Your message is "
                        "intended to be aggressive and assertive."
                    ),
                    checks=[FeedbackFlowStateRef(id="confrontational")],
                    next=ApFlowStateRef(id="normal"),
                ),
                UserFlowOption(
                    prompt=(
                        "Your next message is dismissive. You just received a blunt "
                        "message and take it personally."
                    ),
                    checks=[FeedbackFlowStateRef(id="confrontational")],
                    next=ApFlowStateRef(id="normal"),
                ),
            ],
        ),
    ),
    ApFlowStateMapping(
        id=ApFlowStateRef(id="normal"),
        value=ApFlowState(
            options=[
                FlowOption(
                    prompt=(
                        "Your next message is blunt. Your message is intended "
                        "to be direct and straightforward, which will be perceived "
                        "as rude."
                    ),
                    next=NpFlowStateRef(id="confrontational"),
                ),
                FlowOption(
                    prompt=(
                        "Your next message is somewhat blunt. Your message is direct "
                        "and straightforward, which may be perceived as blunt."
                    ),
                    next=NpFlowStateRef(id="confrontational"),
                ),
            ],
        ),
    ),
    FeedbackFlowStateMapping(
        id=FeedbackFlowStateRef(id="confrontational"),
        value=FeedbackFlowState(
            check=(
                "The user is not confrontational in response to a blunt message from "
                "the autistic individual."
            ),
            prompt=(
                "The latest message was confrontational and aggressive. The user "
                "overreacted to a blunt message and needs to use neutral language "
                "instead. Provide feedback on how the user could have been more "
                "patient and understanding."
            ),
            next=ApFlowStateRef(id="normal"),
        ),
    ),
]


BLUNT_LANGUAGE_LEVEL_CONTEXT = ConversationContext(
    flow_states=[NORMAL_NP_MAPPINGS, BLUNT_MAPPINGS]
)
