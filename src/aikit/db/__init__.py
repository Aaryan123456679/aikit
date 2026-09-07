"""DB — async SQLAlchemy engine/session base + pgvector helpers.

Impl requires the `db` extra. Provides:
- async engine factory
- transaction-scoped session context manager
- DeclarativeBase subclass every service builds models on
"""
from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from typing import Any

from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import DeclarativeBase

__all__ = ["Base", "make_engine", "make_sessionmaker", "session_scope"]


class Base(DeclarativeBase):
    """Declarative base every downstream service builds its ORM models on."""


def make_engine(
    database_url: str,
    *,
    echo: bool = False,
    pool_size: int | None = None,
    max_overflow: int | None = None,
) -> AsyncEngine:
    # pool_size/max_overflow default to None (omitted entirely) rather
    # than SQLAlchemy's own QueuePool defaults (5/10), because those two
    # kwargs are QueuePool-specific and blow up with a TypeError against
    # any other pool class - including SQLite's StaticPool, which this
    # project's own test suite uses. Omitting them when unset preserves
    # exact prior behavior for every caller that doesn't pass them.
    # Callers on Postgres that want a bigger pool (found necessary load-
    # testing the gateway: every request that logs to Postgres holds a
    # connection for that write, so 50 concurrent requests need more than
    # QueuePool's own default 15-connection ceiling) pass them explicitly.
    kwargs: dict[str, Any] = {"echo": echo, "pool_pre_ping": True}
    if pool_size is not None:
        kwargs["pool_size"] = pool_size
    if max_overflow is not None:
        kwargs["max_overflow"] = max_overflow
    return create_async_engine(database_url, **kwargs)


def make_sessionmaker(engine: AsyncEngine) -> async_sessionmaker[AsyncSession]:
    return async_sessionmaker(engine, expire_on_commit=False)


@asynccontextmanager
async def session_scope(
    sessionmaker: async_sessionmaker[AsyncSession],
) -> AsyncIterator[AsyncSession]:
    """Open a session bound to a single transaction: commits on success,
    rolls back on any exception."""
    async with sessionmaker() as session, session.begin():
        yield session
