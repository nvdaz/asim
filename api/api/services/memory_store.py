import math
from dataclasses import dataclass
from heapq import nlargest
from typing import Callable

import numpy as np
from pydantic import BaseModel

from . import llm

MEMORY_HALF_LIFE = 8.0

Recall = Callable[[str], list[str]]


importance_prompt = """
On a scale of 1 to 10, where 1 is purely mundane (e.g. eating breakfast, making bed) and
10 is life-changing (e.g. getting married, moving house), rate the likely importance of
the following memory.

Output format:
{
    "importance_rating": <int from 1 to 10>
}
"""


class ImportanceOutput(BaseModel):
    importance_rating: int


async def calculate_importance(description: str) -> float:
    out = await llm.generate(
        schema=ImportanceOutput,
        model=llm.Model.GPT_4,
        system=importance_prompt,
        prompt=description,
    )

    return out.importance_rating / 10


@dataclass
class Memory:
    description: str
    embedding: np.ndarray
    last_accessed: int
    importance: float


class MemoryInStore(BaseModel):
    description: str
    embedding: list[float]
    last_accessed: int
    importance: float

    @classmethod
    def from_memory(cls, memory: Memory) -> "MemoryInStore":
        return cls(
            description=memory.description,
            embedding=memory.embedding.tolist(),
            last_accessed=memory.last_accessed,
            importance=memory.importance,
        )

    def to_memory(self) -> Memory:
        return Memory(
            self.description,
            np.array(self.embedding),
            self.last_accessed,
            self.importance,
        )


class MemoryStore:
    _memories: list[Memory]

    def __init__(self, memories: list[Memory]) -> None:
        self._memories = memories

    async def remember(self, description: str, time: int) -> None:
        embedding = await llm.embed(description)
        importance = await calculate_importance(description)

        self._memories.append(
            Memory(
                description,
                embedding,
                time,
                importance,
            )
        )

    async def recall(self, query: str, time: int, n: int) -> list[str]:
        query_embedding = await llm.embed(query)

        ranked_memories = []

        for memory in self._memories:
            similarity = np.dot(query_embedding, memory.embedding)
            salience = memory.importance
            recency = math.exp2((memory.last_accessed - time) / MEMORY_HALF_LIFE)

            overall = similarity + salience + recency

            ranked_memories.append((overall, memory.description))

        return [memory for _, memory in nlargest(n, ranked_memories)]


form_opinion_system = """
You are an opinion predictor, who specializes in predicting the opinion of {name} given
a piece of content. Please provide the opinion of {name} only, not your own opinion.

Output format:
{
    "opinion": "<{name}'s opinion>"
}
"""

form_opinion_prompt = """
Summary of relevant context from {name}'s memory:
{context}

Content that {name} is forming an opinion on:
{content}

Remember that you are predicting {name}'s opinion, which may or may not be the same as
your own opinion. Please provide the opinion of {name} only.
"""


class OpinionOut(BaseModel):
    opinion: str


class OpinionModule:
    def __init__(self, memory_store: MemoryStore) -> None:
        self.memory_store = memory_store

    async def generate_opinion_on_content(self, content: str):
        relevant_memory = await self.memory_store.recall(content, 0, 10)

        context = "\n".join(relevant_memory)

        system = form_opinion_system.format(name="John")
        prompt = form_opinion_prompt.format(
            name="John", context=context, content=content
        )

        out = await llm.generate(
            schema=OpinionOut,
            model=llm.Model.GPT_4,
            system=system,
            prompt=prompt,
        )

        return out.opinion
