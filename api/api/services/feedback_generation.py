from pydantic import BaseModel

from api.levels.states import FeedbackState, MessageInstructions
from api.schemas.conversation import (
    BaseFeedback,
    ConversationData,
    Feedback,
    Message,
    MessageElement,
    dump_message_list,
)
from api.schemas.persona import AgentPersona, UserPersona

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


def _extract_feedback_base_examples(
    examples: list[tuple[list[Message], Feedback]],
) -> list[tuple[list[Message], BaseFeedback]]:
    return [
        (messages, BaseFeedback(title=fb.title, body=fb.body))
        for messages, fb in examples
    ]


def _extract_follow_up_examples(
    examples: list[tuple[list[Message], Feedback]],
) -> list[tuple[str, ...] | str]:
    return [
        (*[message.message for message in messages], fb.follow_up)
        if fb.follow_up
        else (*[message.message for message in messages],)
        for messages, fb in examples
    ]


def _extract_explanation_examples(
    examples: list[tuple[list[Message], Feedback]],
) -> list[tuple[list[Message], str, str]]:
    return [
        (messages, fb.follow_up, fb.explanation)
        for messages, fb in examples
        if fb.explanation and fb.follow_up
    ]


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
        f"ongoing conversation between the user and {agent.name}, who is an autistic "
        f"individual. The conversation is happening over text. {prompt}\nUse second "
        "person pronouns to address the user directly. Respond with a JSON object with "
        "the key 'title' containing the title (less than 50 characters, starting with "
        "an interesting emoji) of your feedback, the key 'body' containing the "
        "feedback. Your feedback should be comprehensive and thoroughly explain the "
        "reasoning behind it. But it should be concise and to the point. DO NOT repeat "
        "the question! Analyze the user's message and provide feedback WITHOUT "
        "repeating the question. Use simple, straightforward language that a high "
        "school student would understand. DO NOT tell the user to send a specific "
        f"message. Even though {agent.name} is autistic, DO NOT mention autism in your "
        "feedback. We want to focus on making communication more empathetic, not "
        "anything else."
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


def _make_explanation_prompt(
    user: UserPersona,
    agent: AgentPersona,
    feedback: BaseFeedback,
    messages: list[Message],
    follow_up: str,
):
    messages_str = dump_message_list(messages, user.name, agent.name)

    return (
        f"<conversation>\n{messages_str}\n</conversation>\n"
        f"<feedback>\n{feedback.body}\n</feedback>\n"
        f"<revised>\n{follow_up}\n</revised>"
    )


class FeedbackExplanation(BaseModel):
    explanation: str


async def _generate_follow_up_explanation(
    user: UserPersona,
    conversation: ConversationData,
    feedback: BaseFeedback,
    follow_up: str,
    examples: list[tuple[list[Message], str, str]],
) -> str:
    agent = conversation.agent
    messages = _extract_messages_for_feedback(conversation)

    system_prompt = (
        "You are a social skills coach. Your task is to explain why the new question "
        "is an improvement over the original one. You are reviewing an ongoing "
        "conversation between the user and an autistic individual. The conversation is "
        "happening over text. The user has received feedback from you and a revised "
        'question (refer to it as "this"). Also refer to the user using second person '
        "pronouns. Provide an explanation for why the revised question is an "
        "improvement over the original one. Respond with a JSON object with key "
        "'explanation' containing the explanation (less than two sentences). "
    )

    examples_str = "\n\n".join(
        [
            "[PROMPT]:\n"
            + _make_explanation_prompt(
                user, agent, feedback, messages, follow_up
            ).format(user=user.name, agent=agent.name)
            + "\n[RESPONSE]:\n"
            + FeedbackExplanation(
                explanation=explanation.format(user=user.name, agent=agent.name)
            ).model_dump_json()
            for messages, follow_up, explanation in examples
        ]
    )

    prompt_data = (
        examples_str
        + "\n\n[PROMPT]:\n"
        + _make_explanation_prompt(user, agent, feedback, messages, follow_up)
    )

    response = await llm.generate(
        schema=FeedbackExplanation,
        model=llm.Model.GPT_4,
        system=system_prompt,
        prompt=prompt_data,
    )

    return response.explanation


async def generate_feedback(
    user: UserPersona, conversation: ConversationData, state: FeedbackState
) -> Feedback:
    all_messages = [
        elem.content
        for elem in conversation.elements
        if isinstance(elem, MessageElement)
    ]

    base = await generate_feedback_base(
        user,
        conversation,
        state.prompt,
        examples=_extract_feedback_base_examples(state.examples),
    )

    follow_up = await generate_message(
        user_sent=True,
        user=user,
        agent=conversation.agent,
        messages=all_messages,
        scenario=conversation.info.scenario,
        instructions=MessageInstructions(
            description=state.follow_up,
            examples=_extract_follow_up_examples(state.examples),
        ),
        feedback=base.body,
    )

    explanation = await _generate_follow_up_explanation(
        user,
        conversation,
        base,
        follow_up,
        _extract_explanation_examples(state.examples),
    )

    return Feedback(
        title=base.title,
        body=base.body,
        follow_up=follow_up,
        explanation=explanation,
    )
