from typing import Annotated

from pydantic import AfterValidator

from api.schemas.conversation import Message, message_list_adapter
from api.schemas.persona import Persona

from . import llm


async def generate_message(
    sender: Persona,
    recipient: Persona,
    messages: list[Message],
    scenario: str | None = None,
    instructions: str | None = None,
) -> str:
    def validate_sender(v):
        if v != sender.name:
            raise ValueError(f"Sender must be {sender.name}")
        return v

    class MessageWithSender(Message):
        sender: Annotated[str, AfterValidator(validate_sender)]

    prelude = "\n".join(
        filter(
            None,
            [
                sender.description,
                f"Scenario: {scenario}" if scenario else None,
                (
                    f"INSTRUCTIONS FOR YOUR MESSAGE: {instructions}"
                    if instructions
                    else None
                ),
            ],
        )
    )

    system_prompt = (
        f"{prelude}\nYou ({sender.name}) are chatting over text with {recipient.name}. "
        "Keep your messages under 60 words and appropriate for a text conversation. "
        "ALWAYS provide detailed information and DO NOT end the conversation. "
        "DO NOT try to start any external conversations or schedule any meetings. "
        "Respond with a JSON object containing the key 'message' with your message as "
        f"the value and the key 'sender' with '{sender.name}' as the value. Respond "
        "ONLY with your next message. Do not include previous messages in your "
        "response. STAY ON TOPIC and DO NOT mention your communication styles. DO NOT "
        "reference external information."
    )

    prompt_data = (
        "[CONVERSATION START]"
        if len(messages) == 0
        else message_list_adapter.dump_json(messages[-8:]).decode()
    )

    response = await llm.generate(
        schema=MessageWithSender,
        model=llm.Model.CLAUDE_3_SONNET,
        system=system_prompt,
        prompt=prompt_data,
    )

    return response.message
