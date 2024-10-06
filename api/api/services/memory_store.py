import math
from dataclasses import dataclass
from heapq import nlargest

import numpy as np
from pydantic import BaseModel

from api.schemas.chat import MemoryData

from . import llm

MEMORY_HALF_LIFE = 8.0


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
    return 1.0
    # out = await llm.generate(
    #     schema=ImportanceOutput,
    #     model=llm.Model.CLAUDE_3_HAIKU,
    #     system=importance_prompt,
    #     prompt=description,
    # )

    # return out.importance_rating / 10


@dataclass
class Memory:
    description: str
    embedding: np.ndarray
    last_accessed: int
    importance: float

    @classmethod
    def from_data(cls, data: MemoryData) -> "Memory":
        return Memory(
            data.description,
            np.array(data.embedding),
            data.last_accessed,
            data.importance,
        )

    def to_data(self) -> MemoryData:
        return MemoryData(
            description=self.description,
            embedding=self.embedding.tolist(),
            last_accessed=self.last_accessed,
            importance=self.importance,
        )


class MemoryStore:
    _memories: list[Memory]

    def __init__(self, memories: list[Memory]) -> None:
        self._memories = memories

    @classmethod
    def from_data(cls, data: list[MemoryData]) -> "MemoryStore":
        return MemoryStore([Memory.from_data(memory) for memory in data])

    def to_data(self) -> list[MemoryData]:
        return [memory.to_data() for memory in self._memories]

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
            importance = memory.importance
            recency = math.exp2((memory.last_accessed - time) / MEMORY_HALF_LIFE)

            overall = similarity + importance + recency

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


form_conversation_memory_system = """
You are a conversation memory predictor, who specializes in predicting the memories that
{name} would form based on the latest message in the conversation. Separate each memory
by idea so that each memory is a coherent thought including a subject and predicate. If
there are no memories that Juan would form based on the latest message, provide an empty
list. Each memory should be unique. Do not repeat memories. Aim to provide between 0 and
1 memories, but if appropriate use more.

Output format:
{{
    "new_memories": ["<memory formed by {name}>", ...]
}}
"""

form_conversation_memory_prompt = """
Summary of relevant context from {name}'s memory:
{context}

Latest message in the conversation:
{message}

What are the new thoughts {name} is forming, based on their latest message, without
repeating things they are already aware of?
"""


class ConversationMemoryOut(BaseModel):
    new_memories: list[str]


class ConversationMemoryModule:
    def __init__(self, memory_store: MemoryStore) -> None:
        self.memory_store = memory_store

    async def generate_memory_on_message(self, message: str, name: str):
        relevant_memory = await self.memory_store.recall(message, 0, 10)

        context = "\n".join(relevant_memory)

        system = form_conversation_memory_system.format(name=name)
        prompt = form_conversation_memory_prompt.format(
            name=name, context=context, message=message
        )

        out = await llm.generate(
            schema=ConversationMemoryOut,
            model=llm.Model.CLAUDE_3_HAIKU,
            system=system,
            prompt=prompt,
        )

        return out.new_memories
