import asyncio
import json
import logging
import os
import re
from enum import Enum
from typing import Type, TypeVar

import numpy as np
import websockets as ws
from pydantic import BaseModel, TypeAdapter
from tenacity import retry, stop_after_attempt, wait_random_exponential

_LLM_URI = os.getenv("LLM_URI")


class ModelVendor(str, Enum):
    OPENAI = "openai"
    ANTHROPIC = "anthropic"

    def concurrency_limit(self) -> int:
        match self:
            case ModelVendor.OPENAI:
                return 4
            case ModelVendor.ANTHROPIC:
                return 32


class Model(str, Enum):
    GPT_4 = "gpt4-new"
    GPT_3_5 = "gpt3-5"
    CLAUDE_3_SONNET = "anthropic.claude-3-sonnet-20240229-v1:0"
    CLAUDE_3_HAIKU = "anthropic.claude-3-haiku-20240307-v1:0"

    def vendor(self) -> ModelVendor:
        match self:
            case Model.GPT_4 | Model.GPT_3_5:
                return ModelVendor.OPENAI
            case Model.CLAUDE_3_SONNET | Model.CLAUDE_3_HAIKU:
                return ModelVendor.ANTHROPIC


_GENERATE_SEMAPHORES = {
    vendor: asyncio.Semaphore(vendor.concurrency_limit()) for vendor in ModelVendor
}


async def _generate_unchecked(
    model: Model, prompt: str, system: str, temperature: float | None = None
):
    async with _GENERATE_SEMAPHORES[model.vendor()], ws.connect(_LLM_URI) as conn:
        action = {
            "action": "runModel",
            "model": model.value,
            "system": system,
            "prompt": prompt,
            "temperature": temperature,
        }
        await conn.send(json.dumps(action))

        response, response_dict = None, None
        while response_dict is None or "message" in response_dict:
            response = await conn.recv()

            response_dict = json.loads(response)

            if (
                "message" in response_dict
                and response_dict["message"] == "Internal server error"
            ):
                logging.error(
                    f"Could not invoke LLM generate: ISE. action: {action}. "
                    f"response: {response}"
                )
                raise RuntimeError("Could not invoke LLM generate: ISE")

        return response_dict["result"]


SchemaType = TypeVar("SchemaType", bound=BaseModel)

@retry(wait=wait_random_exponential(), stop=stop_after_attempt(3))
async def generate(
    schema: Type[SchemaType] | TypeAdapter[SchemaType],
    model: Model,
    prompt: str,
    system: str,
    temperature: float = None,
) -> Type[SchemaType]:
    response = None
    try:
        response = await _generate_unchecked(model, prompt, system, temperature)
        data = response[response.index("{") : response.rindex("}") + 1]

        # strip control characters from data
        data = re.sub(r"[\x00-\x1f\x7f]", "", data)
        return (
            schema.validate_json(data)
            if isinstance(schema, TypeAdapter)
            else schema.model_validate_json(data)
        )
    except Exception as e:
        logging.warning(f"Generate Unexpected error: {e}. {response}")

        raise RuntimeError("Could not generate valid response") from e


_EMBED_SEMAPHORE = asyncio.Semaphore(32)


@retry(wait=wait_random_exponential(), stop=stop_after_attempt(3))
async def embed(text: str) -> np.ndarray:
    async with _EMBED_SEMAPHORE, ws.connect(_LLM_URI) as conn:
        action = {"action": "extractEmbedding", "prompt": text}
        await conn.send(json.dumps(action))

        response, response_dict = None, None
        while response_dict is None or "message" in response_dict:
            response = await conn.recv()
            response_dict = json.loads(response)

            if (
                "message" in response_dict
                and response_dict["message"] == "Internal server error"
            ):
                raise RuntimeError("Could not invoke LLM embed: ISE")

        result = response_dict["result"]

        return np.array(result)


async def embed_many(texts: list[str]) -> list[np.ndarray]:
    return await asyncio.gather(*[embed(text) for text in texts])
