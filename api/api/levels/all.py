from api.schemas.conversation import (
    LevelConversationStage,
)

from . import level_1, level_2, level_3
from .seed import LevelConversationScenarioSeed
from .states import States


def get_level_states(stage: LevelConversationStage) -> States:
    level_states = {
        1: level_1.STATES,
        2: level_2.STATES,
        3: level_3.STATES,
    }

    return level_states[stage.level]


def get_base_level_scenario(
    stage: LevelConversationStage,
) -> LevelConversationScenarioSeed:
    level_scenarios = {
        1: level_1.SCENARIO_SEED,
        2: level_2.SCENARIO_SEED,
        3: level_3.SCENARIO_SEED,
    }

    return level_scenarios[stage.level]
