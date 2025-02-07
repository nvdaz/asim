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
        f"expert on {topic}. "
        + "\nExample for topic 'anything space': "
        + GeneratedTopic(
            introduction="Tufts University is hosting an event where you can ask "
            f"anything about space to {agent}, who is an expert in the field. "
            f"Feel free to ask {agent} anything you want to know about space."
        ).model_dump_json()
        + "\nExample for topic 'sports': "
        + GeneratedTopic(
            introduction=f"As part of an event, {agent} is on campus at Tufts "
            f"University. You can ask {agent} anything you want to know about sports."
        ).model_dump_json(),
    )

    return result.introduction
