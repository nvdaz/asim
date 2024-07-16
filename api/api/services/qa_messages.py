import asyncio
import os
from typing import Annotated
from uuid import UUID

import aiofiles
import httpx
from pydantic import BaseModel, ConfigDict, TypeAdapter
from pydantic.fields import Field

_CONVERSATIONS_URI = os.environ.get("CONVERSATIONS_URI")


class QaMessage(BaseModel):
    qa_id: Annotated[UUID, Field(alias="user_id")]
    message: str
    response: str

    model_config = ConfigDict(populate_by_name=True)


qa_message_list_adapter: TypeAdapter[list[QaMessage]] = TypeAdapter(list[QaMessage])


async def _get_messages_from_server() -> list[QaMessage]:
    async with httpx.AsyncClient() as client:
        response = await client.get(_CONVERSATIONS_URI, timeout=60)
        response.raise_for_status()

        data = response.json()

        header = data["result"][0]

        records_raw = [
            {key: value for key, value in zip(header, conversation)}
            for conversation in data["result"][1:]
        ]

        return qa_message_list_adapter.validate_python(records_raw)


_MESSAGES_FILE_LOCK = asyncio.Lock()


async def get_messages() -> list[QaMessage]:
    cache_file = "cache/qa_messages.json"
    if os.path.exists(cache_file):
        async with _MESSAGES_FILE_LOCK, aiofiles.open(cache_file, "r") as f:
            content = await f.read()
            return qa_message_list_adapter.validate_json(content)
    else:
        messages = await _get_messages_from_server()
        async with _MESSAGES_FILE_LOCK, aiofiles.open(cache_file, "w") as f:
            await f.write(qa_message_list_adapter.dump_json(messages).decode())
        return messages


async def get_messages_by_user(qa_id: UUID) -> list[QaMessage]:
    messages = await get_messages()
    return [m for m in messages if m.qa_id == qa_id]
