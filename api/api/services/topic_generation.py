from pydantic import BaseModel

from . import llm


class GeneratedTopic(BaseModel):
    introduction: str


async def generate_topic_message(agent: str, topic: str):
    result = await llm.generate(
        schema=GeneratedTopic,
        model=llm.Model.GPT_4o,
        system="You are introducing a user to a scenario where they are talking to an "
        "expert about a given topic. The user can ask whatever they want to know about "
        "the topic to the expert. Generate an introduction to the conversation for the "
        "user. Respond with a JSON object with a key 'introduction' and a value that "
        "is the introduction to the conversation.",
        prompt=f"The person will have the opportunity to chat with {agent}, who is an "
        f"expert on {topic}. Example for topic 'anything space': "
        + GeneratedTopic(
            introduction=f"{agent} is passionate about astronomy. Ask them anything "
            "you want to know about black holes, the solar system, cosmic events, or "
            "any other fascinating aspects of the universe."
        ).model_dump_json(),
    )

    return result.introduction
