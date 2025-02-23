from pydantic import BaseModel

from . import llm


class GeneratedTopic(BaseModel):
    introduction: str


async def generate_topic_message(agent: str, topic: str):
    result = await llm.generate(
        schema=GeneratedTopic,
        model=llm.Model.GPT_4o,
        system="You are facilitating a casual, engaging conversation between a user and a friend on a specific topic. "
        "The setting is relaxed and informal, allowing for open dialogue and natural curiosity. "
        "Create a welcoming introduction that sets the tone for this conversation. "
        "Respond with a JSON object containing an 'introduction' key and the introduction text as its value.",
        prompt=f"The user will engage in an informal discussion with {agent}, a friend "
        f"who is an enthusiast/has great knowledge of/expert in the following topic: {topic}. The reading/flow if the intro should be good."
        + "\nExample for topic 'anything space': "
        + GeneratedTopic(
            introduction=f"You recently became friends with {agent}, who is an "
            "enthusiast in astronomy. They are eager to share their knowledge and "
            "insights about space with you. In this informal conversation, you can share "
            "your own experiences, discuss ideas, or ask any questions that come to "
            "mind."
        ).model_dump_json()
        + "\nExample for topic 'sports': "
        + GeneratedTopic(
            introduction=f"You recently became friends with {agent}, who is a sports "
            "fanatic. They are eager to share their knowledge and insights about "
            "sports with you. In this informal conversation, you can share your own "
            "experiences, discuss ideas, or ask any questions that come to mind."
        ).model_dump_json(),
    )

    return result.introduction


class GeneratedScenario(BaseModel):
    scenario: str


async def generate_scenario_message(user: str, agent: str, topic: str):
    scenario = (
        f"{user} is eager to dive deeper into {topic}. {agent} is an enthusiast in "
        f"{topic} and {user}'s friend. In this conversation, {user} will talk to "
        f"{agent} about {topic}."
    )

    result = await llm.generate(
        schema=GeneratedScenario,
        model=llm.Model.GPT_4o,
        system="You are given an input JSON object. Ensure that the language flows "
        "properly. If so, you can return an object with the same 'scenario' key and "
        "the same text as its value. If not, rephrase it to make it more natural and "
        "return the new object. Respond with a JSON  containing a 'scenario' key.",
        prompt=GeneratedScenario(scenario=scenario).model_dump_json(),
    )

    return result.scenario
