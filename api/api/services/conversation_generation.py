import random

from bson import ObjectId
from pydantic import AfterValidator, BaseModel
from typing_extensions import Annotated

from api.db.conversations import get_previous_scenarios
from api.schemas.conversation import ConversationScenario
from api.schemas.persona import BasePersona, Persona

from . import llm


async def generate_conversation_scenario(
    user_id: ObjectId, user: Persona, subject_name: str
) -> ConversationScenario:
    system_prompt = (
        "As a scenario generator, your task is to generate a casual conversational "
        f"scenario that could happen over a text messaging app based on {user.name}'s "
        "profile. The scenario should be a specific situation that could happen "
        f"between {user.name} and an unfamiliar person {subject_name} over text "
        "messaging. The scenario should be realistic and relatable. Respond with a "
        f"JSON object. The 'user_perspective' key should be a string describing "
        f"{user.name}'s perspective in the scenario (use second person pronouns to "
        f"refer to {user.name}), the 'subject_perspective' key should be a string "
        f"describing {subject_name}'s perspective (use second person pronouns to refer "
        f"to {subject_name}), the 'user_goal' key should be a string describing "
        f"{user.name}'s objective in the scenario (begin with an action verb, e.g., "
        "'Convince', 'Explain', 'Find out' and use second person pronouns to refer to "
        f"{user.name}), and the 'is_user_initiated' key should be a boolean that is "
        f"true if the first message would be sent by {user.name} and false if it would "
        f"be sent by {subject_name}. Do not generate scenarios that involve "
        "significant external elements, such as finding a bug in a software program "
        "(it is not possible to send the code). Also do not generate scenarios that "
        "are too similar to a previously generated scenario. Examples:\n"
        "\n".join(
            [
                ex.model_dump_json()
                for ex in [
                    ConversationScenario(
                        user_perspective=(
                            "Phil, a theoretical physics student, has reached out to "
                            "you over text. Phil is looking for advice on studying "
                            "theoretical physics and wants to discuss different "
                            "areas of the field to explore further."
                        ),
                        subject_perspective=(
                            "You reach out to Professor Green, a theoretical physics "
                            "professor, over text. Professor Green is excited to chat "
                            "about theoretical physics and share advice on studying "
                            "the field and their experiences in it."
                        ),
                        user_goal=(
                            "Provide advice on studying theoretical physics to Phil, "
                            "discussing different areas of the field that Phil can "
                            "explore further."
                        ),
                        is_user_initiated=False,
                    ),
                    ConversationScenario(
                        user_perspective=(
                            "Having just started at a pharmaceutical company, you "
                            "exchanged numbers with your colleague, Jake. Start "
                            "texting to discuss work, get insights into his role, and "
                            "learn about his interests outside of work."
                        ),
                        subject_perspective=(
                            "You've given your number to Christina, a new team member "
                            "at the pharmaceutical company you work for. Christina "
                            "wants to chat about work and get to know you better."
                        ),
                        user_goal=(
                            "Understand Jake's role at the company and his interests "
                            "to build a friendly working relationship."
                        ),
                        is_user_initiated=True,
                    ),
                    ConversationScenario(
                        user_perspective=(
                            "After meeting Avery in photography class and exchanging "
                            "numbers, you start texting to potentially collaborate on "
                            "a project. Ask about their favorite subjects, tips, and "
                            "projects to discuss further."
                        ),
                        subject_perspective=(
                            "You met Joe in photography class and asked for his "
                            "number. Joe is excited to talk about photography with "
                            "you, discussing favorite subjects, tips, and projects. "
                            "You want to potentially collaborate on a project."
                        ),
                        user_goal=(
                            "Engage with Avery in a discussion about photography, "
                            "learning about their interests and projects to explore "
                            "collaboration opportunities."
                        ),
                        is_user_initiated=False,
                    ),
                    ConversationScenario(
                        user_perspective=(
                            "Being new to the neighborhood, you start texting your "
                            "neighbor Jordan to get acquainted. Ask about local "
                            "events, the best dining spots, and any helpful tips for "
                            "newcomers."
                        ),
                        subject_perspective=(
                            "David, your new neighbor, has reached out to you over "
                            "text. David is eager to chat about local events, dining "
                            "spots, and tips for newcomers."
                        ),
                        user_goal=(
                            "Learn about the community and build a friendly "
                            "relationship with Jordan."
                        ),
                        is_user_initiated=True,
                    ),
                    ConversationScenario(
                        user_perspective=(
                            "At a math conference, you start texting Riley, a fellow "
                            "attendee interested in topological algebra and category "
                            "theory. Get to know Riley better and discuss their "
                            "research, favorite mathematicians, and future projects."
                        ),
                        subject_perspective=(
                            "After meeting you at a math conference, Eden is eager to "
                            "chat about topological algebra and category theory. Eden "
                            "wants to learn about your research and interests in the "
                            "field."
                        ),
                        user_goal=(
                            "Dive into a discussion about topological algebra and "
                            "category theory with Riley, learning about their research "
                            "and interests to build a professional connection."
                        ),
                        is_user_initiated=False,
                    ),
                    ConversationScenario(
                        user_perspective=(
                            "After meeting Finn, an avid hiker, at a social event, "
                            "you start texting to share hiking experiences. Ask about "
                            "their favorite trails, future hiking plans, and advice "
                            "for beginners."
                        ),
                        subject_perspective=(
                            "You met Alex at a social event and exchanged numbers to "
                            "chat about hiking. Alex wants to learn about your "
                            "favorite trails, future hiking plans, and advice for "
                            "beginners."
                        ),
                        user_goal=(
                            "Discuss hiking with Finn, discovering their experiences "
                            "and gaining advice."
                        ),
                        is_user_initiated=True,
                    ),
                ]
            ]
        )
    )

    sampled_interests = random.sample(user.interests, min(2, len(user.interests)))

    previous_scenarios = await get_previous_scenarios(user_id)

    class GenerateConversationScenarioPrompt(BaseModel):
        name: str
        age: str
        occupation: str
        interests: list[str]
        previous_user_scenarios: list[str]

    prompt_data = GenerateConversationScenarioPrompt(
        name=user.name,
        age=user.age,
        occupation=user.occupation,
        interests=sampled_interests,
        previous_user_scenarios=previous_scenarios,
    ).model_dump_json()

    print(prompt_data)

    scenario = await llm.generate(
        schema=ConversationScenario,
        model=llm.MODEL_GPT_4,
        system=system_prompt,
        prompt=prompt_data,
    )

    return scenario


async def _generate_subject_base(scenario, name):
    def validate_name(v):
        if v != name:
            raise ValueError(f"Name must be {name}")
        return v

    class SubjectBasePersona(BasePersona):
        name: Annotated[str, AfterValidator(validate_name)]

    system_prompt = (
        f"Generate a persona for {name}, an autistic individual in the provided "
        "scenario (referred to as 'you'). Fill in the persona details based on the "
        "information provided in the scenario. Generate any missing information to "
        "create a realistic and relatable character. Respond with a JSON object "
        "containing the keys 'name' (string), 'age' (age range), 'occupation', and "
        "'interests' (list of strings)."
    )

    response = await llm.generate(
        schema=SubjectBasePersona,
        model=llm.MODEL_GPT_4,
        system=system_prompt,
        prompt=scenario,
    )

    return response


async def _generate_subject_persona_from_base(subject: BasePersona):
    class PersonaDescriptionResponse(BaseModel):
        persona: str

    system_prompt = (
        "As a persona generator, your task is to generate a system prompt that will "
        "be used to make ChatGPT embody a persona based on the provided information. "
        "The persona is an autistic individual who struggles to communicate "
        "effectively with others. The persona should exhibit the vocal styles "
        "of an autistic person and should be ignorant of the needs of neurotypical "
        "individuals due to a lack of experience with them. The persona should be a "
        "realistic and relatable character who is messaging over text with another "
        "person. Respond with a JSON object containing the key 'persona' and the "
        "system prompt as the value. The prompt should start with 'You are "
        f"{subject.name}...'."
    )

    prompt_data = subject.model_dump_json()

    response = await llm.generate(
        schema=PersonaDescriptionResponse,
        model=llm.MODEL_GPT_4,
        system=system_prompt,
        prompt=prompt_data,
    )

    return Persona(**subject.model_dump(), description=response.persona)


async def generate_subject_persona(scenario, subject_name):
    subject_info = await _generate_subject_base(scenario, subject_name)

    subject_persona = await _generate_subject_persona_from_base(subject_info)

    return subject_persona


# async def generate_conversation_info(user_id: ObjectId, user: Persona):
#     subject_name = random.choice(Provider.first_names)
#     scenario = await generate_conversation_scenario(user_id, user, subject_name)
#     subject_persona = await _generate_subject_persona(
#         scenario.subject_scenario, subject_name
#     )

#     return ConversationInfo(
#         scenario=scenario,
#         user=user,
#         subject=subject_persona,
#     )
