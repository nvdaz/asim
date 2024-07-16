from .base import (
    NORMAL_AP_MAPPINGS,
    NORMAL_NP_MAPPINGS,
    ConversationContext,
    FlowStateMapping,
    NpFlowState,
    NpFlowStateMapping,
    NpFlowStateRef,
)
from .blunt_language import BLUNT_MAPPINGS
from .figurative_language import FIGURATIVE_MAPPINGS

PLAYGROUND_NP_MAPPINGS: list[FlowStateMapping] = [
    NpFlowStateMapping(
        id=NpFlowStateRef(id="normal"),
        value=NpFlowState(
            allow_custom=True,
        ),
    ),
    NpFlowStateMapping(
        id=NpFlowStateRef(id="confrontational"),
        value=NpFlowState(
            allow_custom=True,
        ),
    ),
]

PLAYGROUND_CONTEXT = ConversationContext(
    flow_states=[
        NORMAL_NP_MAPPINGS,
        NORMAL_AP_MAPPINGS,
        FIGURATIVE_MAPPINGS,
        BLUNT_MAPPINGS,
        PLAYGROUND_NP_MAPPINGS,
    ]
)
