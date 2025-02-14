from pydantic import BaseModel

from . import llm


class GeneratedTopic(BaseModel):
    introduction: str


async def generate_topic_message(agent: str, topic: str):
    result = await llm.generate(
        schema=GeneratedTopic,
        model=llm.Model.GPT_4o,
        system="You are facilitating a casual, engaging conversation between a user and an expert on a specific topic. "
        "The setting is relaxed and informal, allowing for open dialogue and natural curiosity. "
        "Create a welcoming introduction that sets the tone for this conversation. "
        "Respond with a JSON object containing an 'introduction' key and the introduction text as its value.",
        prompt=f"The user will engage in an informal discussion with {agent}, a distinguished expert in {topic}. "
        + "\nExample for topic 'anything space': "
        + GeneratedTopic(
            introduction=f"Meet {agent}, an accomplished expert ready to share their "
            "knowledge and insights about space. In this casual conversation, you can "
            "share your own experiences, discuss ideas, or ask any questions that come to mind."
        ).model_dump_json()
        + "\nExample for topic 'sports': "
        + GeneratedTopic(
            introduction="Today, you will have the opportunity to have a casual chat "
            f"with {agent}, an experienced professional in the world of sports. Feel "
            "free to share your thoughts, discuss your favorite moments, or explore any "
            "aspects of the subject that spark your interest."
        ).model_dump_json(),
    )

    return result.introduction
