from __future__ import annotations

from sqlalchemy import Column, Integer, String, select

from aikit.db import Base, make_engine, make_sessionmaker, session_scope


class Widget(Base):
    __tablename__ = "widget"
    id = Column(Integer, primary_key=True)
    name = Column(String, nullable=False)


async def test_session_scope_commits_on_success():
    engine = make_engine("sqlite+aiosqlite://")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    sessionmaker = make_sessionmaker(engine)

    async with session_scope(sessionmaker) as session:
        session.add(Widget(id=1, name="a"))

    async with sessionmaker() as session:
        rows = (await session.execute(select(Widget))).scalars().all()
        assert [r.name for r in rows] == ["a"]


async def test_session_scope_rolls_back_on_error():
    engine = make_engine("sqlite+aiosqlite://")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    sessionmaker = make_sessionmaker(engine)

    class Boom(Exception):
        pass

    try:
        async with session_scope(sessionmaker) as session:
            session.add(Widget(id=1, name="a"))
            raise Boom
    except Boom:
        pass

    async with sessionmaker() as session:
        rows = (await session.execute(select(Widget))).scalars().all()
        assert rows == []
