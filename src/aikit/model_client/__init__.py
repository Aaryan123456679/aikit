"""ModelClient — unified async interface over heterogeneous LLM backends.

DIP: consumers depend on this Protocol, never on Ollama/hosted specifics.
LSP: every implementation is substitutable.
ISP: streaming and non-streaming are separate methods.
"""
from __future__ import annotations

from collections.abc import AsyncIterator
from dataclasses import dataclass
from typing import Literal, Protocol, runtime_checkable

Role = Literal["system", "user", "assistant"]


@dataclass(frozen=True)
class ChatMessage:
    role: Role
    content: str


@dataclass(frozen=True)
class Completion:
    content: str
    model: str
    tokens_in: int
    tokens_out: int
    latency_ms: float


@dataclass(frozen=True)
class Usage:
    """Terminal event on a `stream()` iterator: exactly one, always last."""

    tokens_in: int
    tokens_out: int
    finish_reason: str


StreamEvent = str | Usage


@runtime_checkable
class ModelClient(Protocol):
    """A single LLM backend. Implementations: OllamaClient, HostedClient."""

    name: str

    async def complete(
        self, messages: list[ChatMessage], *, model: str | None = None
    ) -> Completion: ...

    def stream(
        self, messages: list[ChatMessage], *, model: str | None = None
    ) -> AsyncIterator[StreamEvent]:
        """An async-generator method: called directly (no `await`), then
        iterated with `async for`. Yields text deltas (`str`) followed by
        exactly one terminal `Usage` — callers can accumulate text and read
        cost/finish_reason off the last event without a second round trip."""
        ...

    async def health(self) -> bool: ...

    async def aclose(self) -> None: ...
