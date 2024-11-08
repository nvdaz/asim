from pydantic import BaseModel

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


def format_messages_context_short(
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


def format_messages_context_long(
    messages_raw: list[ChatMessage | InChatFeedback], recipient: str
) -> str:
    messages: list[ChatMessage] = [
        msg for msg in messages_raw if isinstance(msg, ChatMessage)
    ]

    if len(messages) == 0:
        return ""

    return "\n".join([f"{msg.sender}: {msg.content}" for msg in messages])


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
Keep the conversation going naturally. Do not end the conversation. Introduce new
topics if the conversation is dying.

Output format: Output a json of the following format:
{{
"message": "<{name}'s utterance>",
}}
"""

action_begin = """
Begin the conversation between {name} and {other_name}.
"""

action_continue = """
Here is the conversation so far between {name} and {other_name}:
{conversation}

{objective_prompt}

In {name}'s voice, generate their response to {other_name}'s last message in the convo above. The response should be such that the conversation is personalized for {other_name} based on the information provided about them in the scenario.
"""

# scenario is the situation in which the conversation is taking place (i.e. gloucester trip)
prompt = """
{scenario}

{action}
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

    conversation_context = format_messages_context_long(messages, recipient_name)

    system_prompt = system_prompt_template.format(name=sender_name)

    action_prompt = action_begin if len(messages) == 0 else action_continue

    action = action_prompt.format(
        name=sender_name,
        other_name=recipient_name,
        conversation=conversation_context,
        objective_prompt=(
            objective_prompt.format(name=sender_name)
            + "\n"
            + "IMPORTANT: You MUST follow these instructions when generating the "
            "response. These insights are crucial to the conversation.\n"
            if objective_prompt
            else ""
        ),
    )

    prompt_data = prompt.format(
        name=sender_name,
        other_name=recipient_name,
        conversation=conversation_context,
        scenario=f"""
Here is the scenario:
{agent_name} wants to plan a trip with {user.name}. Both of them are colleagues at work who recently met each other. They work at Google and live in New York. {user.name} is 26 years old, male (he/him) and a Computer Scientist. {user.name} is originally from Boston, MA. Politically, {user.name} is a liberal. {user.name} is vegetarian, and likes to bike and run a lot. {user.name} likes Orlando, Florida because of its sunny weather, theme parks and close proximity to beaches. In this conversation, {agent_name} will float the idea of planning a trip to Orlando, Florida, discuss details/itinerary and convince {user.name} to join them.
""",
        action=action,
    )

    response = await llm.generate(
        schema=Message,
        model=llm.Model.GPT_4o,
        system=system_prompt,
        prompt=prompt_data,
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
        model=llm.Model.GPT_4o,
        system=system_prompt,
        prompt=prompt_data,
    )

    return res.send_message
