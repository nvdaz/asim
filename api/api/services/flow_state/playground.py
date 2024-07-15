from .base import (
    NORMAL_AP_MAPPINGS,
    NORMAL_NP_MAPPINGS,
    FlowStateMapping,
    NpFlowState,
    NpFlowStateMapping,
    NpFlowStateRef,
    build_mappings,
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


PLAYGROUND_MAPPINGS = build_mappings(
    NORMAL_NP_MAPPINGS,
    NORMAL_AP_MAPPINGS,
    FIGURATIVE_MAPPINGS,
    BLUNT_MAPPINGS,
    PLAYGROUND_NP_MAPPINGS,
)

print(PLAYGROUND_MAPPINGS)
