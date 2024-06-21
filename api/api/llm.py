import asyncio
import hashlib
import json
import os
import pickle as pkl

import websockets as ws
from torch import Tensor
from torch.nn.functional import normalize
from transformers import AutoModel

__LLM_URI = os.environ.get("LLM_URI")


MODEL_GPT_4 = "gpt4-new"
MODEL_GPT_3_5 = "gpt3-5"
MODEL_CLAUDE_HAIKU = "anthropic.claude-3-haiku-20240307-v1:0"
MODEL_CLAUDE_SONNET = "anthropic.claude-3-sonnet-20240229-v1:0"


async def __generate(
    model: str, prompt: str, system: str, temperature: float | None = None
) -> str:
    async with asyncio.timeout(300), ws.connect(__LLM_URI) as websocket:
        action = json.dumps(
            {
                "action": "runModel",
                "model": model,
                "system": system,
                "prompt": prompt,
                "temperature": temperature,
            }
        )
        await websocket.send(action)

        response, response_dict = None, None
        while response_dict is None or "message" in response_dict:
            response = await websocket.recv()
            response_dict = json.loads(response)

        return response_dict["result"]


async def generate(
    model: str, prompt: str, system: str, temperature: float | None = None
) -> str:
    cache_file = "cache/llm_generate.pkl"
    if os.path.exists(cache_file):
        with open(cache_file, "rb") as f:
            cache = pkl.load(f)
    else:
        cache = {}

    key = hashlib.sha256(
        json.dumps((model, prompt, system, temperature), sort_keys=True).encode()
    ).hexdigest()

    if key in cache:
        return cache[key]

    result = await __generate(model, prompt, system, temperature)

    cache[key] = result

    with open(cache_file, "wb") as f:
        pkl.dump(cache, f, protocol=pkl.HIGHEST_PROTOCOL)

    return result


__HF_TOKEN = os.environ.get("HF_TOKEN")

__embed_model = None


def __get_model():
    global __embed_model

    if __embed_model is None:
        __embed_model = AutoModel.from_pretrained(
            "nvidia/NV-Embed-v1", token=__HF_TOKEN, trust_remote_code=True
        )

    return __embed_model


async def __embed(text: list[str]) -> list[Tensor]:
    model = __get_model()
    max_length = 4096

    embeddings = model.encode(text, instruction="", max_length=max_length)

    return normalize(embeddings)


async def embed(texts: list[str]) -> list[Tensor]:
    cache_file = "cache/llm_embed.pkl"
    if os.path.exists(cache_file):
        with open(cache_file, "rb") as f:
            cache = pkl.load(f)
    else:
        cache = {}

    uncached_texts = []
    uncached_indices = []
    for i, text in enumerate(texts):
        key = hashlib.sha256(json.dumps(text, sort_keys=True).encode()).hexdigest()
        if key in cache:
            continue
        uncached_texts.append(text)
        uncached_indices.append(i)

    if uncached_texts:
        print("Embedding ", len(uncached_texts))
        BATCH_SIZE = 10
        for i in range(0, len(uncached_texts), BATCH_SIZE):
            uncached_embeddings = await __embed(uncached_texts[i : i + BATCH_SIZE])
            for j, embedding in enumerate(uncached_embeddings):
                key = hashlib.sha256(
                    json.dumps(uncached_texts[i + j], sort_keys=True).encode()
                ).hexdigest()
                cache[key] = embedding
            with open(cache_file, "wb") as f:
                pkl.dump(cache, f, protocol=pkl.HIGHEST_PROTOCOL)
            print("Embedded ", i, "of", len(uncached_texts))

    embeddings = []
    for text in texts:
        key = hashlib.sha256(json.dumps(text, sort_keys=True).encode()).hexdigest()
        embeddings.append(cache[key])

    return embeddings
