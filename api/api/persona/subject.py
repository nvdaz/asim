import json
import random

# import faker
from api import llm

# fake = faker.Faker()


def __generate_vocal_styles():
    VOCAL_STYLES = [
        "Echolalia (repeat what others say)",
        "Stilted Speech (speak in a formal, stiff manner)",
        "Literal Interpretation (interpret words literally)",
        "Repetitive Speech (repeat words or phrases)",
        "Idiosyncratic Phrasing (use unique phrases)",
        "Hyperlexia (use advanced vocabulary)",
        "Hyperverbal (talk excessively)",
        "Clipped Speech (use short, abrupt sentences)",
        "Flat Affect (lack of emotional expression)",
        "Verbose Speech (provide more information than necessary)",
        "Scripted Speech (use pre-rehearsed phrases)",
        "Pedantic Speech (focus on precise details)",
        # "Pronoun Reversal (mix up pronouns, e.g., 'you' instead of 'I')",
        "Blunt Speech (speak in a direct, straightforward manner)",
        "Interest Inertia (focus on a single topic, regardless of context)",
    ]

    return random.sample(VOCAL_STYLES, random.randint(3, 5))


async def __generate_base_subject_info(scenario):
    system_prompt = (
        "Generate a persona for an autistic person '{{SUBJECT}}' in the provided "
        "scenario. Respond with a JSON object containing the following keys: 'age', "
        "'occupation', and 'interests'."
    )

    response = await llm.generate(
        model=llm.MODEL_GPT_4,
        system=system_prompt,
        prompt=scenario,
    )

    json_data = response[response.index("{") : response.rindex("}") + 1]

    return json.loads(json_data)


async def __generate_subject_persona_info(scenario):
    subject_info = await __generate_base_subject_info(scenario)
    vocal_styles = __generate_vocal_styles()

    subject_info["vocal_styles"] = vocal_styles

    return subject_info


async def __generate_subject_persona_from_info(subject_name: str, subject_info: dict):
    system_prompt = (
        "As a persona generator, your task is to generate a system prompt that will "
        "be used to make ChatGPT embody a persona based on the provided information. "
        "The persona is an autistic individual who struggles to communicate "
        "effectively with others. The persona should exhibit the vocal styles "
        "of an autistic person and should be ignorant of the needs of neurotypical "
        "individuals due to a lack of experience with them. The persona should be a "
        "realistic and relatable character who is messaging over text with another "
        f"person. Put the prompt in '<' and '>'. Start with 'You are {subject_name}...'"
    )

    prompt_data = json.dumps({**subject_info, "name": subject_name})

    response = await llm.generate(
        model=llm.MODEL_GPT_4,
        system=system_prompt,
        prompt=prompt_data,
    )

    persona = response[response.index("<") + 1 : response.index(">")]

    return persona


async def generate_subject_persona(scenario):
    # subject_name = fake.first_name()
    subject_name = "Alex"
    subject_persona_info = await __generate_subject_persona_info(scenario)
    subject_persona_info["name"] = subject_name

    subject_persona = await __generate_subject_persona_from_info(
        subject_name, subject_persona_info
    )

    return subject_persona_info, subject_persona
