import os
from typing import List
from uuid import UUID

import httpx
from pydantic import BaseModel, TypeAdapter
from pydantic.fields import Field
from typing_extensions import Annotated

_CONVERSATIONS_URI = os.environ.get("CONVERSATIONS_URI")


class QaMessage(BaseModel):
    qa_id: Annotated[UUID, Field(alias="user_id")]
    message: str
    response: str


qa_message_list_adapter = TypeAdapter(List[QaMessage])


async def get_messages() -> list[QaMessage]:
    async with httpx.AsyncClient() as client:
        response = await client.get(_CONVERSATIONS_URI, timeout=30)
        response.raise_for_status()

        data = response.json()

        header = data["result"][0]

        records_raw = [
            {key: value for key, value in zip(header, conversation)}
            for conversation in data["result"][1:]
        ]

        return qa_message_list_adapter.validate_python(records_raw)


async def get_messages_by_user(qa_id: UUID) -> list[QaMessage]:
    messages = await get_messages()
    return [m for m in messages if m.qa_id == qa_id]
