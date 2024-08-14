from typing import Annotated, Sequence

from pydantic import AfterValidator, BaseModel

from api.schemas.conversation import (
    BaseConversationScenario,
    Message,
    PlaygroundConversationScenario,
    dump_message_list,
)
from api.schemas.persona import AgentPersona, UserPersona

from . import llm


def _format_example(
    example: tuple[str, str] | str,
) -> str:
    if isinstance(example, tuple):
        return f"'{example[0]}' -> '{example[1]}'"
    else:
        return f"'{example}'"


async def generate_message(
    user_sent: bool,
    user: UserPersona,
    agent: AgentPersona,
    messages: list[Message],
    scenario: BaseConversationScenario,
    instructions: str | None = None,
    examples: Sequence[tuple[str, str] | str] | None = None,
) -> str:
    user_name = f"{user.name} (the user)" if user.name else "the user"

    sender_name = user_name if user_sent else agent.name
    recipient_name = agent.name if user_sent else user_name

    def validate_sender(sender: str) -> str:
        if sender != sender_name:
            raise ValueError(f"Sender must be {sender_name}")

        return sender

    class MessageWithRole(BaseModel):
        sender: Annotated[str, AfterValidator(validate_sender)]
        message: str

    scenario_perspective = (
        scenario.user_perspective if user_sent else scenario.agent_perspective
    )

    prelude = "\n".join(
        filter(
            None,
            [
                user.description if user_sent else agent.description,
                scenario_perspective,
                (
                    f"Tailor your message to the user's culture: {user.culture}"
                    if (
                        isinstance(scenario, PlaygroundConversationScenario)
                        and not user_sent
                    )
                    else None
                ),
            ],
        )
    )

    max_len = 40 if user_sent else 60

    system_prompt = (
        f"{prelude}\nYou ({sender_name}) are chatting over text with {recipient_name}. "
        f"Keep your messages under {max_len} words and appropriate for a text "
        "conversation. ALWAYS provide detailed information and DO NOT end the "
        "conversation. DO NOT try to start any external conversations or schedule any "
        f"meetings. You are {sender_name}, and are writing to {recipient_name}. "
        "YOU ARE NOT AN AI. Respond with a JSON object containing the key 'message' "
        f"with your message as the value and the key 'sender' with '{sender_name}' as "
        "the value. Respond ONLY with your next message. Do not include previous "
        "messages in your response. STAY ON TOPIC. DO NOT reference external "
        "information."
    )

    examples_str = (
        "\nIMPORTANT: I MUST MODEL MY RESPONSES AFTER THESE EXAMPLES.\n"
        "<example_responses>\n"
        + "\n".join([_format_example(example) for example in examples]).format(
            user=user.name, agent=agent.name
        )
        + "\n</example_responses>\n"
        if examples
        else None
    )

    prompt_data = (
        (
            "[CONVERSATION START]"
            if len(messages) == 0
            else dump_message_list(messages[-12:], user.name, agent.name)
        )
        + f"\n{sender_name}:"
        + "\n<instructions>"
        + (f"\n{instructions}\n{examples_str or ''}\n" if instructions else "")
        + f"\nI am {sender_name}.\n</instructions>"
        + f"\nRESPOND AS {sender_name.upper()}. IMPORTANT: FOLLOW THE INSTRUCTIONS "
        "CAREFULLY TO ENSURE YOUR MESSAGE IS APPROPRIATE."
    )

    response = await llm.generate(
        schema=MessageWithRole,
        model=llm.Model.CLAUDE_3_SONNET,
        system=system_prompt,
        prompt=prompt_data,
        temperature=0.8,
    )

    return response.message
