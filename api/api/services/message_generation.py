from typing import Annotated

from pydantic import AfterValidator, BaseModel

from api.schemas.conversation import ConversationScenario, Message, message_list_adapter
from api.schemas.persona import Persona

from . import llm


async def generate_message(
    user_sent: bool,
    user: Persona,
    agent: Persona,
    messages: list[Message],
    scenario: ConversationScenario,
    instructions: str | None = None,
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
                scenario_perspective if scenario_perspective else None,
                (
                    f"INSTRUCTIONS FOR YOUR MESSAGE: {instructions}"
                    if instructions
                    else None
                ),
            ],
        )
    )

    max_len = 60 if user_sent else 120

    system_prompt = (
        f"{prelude}\nYou ({sender_name}) are chatting over text with {recipient_name}. "
        f"Keep your messages under {max_len} words and appropriate for a text "
        "conversation. ALWAYS provide detailed information and DO NOT end the "
        "conversation. DO NOT try to start any external conversations or schedule any "
        f"meetings. You are {sender_name}, and are writing to {recipient_name}. "
        "YOU ARE NOT AN AI. Respond with a JSON object containing the key 'message' "
        f"with your message as the value and the key 'sender' with '{sender_name}' as "
        "the value. Respond ONLY with your next message. Do not include previous "
        "messages in your response. STAY ON TOPIC and DO NOT mention your "
        "communication styles. DO NOT reference external information."
    )

    prompt_data = (
        "[CONVERSATION START]"
        if len(messages) == 0
        else message_list_adapter.dump_json(messages[-8:]).decode()
    )

    response = await llm.generate(
        schema=MessageWithRole,
        model=llm.Model.CLAUDE_3_SONNET,
        system=system_prompt,
        prompt=prompt_data,
    )

    return response.message
