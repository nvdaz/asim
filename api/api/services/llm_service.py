import asyncio
import hashlib
import json
import os
import pickle as pkl

import aiofiles
import numpy as np
import websockets as ws

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

        return response_dict["result"]


_GENERATE_CACHE_LOCK = asyncio.Lock()


async def generate(model: str, prompt: str, system: str, temperature: float = None):

    cache_file = "cache/llm_generate.pkl"
    async with _GENERATE_CACHE_LOCK:
        if os.path.exists(cache_file):
            async with aiofiles.open(cache_file, "rb") as f:
                content = await f.read()
                cache = pkl.loads(content)
        else:
            cache = {}

    key = hashlib.sha256(
        json.dumps((model, prompt, system, temperature)).encode()
    ).hexdigest()

    if key in cache:
        return cache[key]

    result = await _generate(model, prompt, system, temperature)

    async with _GENERATE_CACHE_LOCK:
        if os.path.exists(cache_file):
            async with aiofiles.open(cache_file, "rb") as f:
                content = await f.read()
                cache = pkl.loads(content)
        else:
            cache = {}
        cache[key] = result
        async with aiofiles.open(cache_file, "wb") as f:
            await f.write(pkl.dumps(cache, protocol=pkl.HIGHEST_PROTOCOL))

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
