from api.schemas.chat import ChatData
from api.schemas.user import UserData
from api.services import generate_suggestions, message_generation


async def generate_agent_message(
    user: UserData, chat: ChatData, state: str, objective: str | None
):
    if state == "react" or state == "objective-blunt":
        objective_prompt = (
            (generate_suggestions.objective_misunderstand_reaction_prompt(objective))
            if objective
            else None
        )
    else:
        objective_prompt = None

    return await message_generation.generate_message(
        user=user,
        user_sent=False,
        agent_name=chat.agent,
        messages=chat.messages,
        objective_prompt=objective_prompt,
    )
