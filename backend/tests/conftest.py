from __future__ import annotations

import os
from collections.abc import AsyncIterator, Iterator

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.models.base import Base


@pytest.fixture(autouse=True)
def isolate_env(monkeypatch: pytest.MonkeyPatch, tmp_path) -> Iterator[None]:
    """Strip AGENTBUILDER_* env vars before each test for deterministic Settings.
    Use file-based sqlite so the startup hook and request handler share the same DB.
    """
    for key in list(os.environ):
        if key.startswith("AGENTBUILDER_"):
            monkeypatch.delenv(key, raising=False)
    db_path = tmp_path / "test.db"
    monkeypatch.setenv(
        "AGENTBUILDER_DATABASE_URL",
        f"sqlite+aiosqlite:///{db_path}",
    )
    yield


@pytest.fixture(autouse=True)
def _reset_singletons() -> Iterator[None]:
    """Reset global singletons between tests."""
    from app.core import db as db_module

    db_module._engine = None
    db_module._sessionmaker = None
    yield
    db_module._engine = None
    db_module._sessionmaker = None
    try:
        from app.services.knowledge.bootstrap import reset_orchestrator

        reset_orchestrator()
    except ImportError:
        pass


@pytest_asyncio.fixture
async def db_session() -> AsyncIterator[AsyncSession]:
    """In-memory SQLite session with all tables created (for unit tests)."""
    engine = create_async_engine("sqlite+aiosqlite:///:memory:", future=True)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    sm = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)
    async with sm() as session:
        yield session
    await engine.dispose()
