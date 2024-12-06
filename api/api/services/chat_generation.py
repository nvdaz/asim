from api.schemas.chat import ChatData
from api.schemas.user import UserPersonalizationOptions
from api.services import generate_suggestions, message_generation


async def generate_agent_message(
    pers: UserPersonalizationOptions,
    chat: ChatData,
    state: str,
    objective: str | None,
    problem: str | None,
    bypass_objective_prompt_check: bool = False,
):
    if state == "react" or state == "objective-blunt":
        objective_prompt = (
            (
                generate_suggestions.objective_misunderstand_reaction_prompt(
                    objective, problem
                )
            )
            if objective
            else None
        )
    else:
        objective_prompt = None

    return await message_generation.generate_message(
        pers=pers,
        user_sent=False,
        agent_name=chat.agent,
        personalize=chat.suggestion_generation == "content-inspired",
        messages=chat.messages,
        objective_prompt=objective_prompt,
        bypass_objective_prompt_check=bypass_objective_prompt_check,
    )
