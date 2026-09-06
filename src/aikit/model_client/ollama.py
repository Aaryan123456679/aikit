"""OllamaClient — ModelClient implementation over a local Ollama server.

Requires the `http` extra (httpx). This is the only concrete ModelClient
in v1: it doubles as target and judge model per the eval-platform HLD ($0
cost, no hosted API keys needed).
"""
from __future__ import annotations

import json
import time
from collections.abc import AsyncIterator

import httpx

from . import ChatMessage, Completion


class OllamaClient:
    """LSP: substitutable anywhere a `ModelClient` is expected."""

    def __init__(
        self,
        host: str = "http://localhost:11434",
        *,
        default_model: str = "llama3.1",
        timeout: float = 60.0,
        name: str = "ollama",
    ) -> None:
        self.name = name
        self._default_model = default_model
        self._client = httpx.AsyncClient(base_url=host.rstrip("/"), timeout=timeout)

    async def complete(
        self, messages: list[ChatMessage], *, model: str | None = None
    ) -> Completion:
        target_model = model or self._default_model
        payload = {
            "model": target_model,
            "messages": [{"role": m.role, "content": m.content} for m in messages],
            "stream": False,
        }
        start = time.perf_counter()
        resp = await self._client.post("/api/chat", json=payload)
        resp.raise_for_status()
        data = resp.json()
        latency_ms = (time.perf_counter() - start) * 1000
        return Completion(
            content=data.get("message", {}).get("content", ""),
            model=target_model,
            tokens_in=data.get("prompt_eval_count", 0),
            tokens_out=data.get("eval_count", 0),
            latency_ms=latency_ms,
        )

    async def stream(
        self, messages: list[ChatMessage], *, model: str | None = None
    ) -> AsyncIterator[str]:
        payload = {
            "model": model or self._default_model,
            "messages": [{"role": m.role, "content": m.content} for m in messages],
            "stream": True,
        }
        async with self._client.stream("POST", "/api/chat", json=payload) as resp:
            resp.raise_for_status()
            async for line in resp.aiter_lines():
                if not line:
                    continue
                chunk = json.loads(line)
                piece = chunk.get("message", {}).get("content")
                if piece:
                    yield piece

    async def health(self) -> bool:
        try:
            resp = await self._client.get("/api/tags")
            return resp.status_code == 200
        except httpx.HTTPError:
            return False

    async def aclose(self) -> None:
        await self._client.aclose()
