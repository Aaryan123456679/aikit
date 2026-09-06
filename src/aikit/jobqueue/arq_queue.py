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
from arq.worker import Function, func


class ArqJobQueue:
    def __init__(self, redis_url: str) -> None:
        self._redis_url = redis_url
        self._pool: ArqRedis | None = None
        self._handlers: dict[str, Function] = {}

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

        # arq's `func()` names a job by `name`, defaulting to
        # `coroutine.__qualname__` (NOT `__name__`) if omitted - a closure's
        # qualname is always its def-site path (e.g.
        # "ArqJobQueue.register.<locals>.wrapper"), so the name must be set
        # explicitly here or every registration collides under that one name.
        self._handlers[task] = func(wrapper, name=task)

    @property
    def functions(self) -> list[Function]:
        """Pass to `arq.worker.WorkerSettings.functions`."""
        return list(self._handlers.values())

    async def close(self) -> None:
        if self._pool is not None:
            await self._pool.close()
            self._pool = None
