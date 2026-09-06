"""JobQueue — async task fan-out abstraction.

OCP: swap Redis/arq for a Postgres-backed queue without touching producers.
"""
from __future__ import annotations

from collections.abc import Awaitable, Callable
from typing import Any, Protocol


class JobQueue(Protocol):
    async def enqueue(self, task: str, payload: dict[str, Any]) -> str: ...
    def register(
        self, task: str, handler: Callable[[dict[str, Any]], Awaitable[None]]
    ) -> None: ...
