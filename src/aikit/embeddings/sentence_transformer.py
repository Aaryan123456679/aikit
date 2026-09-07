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
        # device="cpu" is deliberate, not a missing feature: auto-detection
        # picks MPS/CUDA when available, but a server process calls encode()
        # from multiple concurrent executor threads (one per in-flight
        # request), and MPS does not tolerate concurrent access from
        # multiple threads reliably - it can crash the whole process rather
        # than raise a catchable exception. CPU is also the right choice
        # for this workload's shape (many small, single-item, latency-
        # sensitive calls), where GPU dispatch overhead would dominate
        # anyway.
        self._model = SentenceTransformer(model_name, device="cpu")
        dim = self._model.get_sentence_embedding_dimension()
        if dim is None:
            raise ValueError(f"model {model_name!r} did not report an embedding dimension")
        self.dim: int = dim

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
