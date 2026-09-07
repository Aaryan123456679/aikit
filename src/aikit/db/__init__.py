"""DB — async SQLAlchemy engine/session base + pgvector helpers.

Impl requires the `db` extra. Provides:
- async engine factory
- transaction-scoped session context manager
- DeclarativeBase subclass every service builds models on
"""
from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

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
    pool_size: int = 5,
    max_overflow: int = 10,
) -> AsyncEngine:
    # pool_size/max_overflow default to SQLAlchemy's own defaults (5, 10 -
    # 15 concurrent connections total), so existing callers see no change.
    # Found via load-testing the gateway at real concurrency: every request
    # that logs to Postgres holds a connection for that write, so a
    # service's real concurrency ceiling is min(this pool, everything
    # else) - callers expecting more than ~15 concurrent in-flight DB
    # operations need to size this explicitly rather than discover the
    # default under load.
    return create_async_engine(
        database_url,
        echo=echo,
        pool_pre_ping=True,
        pool_size=pool_size,
        max_overflow=max_overflow,
    )


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
