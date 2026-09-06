"""SentenceTransformerEmbeddingService — local, batched embeddings.

Requires the `embeddings` extra (sentence-transformers). Runs the (blocking,
CPU-bound) model in a thread executor so it never blocks the event loop.
"""
from __future__ import annotations

import asyncio

import numpy as np
from sentence_transformers import SentenceTransformer

from . import Vector


class SentenceTransformerEmbeddingService:
    """LSP: substitutable anywhere an `EmbeddingService` is expected."""

    def __init__(self, model_name: str = "all-MiniLM-L6-v2") -> None:
        self._model = SentenceTransformer(model_name)
        self.dim = self._model.get_sentence_embedding_dimension()

    async def embed(self, texts: list[str]) -> list[Vector]:
        loop = asyncio.get_running_loop()
        vectors = await loop.run_in_executor(None, self._model.encode, texts)
        return [vector.tolist() for vector in vectors]

    @staticmethod
    def cosine(a: Vector, b: Vector) -> float:
        va, vb = np.asarray(a, dtype=float), np.asarray(b, dtype=float)
        denom = float(np.linalg.norm(va) * np.linalg.norm(vb))
        if denom == 0.0:
            return 0.0
        return float(np.dot(va, vb) / denom)
