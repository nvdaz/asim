from typing import Annotated

from pydantic import AfterValidator, BaseModel

from api.levels.states import MessageInstructions
from api.schemas.conversation import (
    BaseConversationScenario,
    Message,
    dump_message_list,
)
from api.schemas.persona import AgentPersona, UserPersona

from . import llm


def _format_example(
    example: tuple[str, ...] | str,
) -> str:
    if isinstance(example, tuple):
        return " -> ".join([f"'{msg}'" for msg in example])
    else:
        return f"'{example}'"


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


async def generate_message(
    user_sent: bool,
    user: UserPersona,
    agent: AgentPersona,
    messages: list[Message],
    scenario: BaseConversationScenario,
    instructions: MessageInstructions | None = None,
    feedback: str | None = None,
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
                    "Your culture is: "
                    if user_sent
                    else "Tailor your message to the user's culture: "
                )
                + user.culture,
            ],
        )
    )

    max_len = 30 if user_sent else 40

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
        "information.  Respond using casual, everyday language, like you’re texting a "
        "friend."
    )

    prompt_data = (
        (
            "[CONVERSATION START]"
            if len(messages) == 0
            else dump_message_list(messages[-8:], user.name, agent.name)
        )
        + f"\n{sender_name}:"
        + "\n<instructions>"
        + _format_instructions(instructions).format(user=user.name, agent=agent.name)
        + (
            (
                "I must address this feedback from an external social skills coach in "
                "writing my next message:\n"
                + "<feedback>\n"
                + "SOCIAL SKILLS COACH: "
                + feedback
                + "\n</feedback>\n"
            )
            if feedback
            else ""
        )
        + f"I am {sender_name}.\n</instructions>"
        + f"\nRESPOND AS {sender_name.upper()}. IMPORTANT: FOLLOW THE INSTRUCTIONS "
        "CAREFULLY TO ENSURE YOUR MESSAGE IS APPROPRIATE."
    )

    response = await llm.generate(
        schema=MessageWithRole,
        model=instructions.model if instructions else llm.Model.CLAUDE_3_SONNET,
        system=system_prompt,
        prompt=prompt_data,
        temperature=0.8,
    )

    return response.message
