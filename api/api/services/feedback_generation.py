import asyncio
from typing import Annotated

from pydantic import BaseModel, StringConstraints

from api.schemas.conversation import (
    ConversationData,
    Feedback,
    MessageElement,
    UserMessage,
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


class BaseFeedback(BaseModel):
    title: Annotated[str, StringConstraints(max_length=50)]
    body: Annotated[str, StringConstraints(max_length=600)]


async def generate_feedback_base(
    user: UserPersona,
    conversation: ConversationData,
    prompt: str,
) -> BaseFeedback:
    agent = conversation.agent
    messages = _extract_messages_for_feedback(conversation)

    examples = [
        (
            [
                UserMessage(message="What is software made of?"),
            ],
            BaseFeedback(
                title="Keep Questions Clear",
                body=(
                    "The question you asked was not clear and specific. It was vague "
                    "and open-ended, which can be confusing for autistic individuals. "
                    "To avoid misunderstandings, ask questions that are "
                    "straightforward and have a clear subject matter."
                ),
            ),
        ),
        (
            [
                UserMessage(
                    message="Break a leg in your performance today!",
                ),
            ],
            BaseFeedback(
                title="Avoid Idioms",
                body=(
                    "Using idioms like 'break a leg' can sometimes be confusing for "
                    "autistic individuals, as they may interpret the phrase literally. "
                    "Taylor interpreted your message literally and thought you wanted "
                    "them to get hurt instead of wishing them good luck. To avoid "
                    "misunderstandings, use clear, direct language."
                ),
            ),
        ),
    ]

    examples_str = "\n\n".join(
        [
            f"{dump_message_list(messages, 'User', 'Agent')}\n{fb.model_dump_json()}"
            for messages, fb in examples
        ]
    )

    system_prompt = (
        "You are a social skills coach. Your task is to provide feedback on the "
        f"ongoing conversation between the user and {agent.name}, who is an "
        f"autistic individual. The conversation is happening over text. {prompt}"
        "\nUse second person pronouns to address the uesr directly. Respond with "
        "a JSON object with the key 'title' containing the title (less than 50 "
        "characters) of your feedback, the key 'body' containing the feedback (less "
        "than 100 words). DO NOT tell the user to send a specific message."
        f"Examples:\n{examples_str}"
    )

    prompt_data = dump_message_list(messages, user.name, agent.name)

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
) -> Feedback:
    all_messages = [
        elem.content
        for elem in conversation.elements
        if isinstance(elem, MessageElement)
    ]

    base, follow_up = await asyncio.gather(
        generate_feedback_base(user, conversation, prompt),
        generate_message(
            user_sent=True,
            user=user,
            agent=conversation.agent,
            messages=all_messages,
            scenario=conversation.info.scenario,
            instructions=(instructions),
        ),
    )

    return Feedback(
        title=base.title,
        body=base.body,
        follow_up=follow_up,
    )
