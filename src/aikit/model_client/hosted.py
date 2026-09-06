"""HostedClient — ModelClient implementation over any OpenAI-compatible
chat-completions API (OpenAI itself, and the many providers that mirror
its wire format: Groq, Together, Fireworks, OpenRouter, ...).

Requires the `http` extra (httpx).
"""
from __future__ import annotations

import json
import time
from collections.abc import AsyncIterator

import httpx

from . import ChatMessage, Completion, StreamEvent, Usage


class HostedClient:
    """LSP: substitutable anywhere a `ModelClient` is expected."""

    def __init__(
        self,
        base_url: str,
        api_key: str,
        *,
        default_model: str,
        timeout: float = 60.0,
        name: str = "hosted",
    ) -> None:
        self.name = name
        self._default_model = default_model
        self._client = httpx.AsyncClient(
            base_url=base_url.rstrip("/"),
            timeout=timeout,
            headers={"Authorization": f"Bearer {api_key}"},
        )

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
        resp = await self._client.post("/chat/completions", json=payload)
        resp.raise_for_status()
        data = resp.json()
        latency_ms = (time.perf_counter() - start) * 1000
        choice = data["choices"][0]
        usage = data.get("usage") or {}
        return Completion(
            content=choice.get("message", {}).get("content", ""),
            model=data.get("model", target_model),
            tokens_in=usage.get("prompt_tokens", 0),
            tokens_out=usage.get("completion_tokens", 0),
            latency_ms=latency_ms,
        )

    async def stream(
        self, messages: list[ChatMessage], *, model: str | None = None
    ) -> AsyncIterator[StreamEvent]:
        payload = {
            "model": model or self._default_model,
            "messages": [{"role": m.role, "content": m.content} for m in messages],
            "stream": True,
            # Ask for a final usage-only chunk (OpenAI and most compatible
            # providers support this) so the terminal Usage is exact, not
            # estimated client-side.
            "stream_options": {"include_usage": True},
        }
        finish_reason = "stop"
        async with self._client.stream("POST", "/chat/completions", json=payload) as resp:
            resp.raise_for_status()
            async for line in resp.aiter_lines():
                if not line or not line.startswith("data:"):
                    continue
                data = line[len("data:") :].strip()
                if data == "[DONE]":
                    break
                chunk = json.loads(data)
                choices = chunk.get("choices") or []
                if choices:
                    delta = choices[0].get("delta", {})
                    piece = delta.get("content")
                    if piece:
                        yield piece
                    if choices[0].get("finish_reason"):
                        finish_reason = choices[0]["finish_reason"]
                usage = chunk.get("usage")
                if usage:
                    yield Usage(
                        tokens_in=usage.get("prompt_tokens", 0),
                        tokens_out=usage.get("completion_tokens", 0),
                        finish_reason=finish_reason,
                    )

    async def health(self) -> bool:
        try:
            resp = await self._client.get("/models")
            return resp.status_code == 200
        except httpx.HTTPError:
            return False

    async def aclose(self) -> None:
        await self._client.aclose()
