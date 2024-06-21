import json
import random

from . import llm


async def generate_scenario(user_info):
    system_prompt = (
        "As a scenario generator, your task is to generate an everyday conversational "
        "scenario that could happen over a text messaging app based on a user's "
        "profile. The scenario should be a generic situation that could happen between "
        "the user '{{USER}}' and an unfamiliar person '{{SUBJECT}}' in real life. The "
        "scenario should be realistic and relatable. Respond with a JSON object. The "
        "'user_scenario' key should be a string describing the user's perspective in "
        "the scenario, the 'subject_scenario' key should be a string describing the "
        "subject's perspective, and the 'user_goal' key should be a string describing "
        "the user's objective in the scenario.",
    )

    sampled_interests = random.sample(user_info["interests"], 6)
    prompt_data = json.dumps({**user_info, "interests": sampled_interests}, indent=2)

    response = await llm.generate(
        model=llm.MODEL_GPT_4,
        system=system_prompt,
        prompt=prompt_data,
    )

    json_data = response[response.index("{") : response.rindex("}") + 1]

    obj = json.loads(json_data)

    return obj["user_scenario"], obj["subject_scenario"], obj["user_goal"]
