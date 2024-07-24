import random
from typing import Annotated

from bson import ObjectId
from pydantic import AfterValidator, BaseModel

from api.db.conversations import get_previous_info
from api.schemas.conversation import (
    ConversationElement,
    ConversationScenario,
    MessageElement,
    message_list_adapter,
)
from api.schemas.persona import BasePersona, Persona

from . import llm


async def generate_conversation_scenario(
    user_id: ObjectId, user: Persona, agent_name: str
) -> ConversationScenario:
    system_prompt = (
        "As a scenario generator, your task is to generate a casual conversational "
        f"scenario that could happen over a text messaging app based on {user.name}'s "
        "profile. The scenario should be a specific situation that could happen "
        f"between {user.name} and an unfamiliar person {agent_name} over text "
        "messaging. The scenario should be realistic and relatable. Respond with a "
        f"JSON object. The 'user_perspective' key should be a string describing "
        f"{user.name}'s perspective in the scenario (use second person pronouns to "
        f"refer to {user.name}), the 'agent_perspective' key should be a string "
        f"describing {agent_name}'s perspective (use second person pronouns to refer "
        f"to {agent_name}), the 'user_goal' key should be a string describing "
        f"{user.name}'s objective in the scenario (begin with an action verb, e.g., "
        "'Convince', 'Explain', 'Find out' and use second person pronouns to refer to "
        f"{user.name}), and the 'is_user_initiated' key should be a boolean that is "
        f"true if the first message would be sent by {user.name} and false if it would "
        f"be sent by {agent_name}. Do not generate scenarios that involve "
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
                        agent_perspective=(
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
                        agent_perspective=(
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
                        agent_perspective=(
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
                        agent_perspective=(
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
                        agent_perspective=(
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
                        agent_perspective=(
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

    previous_infos = await get_previous_info(user_id, "level")

    previous_scenarios = [info.scenario.user_perspective for info in previous_infos]

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

    scenario = await llm.generate(
        schema=ConversationScenario,
        model=llm.Model.GPT_4,
        system=system_prompt,
        prompt=prompt_data,
    )

    return scenario


async def generate_conversation_topic(user_id: ObjectId, interests: list[str]) -> str:
    previous_info = await get_previous_info(user_id, "playground")

    previous_topics = set(info.topic for info in previous_info)

    unused_interests = [
        interest for interest in interests if interest not in previous_topics
    ]

    if len(unused_interests) == 0:
        unused_interests = interests

    return random.choice(unused_interests)


async def _generate_agent_base(scenario, name):
    def validate_name(v):
        if v != name:
            raise ValueError(f"Name must be {name}")
        return v

    class AgentBasePersona(BasePersona):
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
        schema=AgentBasePersona,
        model=llm.Model.GPT_4,
        system=system_prompt,
        prompt=scenario,
    )

    return response


async def _generate_agent_persona_from_base(agent: BasePersona):
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
        f"{agent.name}...'."
    )

    prompt_data = agent.model_dump_json()

    response = await llm.generate(
        schema=PersonaDescriptionResponse,
        model=llm.Model.GPT_4,
        system=system_prompt,
        prompt=prompt_data,
    )

    return Persona(
        **agent.model_dump(),
        description=(
            f"{response.persona} DO NOT mention how autism affects your communication."
        ),
    )


async def generate_agent_persona(scenario, agent_name):
    agent_info = await _generate_agent_base(scenario, agent_name)

    agent_persona = await _generate_agent_persona_from_base(agent_info)

    return agent_persona


class GenerateConversationTopicResult(BaseModel):
    topic: str | None


async def determine_conversation_topic(
    elements: list[ConversationElement],
) -> str | None:
    system_prompt = (
        "Determine the topic of the conversation happening between the two individuals "
        "from the provided messages. The conversation topic is a string that describes "
        "the main subject of the conversation. The topic should be a specific subject "
        "that the two individuals are discussing. Respond with a JSON object with the "
        "key 'topic' and the topic as the value in title case. If the topic cannot be "
        "determined, set 'topic' to null."
    )

    messages = [
        element.content for element in elements if isinstance(element, MessageElement)
    ]

    prompt_data = str(message_list_adapter.dump_json(messages))

    response = await llm.generate(
        schema=GenerateConversationTopicResult,
        model=llm.Model.GPT_4,
        system=system_prompt,
        prompt=prompt_data,
    )

    return response.topic
