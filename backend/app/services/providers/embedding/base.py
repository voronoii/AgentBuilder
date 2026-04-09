from __future__ import annotations
from typing import Protocol, runtime_checkable

@runtime_checkable
class EmbeddingProvider(Protocol):
    dimension: int
    async def embed_texts(self, texts: list[str]) -> list[list[float]]: ...
