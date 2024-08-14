import asyncio

from api.schemas.conversation import (
    BaseFeedback,
    ConversationData,
    Feedback,
    Message,
    MessageElement,
    dump_message_list,
)
from api.schemas.persona import UserPersona

from . import llm
from .message_generation import generate_message


def _extract_messages_for_feedback(conversation: ConversationData):
    messages = [
        elem.content
        for elem in conversation.elements
        if isinstance(elem, MessageElement)
    ]
    start = 0
    # take all messages since the user's last message
    for i in reversed(range(len(messages) - 2)):
        if not messages[i].user_sent:
            start = i + 1
            break

    return messages[start:]


async def generate_feedback_base(
    user: UserPersona,
    conversation: ConversationData,
    prompt: str,
    examples: list[tuple[list[Message], BaseFeedback]],
) -> BaseFeedback:
    agent = conversation.agent
    messages = _extract_messages_for_feedback(conversation)

    examples_str = "\n\n".join(
        [
            dump_message_list(messages, user.name, agent.name)
            + "\n"
            + BaseFeedback(
                title=fb.title, body=fb.body.format(agent=agent.name)
            ).model_dump_json()
            for messages, fb in examples
        ]
    )

    system_prompt = (
        "You are a social skills coach. Your task is to provide feedback on the "
        f"ongoing conversation between the user and {agent.name}. The conversation is "
        f"happening over text. {prompt}\nUse second person pronouns to address the "
        "user directly. Respond with a JSON object with the key 'title' containing the "
        "title (less than 50 characters) of your feedback, the key 'body' containing "
        "the feedback (less than 100 words). DO NOT tell the user to send a specific "
        "message."
    )

    prompt_data = (
        examples_str + "\n\n\n" + dump_message_list(messages, user.name, agent.name)
    )

    return await llm.generate(
        schema=BaseFeedback,
        model=llm.Model.GPT_4,
        system=system_prompt,
        prompt=prompt_data,
    )


async def generate_feedback(
    user: UserPersona,
    conversation: ConversationData,
    prompt: str,
    instructions: str,
    examples: list[tuple[list[Message], BaseFeedback]],
) -> Feedback:
    all_messages = [
        elem.content
        for elem in conversation.elements
        if isinstance(elem, MessageElement)
    ]

    base, follow_up = await asyncio.gather(
        generate_feedback_base(user, conversation, prompt, examples=examples),
        generate_message(
            user_sent=True,
            user=user,
            agent=conversation.agent,
            messages=all_messages,
            scenario=conversation.info.scenario,
            instructions=instructions,
        ),
    )

    return Feedback(
        title=base.title,
        body=base.body,
        follow_up=follow_up,
    )
