from pydantic import BaseModel

from api.schemas.chat import ChatMessage, InChatFeedback
from api.schemas.user import (
    LocationOptions,
    PlanVacationScenarioOptions,
    UserData,
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
It's currently early December 2024.

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
            gender="Male",
            age="30",
            location=LocationOptions(city="Phoenix", country="USA"),
            company="American Airlines",
            occupation="Airline Pilot",
            interests="Hiking on mountains, reading fiction books, barbecuing with "
            "friends, playing multiplayer video games, watching stand-up comedy, going "
            "to the beach, trying new foods, learning about history",
            scenario=PlanVacationScenarioOptions(
                vacation_destination="Gloucester, Massachusetts",
                vacation_explanation="World-famous beaches, surfing on clear blue "
                "water, local cuisine, friendly locals, fishing, historic buildings, "
                "whale watching, seafood",
            ),
            personality=["optimistic", "open-minded", "supportive", "friendly"],
        )
    else:
        return input_data


def get_scenario(data: UserPersonalizationOptions, agent_name: str) -> str:
    scenario = (
        f"{agent_name} wants to plan a trip with {data.name}. Both of "
        f"them are colleagues at {data.company} where {data.name} "
        f"works as a {data.occupation}. They are both new to the company and recently "
        f"met each other. {data.name} is {data.age} years old and identifies as a "
        f"{data.gender}. {data.name} is originally from {data.location.city}, "
        f"{data.location.country}. {data.name}'s interests are: "
        f"\"{data.interests}\". Here are {data.name}'s personality traits: "
        f"{', '.join(data.personality)}. "
    )

    scenario += (
        f"{data.name}'s dream vacation spot is {data.scenario.vacation_destination}. "
        f'They say they like it because of "{data.scenario.vacation_explanation}". '
        f"In this conversation, {agent_name} will float the idea of planning a trip to "
        f"{data.scenario.vacation_destination}, discuss details/itinerary and convince "
        f"{data.name} to join them. {agent_name} should use information about "
        f"{data.name}'s interests and personality to make the conversation engaging "
        f"and convincing but act natural and don't overdo it. {agent_name} will use a "
        "casual tone."
    )

    return scenario


class Message(BaseModel):
    message: str


async def generate_message(
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
            else f"The response should be such that the conversation is engaging and enjoyable for {pers.name}, based on all the information provided about them in the scenario."
        ),
    )

    scenario = get_scenario(pers, agent_name)

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
            f"Make sure to: 1. Keep {sender_name}'s response short (1-2 lines), natural-sounding and use small letters, as done in an SMS message. 2. Slowly unfold the conversation, so don't talk about many different things in one message. 3. Don't act like you know all the information about {recipient_name} (by not saying I know about you that...), as if your interests matched naturally with them. 4. Use direct language and avoid figurative language and non-literal emojis."
            if not user_sent
            else ""
        ),
        agent_style=(
            ""
            if user_sent
            else f"{agent_name} should use simple and straightforward language in their message. Avoid emojis unless necessary, only using very simple ones."
        ),
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
