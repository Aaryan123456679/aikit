"""ArqJobQueue — JobQueue implementation over Redis via arq.

Requires the `queue` extra (redis, arq). OCP: producers depend on the
`JobQueue` Protocol, so swapping this for a Postgres-backed queue later
touches no call sites.
"""
from __future__ import annotations

from collections.abc import Awaitable, Callable
from typing import Any

from arq import create_pool
from arq.connections import ArqRedis, RedisSettings


class ArqJobQueue:
    def __init__(self, redis_url: str) -> None:
        self._redis_url = redis_url
        self._pool: ArqRedis | None = None
        self._handlers: dict[str, Callable[[Any, dict[str, Any]], Awaitable[None]]] = {}

    async def connect(self) -> None:
        if self._pool is None:
            self._pool = await create_pool(RedisSettings.from_dsn(self._redis_url))

    async def enqueue(self, task: str, payload: dict[str, Any]) -> str:
        await self.connect()
        assert self._pool is not None
        job = await self._pool.enqueue_job(task, payload)
        if job is None:
            raise RuntimeError(f"job deduped or rejected by arq: {task}")
        return job.job_id

    def register(
        self, task: str, handler: Callable[[dict[str, Any]], Awaitable[None]]
    ) -> None:
        async def wrapper(ctx: Any, payload: dict[str, Any]) -> None:
            await handler(payload)

        wrapper.__name__ = task
        self._handlers[task] = wrapper

    @property
    def functions(self) -> list[Callable[..., Awaitable[None]]]:
        """Pass to `arq.worker.WorkerSettings.functions`."""
        return list(self._handlers.values())

    async def close(self) -> None:
        if self._pool is not None:
            await self._pool.close()
            self._pool = None
