from __future__ import annotations

import pytest
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession

from app.core.db import build_engine, build_sessionmaker


@pytest.fixture
def sqlite_url() -> str:
    return "sqlite+aiosqlite:///:memory:"


async def test_build_engine_returns_async_engine(sqlite_url: str):
    engine = build_engine(sqlite_url)
    try:
        assert isinstance(engine, AsyncEngine)
        async with engine.connect() as conn:
            result = await conn.execute(text("SELECT 1"))
            assert result.scalar() == 1
    finally:
        await engine.dispose()


async def test_sessionmaker_yields_async_session(sqlite_url: str):
    engine = build_engine(sqlite_url)
    sessionmaker = build_sessionmaker(engine)
    try:
        async with sessionmaker() as session:
            assert isinstance(session, AsyncSession)
            result = await session.execute(text("SELECT 42"))
            assert result.scalar() == 42
    finally:
        await engine.dispose()
