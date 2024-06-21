import json

from api import llm


async def __generate_user_persona_from_info(user_info: dict, user_name: str) -> str:
    system_prompt = (
        "As a persona generator, your task is to generate a system prompt that will "
        "be used to make ChatGPT embody a persona based on the provided information. "
        f"Put the prompt in '<' and '>'. Start with 'You are {user_name}...'"
    )

    prompt_data = json.dumps({**user_info, "name": user_name})

    response = await llm.generate(
        model=llm.MODEL_GPT_4,
        system=system_prompt,
        prompt=prompt_data,
    )

    persona = response[response.index("<") + 1 : response.index(">")]

    persona = (
        f"{persona}\nAs an autistic individual, you follow the communication "
        "styles of an autistic person and have difficulty communicating naturally "
        "with the other person."
    )

    return persona


async def generate_user_persona(user_info: dict, user_name: str):
    user_persona = await __generate_user_persona_from_info(user_info, user_name)

    return user_persona
