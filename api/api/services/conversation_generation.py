import random
from typing import Annotated

from bson import ObjectId
from pydantic import AfterValidator, BaseModel

from api.db.conversations import get_previous_info
from api.levels.all import get_base_level_scenario
from api.levels.seed import LevelConversationScenarioSeed
from api.schemas.conversation import (
    ConversationElement,
    LevelConversationScenario,
    LevelConversationStage,
    MessageElement,
    dump_message_list,
)
from api.schemas.persona import AgentBasePersona, AgentPersona, UserPersona

from . import llm


async def adapt_scenario_to_user(
    scenario: LevelConversationScenarioSeed, user: UserPersona, agent_name: str
) -> LevelConversationScenario:
    system_prompt = (
        "As a scenario adapter, your task is to adapt the provided scenario to be "
        "tailored to the user's profile. Add details to the scenario that would make "
        "it more relatable and engaging for the user. Mention how the user and the "
        "agent met. Respond with a JSON object "
        "containing the keys 'user_perspective', 'agent_perspective', 'user_goal', "
        "and 'is_user_initiated'. The 'user_perspective' key should be a string "
        "describing the user's perspective in the scenario (use second person pronouns "
        "to refer to the user), the 'agent_perspective' key should be a string "
        f"instructing {agent_name} (use SECOND PERSON PRONOUNS to refer to "
        f"{agent_name}), the 'user_goal' key should be a string describing the "
        "user's objective in the scenario (begin with an action verb, e.g., "
        "'Convince', 'Explain', 'Find out' and use second person pronouns to refer to "
        "the user), and the 'is_user_initiated' key should be a boolean that is true "
        "if the first message would be sent by the user and false if it would be sent "
        f"by {agent_name}. Do not generate scenarios that involve significant external "
        "elements, such as finding a bug in a software program (it is not possible to "
        "send the code). Generate SPECIFIC scenarios. DO NOT use uncertain language or "
        "offer choices."
    )

    prompt_data = (
        f"The user is {user.name} and is {user.age} years old. The user's "
        f"occupation is {user.occupation} and their interests include "
        f"{', '.join(random.sample(user.interests, 2))}. The agent is {agent_name}."
        "Here is the scenario to adapt:\n"
        f"{scenario.model_dump_json()}"
    )

    return await llm.generate(
        schema=LevelConversationScenario,
        model=llm.Model.GPT_4,
        system=system_prompt,
        prompt=prompt_data,
    )


async def generate_level_conversation_scenario(
    user: UserPersona, agent_name: str, stage: LevelConversationStage
) -> LevelConversationScenario:
    scenario_seed = get_base_level_scenario(stage)

    if scenario_seed.adapt:
        scenario = await adapt_scenario_to_user(scenario_seed, user, agent_name)
    else:
        scenario = LevelConversationScenario(**scenario_seed.model_dump())

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

    class NamedAgentBasePersona(AgentBasePersona):
        name: Annotated[str, AfterValidator(validate_name)]

    system_prompt = (
        f"Generate a persona for {name}, an individual in the provided scenario "
        "(referred to as 'you'). Fill in the persona details based on the information "
        "provided in the scenario. Generate any missing information to create a "
        "realistic and relatable character. Respond with a JSON object containing the "
        "keys 'name' (string), 'age' (age range), 'occupation', and 'interests' (list "
        "of strings)."
    )

    response = await llm.generate(
        schema=NamedAgentBasePersona,
        model=llm.Model.GPT_4,
        system=system_prompt,
        prompt=scenario,
    )

    return response


async def _generate_agent_persona_from_base(agent: AgentBasePersona):
    class PersonaDescriptionResponse(BaseModel):
        persona: str

    system_prompt = (
        "As a persona generator, your task is to generate a system prompt that will "
        "be used to make ChatGPT embody a persona based on the provided information. "
        "The persona should be a realistic and relatable character who is messaging "
        "over text with another person. Respond with a JSON object containing the key "
        "'persona' and the system prompt as the value. The prompt should start with "
        f"'You are {agent.name}...'."
    )

    prompt_data = agent.model_dump_json()

    response = await llm.generate(
        schema=PersonaDescriptionResponse,
        model=llm.Model.GPT_4,
        system=system_prompt,
        prompt=prompt_data,
    )

    return AgentPersona(
        **agent.model_dump(),
        description=response.persona,
    )


async def generate_agent_persona(scenario, agent_name):
    agent_info = await _generate_agent_base(scenario, agent_name)

    agent_persona = await _generate_agent_persona_from_base(agent_info)

    return agent_persona


class GenerateConversationTopicResult(BaseModel):
    topic: str | None


async def determine_conversation_topic(
    elements: list[ConversationElement],
    user: UserPersona,
    agent: AgentPersona,
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

    prompt_data = dump_message_list(messages, user.name, agent.name)

    response = await llm.generate(
        schema=GenerateConversationTopicResult,
        model=llm.Model.GPT_4,
        system=system_prompt,
        prompt=prompt_data,
    )

    return response.topic


async def generate_agent_persona_from_topic(name: str, topic: str) -> AgentPersona:
    system_prompt = (
        f"Generate a persona for {name}, a notable figure in the field of {topic}. "
        "The persona should be engaging and interesting to someone who is interested "
        f"in {topic}. Respond with a JSON object containing the keys 'name' (string), "
        "'age' (age range), 'occupation', 'interests' (list of strings), and "
        f"'description' (string). The description should be a short blurb about {name} "
        f"and their work in the field of {topic}. Begin the description with 'You are "
        f"{name}...'."
    )

    return await llm.generate(
        schema=AgentPersona,
        model=llm.Model.GPT_4,
        system=system_prompt,
        prompt=topic,
    )
