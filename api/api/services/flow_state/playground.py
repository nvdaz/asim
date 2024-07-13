from .base import NORMAL_AP_MAPPINGS, NORMAL_NP_MAPPINGS, build_mappings
from .blunt_language import BLUNT_MAPPINGS
from .figurative_language import FIGURATIVE_MAPPINGS

PLAYGROUND_MAPPINGS = build_mappings(
    NORMAL_NP_MAPPINGS, NORMAL_AP_MAPPINGS, FIGURATIVE_MAPPINGS, BLUNT_MAPPINGS
)
