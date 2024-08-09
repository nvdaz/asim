from pydantic import BaseModel


class LevelConversationScenarioSeed(BaseModel):
    user_perspective: str
    agent_perspective: str
    user_goal: str
    is_user_initiated: bool
    adapt: bool
