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
                f"Instructions: {instructions}" if instructions else None,
            ],
        )
    )

    system_prompt = (
        f"{prelude}\nYou ({sender.name}) are chatting over text with {recipient.name}. "
        "Keep your messages under 50 words and appropriate for a text conversation. "
        "Keep the conversation going. Return a JSON object with the key 'message' and "
        f"your message as the value and the key 'sender' with '{sender.name}' as the "
        "value. Respond ONLY with your next message. Do not include the previous "
        "messages in your response."
    )

    prompt_data = (
        "[CONVERSATION START]"
        if len(messages) == 0
        else message_list_adapter.dump_json(messages).decode()
    )

    response = await llm.generate(
        schema=MessageWithSender,
        model=llm.Model.GPT_4,
        system=system_prompt,
        prompt=prompt_data,
    )

    return response.message
