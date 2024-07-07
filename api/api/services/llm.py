import asyncio
import hashlib
import json
import logging
import os
import pickle as pkl
from typing import Type, TypeVar

import aiofiles
import numpy as np
import websockets as ws
from pydantic import BaseModel, ValidationError

_LLM_URI = os.getenv("LLM_URI")

_GENERATE_SEMAPHORE = asyncio.Semaphore(4)


MODEL_GPT_4 = "gpt4-new"
MODEL_GPT_3_5 = "gpt3-5"
MODEL_CLAUDE_HAIKU = "anthropic.claude-3-haiku-20240307-v1:0"
MODEL_CLAUDE_SONNET = "anthropic.claude-3-sonnet-20240229-v1:0"


async def _generate(
    model: str, prompt: str, system: str, temperature: float | None = None
):
    async with _GENERATE_SEMAPHORE, ws.connect(_LLM_URI) as conn:
        action = {
            "action": "runModel",
            "model": model,
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


async def _generate_strict(
    schema: Type[SchemaType],
    model: str,
    prompt: str,
    system: str,
    temperature: float = None,
    max_tries: int = 3,
) -> Type[SchemaType]:
    for attempt in range(max_tries):
        response = None
        try:
            response = await _generate(model, prompt, system, temperature)
            data = response[response.index("{") : response.rindex("}") + 1]
            return schema(**json.loads(data))
        except Exception as e:
            logging.warning(
                f"Attempt {attempt + 1}/{max_tries} - Unexpected error: {e}. {response}"
            )

    raise RuntimeError("Could not generate valid response")


_GENERATE_CACHE_LOCK = asyncio.Lock()


async def generate(
    schema: Type[SchemaType],
    model: str,
    prompt: str,
    system: str,
    temperature: float = None,
    max_tries: int = 3,
):
    cache_file = "cache/llm_generate.json"
    async with _GENERATE_CACHE_LOCK:
        if os.path.exists(cache_file):
            async with aiofiles.open(cache_file, "r") as f:
                content = await f.read()
                cache = json.loads(content)
        else:
            cache = {}

    key = hashlib.sha256(
        json.dumps(
            (schema.model_json_schema(), model, prompt, system, temperature),
            sort_keys=True,
        ).encode()
    ).hexdigest()

    if key in cache:
        try:
            return schema(**cache[key])
        except ValidationError as e:
            logging.warning(f"Cache invalid: {e.errors()}")

    result = await _generate_strict(
        schema, model, prompt, system, temperature, max_tries
    )

    async with _GENERATE_CACHE_LOCK:
        if os.path.exists(cache_file):
            async with aiofiles.open(cache_file, "r") as f:
                content = await f.read()
                cache = json.loads(content)
        else:
            cache = {}
        cache[key] = result.model_dump()
        async with aiofiles.open(cache_file, "w") as f:
            await f.write(json.dumps(cache, indent=2))

    return result


_EMBED_SEMAPHORE = asyncio.Semaphore(16)


async def _embed(text: str) -> np.ndarray:
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


_EMBED_CACHE_LOCK = asyncio.Lock()


async def embed(texts: list[str]) -> list[np.array]:
    cache_file = "cache/llm_embed.pkl"

    async with _EMBED_CACHE_LOCK:
        if os.path.exists(cache_file):
            async with aiofiles.open(cache_file, "rb") as f:
                content = await f.read()
                cache = pkl.loads(content)
        else:
            cache = {}

        uncached_texts = []
        uncached_indices = []
        for i, text in enumerate(texts):
            key = hashlib.sha256(text.encode()).hexdigest()
            if key in cache:
                continue
            uncached_texts.append(text)
            uncached_indices.append(i)

        if uncached_texts:
            embeddings = await asyncio.gather(
                *[_embed(text) for text in uncached_texts]
            )

            for i, idx in enumerate(uncached_indices):
                cache[hashlib.sha256(texts[idx].encode()).hexdigest()] = embeddings[i]

            async with aiofiles.open(cache_file, "wb") as f:
                await f.write(pkl.dumps(cache, protocol=pkl.HIGHEST_PROTOCOL))

        embeddings = []
        for text in texts:
            key = hashlib.sha256(text.encode()).hexdigest()
            embeddings.append(cache[key])

        return embeddings
