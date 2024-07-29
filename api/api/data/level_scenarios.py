from api.schemas.conversation import LevelConversationScenario, LevelConversationStage


def get_base_level_scenario(stage: LevelConversationStage) -> LevelConversationScenario:
    match stage:
        case LevelConversationStage(level=level) if level == 1:
            return LevelConversationScenario(
                user_perspective=(
                    "You are working on a group project with your classmates."
                ),
                agent_perspective=(
                    "You are working on a group project with your classmates."
                ),
                user_goal="Set up a meeting with your group to discuss the project.",
                is_user_initiated=True,
            )
        case LevelConversationStage(level=level) if level == 2:
            return LevelConversationScenario(
                user_perspective=(
                    "You are working on a group project with your colleagues."
                ),
                agent_perspective=(
                    "You are working on a group project with your colleagues."
                ),
                user_goal="Set up a meeting with your group to discuss the project.",
                is_user_initiated=True,
            )
        case _:
            raise ValueError(f"Invalid level and part: {stage.level} and {stage.part}.")
