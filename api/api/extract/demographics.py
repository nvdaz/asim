import json

from api import llm


async def extract_demographics(messages: list[list[str]]) -> dict:
    system_prompt = (
        "As a user analyst, your task is to extract demographic information about the "
        "user based on the messages they sent to a chatbot. Start by analyzing "
        "messages sent by the user for any personal details, then use deductive "
        "reasoning to accurately determine their demographic information. Respond like "
        'this: <analysis>[ANALYSIS HERE]</analysis> {"age": "AGE", "gender": '
        '"GENDER", "location": "LOCATION", "occupation": "OCCUPATION", '
        '"highest_education": "HIGHEST EDUCATION"}'
    )
    prompt_data = "\n".join([message[0] for message in messages])
    response = await llm.generate(
        model=llm.MODEL_GPT_4,
        system=system_prompt,
        prompt=prompt_data,
    )

    data = response[response.index("{") : response.rindex("}") + 1]

    demographics = json.loads(data)

    assert "age" in demographics
    assert "gender" in demographics
    assert "location" in demographics
    assert "occupation" in demographics
    assert "highest_education" in demographics

    return demographics
