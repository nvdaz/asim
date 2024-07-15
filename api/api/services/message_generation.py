from typing import Annotated

from pydantic import AfterValidator, BaseModel

from api.schemas.conversation import Message, message_list_adapter
from api.schemas.persona import Persona

from . import llm


async def generate_message(
    sender: Persona, other: Persona, messages: list[Message], extra=""
) -> str:
    def validate_sender(v):
        if v != sender.name:
            raise ValueError(f"Sender must be {sender.name}")
        return v

    class MessageResponse(BaseModel):
        message: str
        sender: Annotated[str, AfterValidator(validate_sender)]

    instr = f"Instructions: {extra}" if extra else ""

    system_prompt = (
        f"{sender.description}\n{instr}\nYou ({sender.name}) are chatting over text "
        f"with {other.name}. Keep your messages under 50 words and appropriate for a "
        "text conversation. Keep the conversation going. Return a JSON object with the "
        "key 'message' and your message as the value and the key 'sender' with "
        f"'{sender.name}' as the value. Respond ONLY with your next message. Do not "
        "include the previous messages in your response."
    )

    prompt_data = (
        "[CONVERSATION START]"
        if len(messages) == 0
        else str(message_list_adapter.dump_json(messages))
    )

    response = await llm.generate(
        schema=MessageResponse,
        model=llm.MODEL_GPT_4,
        system=system_prompt,
        prompt=prompt_data,
    )

    return response.message
