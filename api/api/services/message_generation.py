from pydantic import BaseModel

from api.levels.states import MessageInstructions
from api.schemas.chat import ChatMessage, InChatFeedback
from api.schemas.user import UserData

from . import llm


def _format_example(
    example: tuple[str, ...] | str,
) -> str:
    if isinstance(example, tuple):
        return " -> ".join([f"'{msg}'" for msg in example])
    else:
        return f"'{example}'"


def format_messages_context(
    messages_raw: list[ChatMessage | InChatFeedback], recipient: str
) -> str:
    messages: list[ChatMessage] = [
        msg for msg in messages_raw if isinstance(msg, ChatMessage)
    ]

    if len(messages) == 0:
        return ""

    if messages[-1].sender == recipient:
        i = len(messages) - 1

        while i >= 0 and messages[i].sender == recipient:
            i -= 1

        while i >= 0 and messages[i].sender != recipient:
            i -= 1

        return "\n".join([f"{msg.sender}: {msg.content}" for msg in messages[i + 1 :]])
    else:
        i = len(messages) - 1

        while i >= 0 and messages[i].sender != recipient:
            i -= 1

        while i >= 0 and messages[i].sender == recipient:
            i -= 1

        return "\n".join([f"{msg.sender}: {msg.content}" for msg in messages[i + 1 :]])


def _format_instructions(instructions: MessageInstructions | None) -> str:
    if not instructions:
        return ""

    examples_str = (
        (
            "IMPORTANT: I MUST MODEL MY RESPONSE AFTER THE EXAMPLES BELOW.\n"
            "<example_responses>\n"
            + "\n".join([_format_example(example) for example in instructions.examples])
            + "\n</example_responses>\n"
        )
        if instructions.examples
        else ""
    )

    return f"\n{instructions.description}\n{examples_str}\n"


system_prompt_template = """
You are a conversation predictor, who specializes in predicting the next message in a
conversation between two people.

They are relaxed and casual, using incomplete thoughts, sentence fragments, hesitations,
and random asides as they speak. They use everyday humor that is off-the-cuff, awkward,
and imperfect. Never use witty jokes, metaphors, similies, or clever wordplay. Never
use thought-out or planned humor.

Keep the predicted message under 5 sentences, but you should aim for just 2-3 sentences.

Remember, the two individuals are having a casual conversation. They talk like humans,
not like chatbots, so their conversation is not always logical or coherent. They may
stumble over their words, repeat themselves, or change the subject abruptly. Take on
{name}'s voice and perspective, only using information that they would know. Focus on
using their specific personal details to drive the conversation. Don't use any
information that they wouldn't know. Ask clarifying questions when {name} would be
confused.

People use spontaneous tangents, filler words, misunderstandings, and interjections to
keep it real. They use varied sentence length and structure. They may hesitate,
misunderstand, and aren't always clear. Use simple language, aiming for a Flesch
reading score of 80 or higher. Avoid jargon except where necessary. Generally avoid
adjectives, adverbs, and emojis.

Change the topic when appropriate. Do not plan any events outside of the conversation.

Output format: Output a json of the following format:
{{
"message": "<{name}'s utterance>",
}}
"""

prompt = """
{context}

{action}

Reply using {name}'s voice. Do not copy the other person's style or language. That would
be unrealistic.
"""

init_conversation_prompt = """
How would {name} initiate a conversation?
"""

continue_conversation_prompt = """
{name} and {other_name} are having a conversation.
How would {name} respond to {other_name}'s message to continue the conversation?
Here is their conversation so far:
{conversation}
"""


def dump_message_list(
    messages: list[ChatMessage],
) -> str:
    return "\n".join([f"{msg.sender}: {msg.content}" for msg in messages[-3:]])


class Message(BaseModel):
    message: str


async def generate_message(
    user: UserData,
    agent_name: str,
    user_sent: bool,
    messages: list[ChatMessage | InChatFeedback],
    objective_prompt: str | None = None,
) -> str:
    sender_name = user.name if user_sent else agent_name
    recipient_name = agent_name if user_sent else user.name

    conversation_context = format_messages_context(messages, recipient_name)

    system_prompt = system_prompt_template.format(name=sender_name)

    prompt_data = (
        prompt.format(
            action=(
                init_conversation_prompt.format(name=sender_name)
                if len(messages) == 0
                else continue_conversation_prompt.format(
                    name=sender_name,
                    other_name=recipient_name,
                    conversation=conversation_context,
                )
            ),
            name=sender_name,
            context="You are planning a trip to Gloucester, Massachusetts with your "
            "friend, and you are discussing the details of the trip.",
        )
        + "\n"
        + (
            "IMPORTANT: You MUST follow these instructions when generating the "
            "response. These insights are crucial to the conversation.\n"
            + objective_prompt.format(name=sender_name)
            + "\n"
            if objective_prompt
            else ""
        )
    )

    response = await llm.generate(
        schema=Message,
        model=llm.Model.GPT_4,
        system=system_prompt,
        prompt=prompt_data,
        temperature=1.0,
    )

    return response.message


decide_to_message_system = """
You are a conversation predictor, who specializes in predicting whether {name} would
send a follow-up message in a conversation to their last message. {name} should only
send a message if it is necessary to keep the conversation going or if they have
something important to say.

Output format: Output a json of the following format:
{{
"send_message": <true if {name} would send a message, false otherwise>,
}}
"""


class DecideToMessageOutput(BaseModel):
    send_message: bool


async def decide_whether_to_message(
    name: str,
    messages: list[ChatMessage],
) -> bool:
    system_prompt = decide_to_message_system.format(name=name)

    prompt_data = "Here is the conversation so far:\n" + dump_message_list(messages)

    res = await llm.generate(
        schema=DecideToMessageOutput,
        model=llm.Model.GPT_4,
        system=system_prompt,
        prompt=prompt_data,
    )

    return res.send_message
