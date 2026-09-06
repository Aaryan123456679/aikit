"""EmbeddingService — local, batched text embeddings.

Reused by: eval (similarity scorer), gateway (semantic cache), memory (retrieval).
Concrete impl requires the `embeddings` extra (sentence-transformers).
"""
from __future__ import annotations

from typing import Protocol, runtime_checkable

Vector = list[float]


@runtime_checkable
class EmbeddingService(Protocol):
    dim: int

    async def embed(self, texts: list[str]) -> list[Vector]: ...

    @staticmethod
    def cosine(a: Vector, b: Vector) -> float: ...
