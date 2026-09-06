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


def make_engine(database_url: str, *, echo: bool = False) -> AsyncEngine:
    return create_async_engine(database_url, echo=echo, pool_pre_ping=True)


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
