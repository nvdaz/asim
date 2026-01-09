import asyncio
import json
import logging
import os
import re
from concurrent.futures import ThreadPoolExecutor
from enum import Enum
from typing import TypeVar, overload

import numpy as np
import requests
import websockets as ws
from pydantic import BaseModel, TypeAdapter
from tenacity import retry, stop_after_attempt, wait_random_exponential

_LLM_URI: str = os.getenv("LLM_URI", "")
_LLM_KEY: str = os.getenv("LLM_KEY", "")

assert _LLM_URI != "", "LLM_URI environment variable must be set"
assert _LLM_KEY != "", "LLM_KEY environment variable must be set"


class Model(str, Enum):
    GPT_4 = "gpt4-new"
    GPT_4o = "gpt-4o"
    GPT_4o_mini = "4o-mini"
    GPT_3_5 = "gpt3-5"

    CLAUDE_3_SONNET = "us.anthropic.claude-3-sonnet-20240229-v1:0"
    CLAUDE_3_HAIKU = "us.anthropic.claude-3-haiku-20240307-v1:0"
    CLAUDE_3p5_SONNET = "us.anthropic.claude-3-5-sonnet-20240620-v1:0"


async def _generate_unchecked(
    model: Model, prompt: str, system: str, temperature: float | None = None
) -> str:
    body = {
        "model": model.value,
        "system": system,
        "query": prompt,
        "lastk": 0,
        "temperature": temperature,
        "cache_match_thresh": 1.1,
    }
    body = {k: v for k, v in body.items() if v is not None}

    headers = {"request_type": "call", "x-api-key": _LLM_KEY}

    def make_request():
        response = requests.post(_LLM_URI, headers=headers, json=body)
        response.raise_for_status()
        return response.json()

    loop = asyncio.get_running_loop()
    with ThreadPoolExecutor() as pool:
        try:
            res = await loop.run_in_executor(pool, make_request)
        except requests.exceptions.HTTPError as e:
            print(f"Request failed: {e}")
            raise e

    print("-----------------")
    print(system)
    print(prompt)
    print("---")
    print(res)
    print("-----------------")

    return res["result"]


SchemaType = TypeVar("SchemaType", bound=BaseModel)


@overload
async def generate(
    schema: None,
    model: Model,
    prompt: str,
    system: str,
    temperature: float | None = None,
) -> str: ...


@overload
async def generate(
    schema: type[SchemaType] | TypeAdapter[SchemaType],
    model: Model,
    prompt: str,
    system: str,
    temperature: float | None = None,
) -> SchemaType: ...


@retry(wait=wait_random_exponential(), stop=stop_after_attempt(3))
async def generate(
    schema: type[SchemaType] | TypeAdapter[SchemaType] | None,
    model: Model,
    prompt: str,
    system: str,
    temperature: float | None = None,
) -> SchemaType | str:
    response = None
    try:
        response = await _generate_unchecked(model, prompt, system, temperature)
        data = (
            response[response.index("{") : response.rindex("}") + 1]
            if schema
            else response
        )

        # strip control characters from data
        data = re.sub(r"[\x00-\x1f\x7f]", "", data)

        if schema is None:
            return data
        if isinstance(schema, TypeAdapter):
            return schema.validate_json(data)
        else:
            return schema.model_validate_json(data)

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
