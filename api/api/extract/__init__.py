from .demographics import extract_demographics
from .interests import extract_interests


async def extract_user_info(messages: list[str]) -> dict:
    interests = await extract_interests(messages)
    demographics = await extract_demographics(messages)

    return {"interests": interests, "demographics": demographics}
