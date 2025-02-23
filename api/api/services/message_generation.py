from datetime import datetime

from pydantic import BaseModel

from api.schemas.chat import ChatMessage, InChatFeedback
from api.schemas.user import (
    UserPersonalizationOptions,
)

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

    return "\n".join([f"{msg.sender}: {msg.content}" for msg in messages[-20:]])


def format_messages_context_m(
    messages_raw: list[ChatMessage | InChatFeedback], recipient: str
) -> str:
    messages: list[ChatMessage] = [
        msg for msg in messages_raw if isinstance(msg, ChatMessage)
    ]

    if len(messages) == 0:
        return ""

    return "\n".join([f"{msg.sender}: {msg.content}" for msg in messages[-4:]])


system_prompt_template = """
You are a conversation predictor, who specializes in predicting the next message in a
conversation between two people.

Keep the predicted message short and natural-sounding, like text messages typically are.

Output format: Output a json of the following format:
{{
"message": "<{name}'s utterance>"
}}
"""

action_begin = """
Begin the conversation between {name} and {other_name}.
In {name}'s voice, start the conversation by sending a message to {other_name}.
"""

action_continue = """
Here is the conversation so far between {name} and {other_name}:
{conversation}

{objective_prompt}

In {name}'s voice, generate their response to {other_name}'s last message in the convo above.

{other}
"""

# scenario is the situation in which the conversation is taking place (e.g. gloucester trip)
prompt = """
{scenario}
It's currently {date}.

{action}

{specific_instructions}

{agent_style}
"""


def dump_message_list(
    messages: list[ChatMessage],
) -> str:
    return "\n".join([f"{msg.sender}: {msg.content}" for msg in messages[-3:]])


def get_personalization_options(
    input_data: UserPersonalizationOptions, personalize: bool
):
    if not personalize:
        return UserPersonalizationOptions(
            name="Frank",
            pronouns="he/him",
            topic="astronomy",
        )
    else:
        return input_data


class Message(BaseModel):
    message: str


async def generate_message(
    scenario: str,
    pers: UserPersonalizationOptions,
    agent_name: str,
    user_sent: bool,
    messages: list[ChatMessage | InChatFeedback],
    objective_prompt: str | None = None,
    bypass_objective_prompt_check=False,
) -> str:
    sender_name = pers.name if user_sent else agent_name
    recipient_name = agent_name if user_sent else pers.name

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
        other=(
            "See the examples above to generate the response."
            if (objective_prompt or bypass_objective_prompt_check)
            else f"The response should be such that the conversation is engaging for {pers.name}, based on all the information provided about them in the scenario."
        ),
    )

    current_date = datetime.now()
    formatted_date = current_date.strftime("%a %d %b %Y, %I:%M%p")

    prompt_data = prompt.format(
        name=sender_name,
        other_name=recipient_name,
        conversation=conversation_context,
        scenario=(
            f"Here is the scenario: {scenario.format(user=pers.name, agent=agent_name)}"
            if not (objective_prompt or bypass_objective_prompt_check)
            else ""
        ),
        action=action,
        specific_instructions=(
            f"Make sure to: 1. Keep {sender_name}'s response short (1-4 lines) but friendly, natural-sounding and use small letters, as done in an SMS message. 2. Slowly unfold the conversation, so don't talk about many different things in one message. 3. Don't act like you know all the information about {recipient_name} (by not saying I know about you that...), as if your interests matched naturally with them."
            if not user_sent
            else f"Make sure to: 1. Keep {sender_name}'s response short (1-4 lines) but friendly, natural-sounding and use small letters, as done in an SMS message. 2. Slowly unfold the conversation, so don't talk about many different things in one message. "
        ),
        agent_style=(
            f"{pers.name} is personable and friendly without being overly enthusiastic. They speak naturally and human-like."
            if user_sent
            else f"{agent_name} is personable and friendly without being overly enthusiastic. They speak naturally and human-like. They do not use figurative language or emojis."
        ),
        date=formatted_date,
    ).strip()

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
"send_message": <true if {name} would send a message, false otherwise>
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
