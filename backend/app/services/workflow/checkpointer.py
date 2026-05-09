"""Process-singleton AsyncPostgresSaver for LangGraph multi-turn state.

LangGraph manages its own tables (``checkpoints``, ``checkpoint_blobs``,
``checkpoint_writes``, ``checkpoint_migrations``). On first use we call
``setup()`` once to create them; alembic does not own these.

Implementation note: ``langgraph-checkpoint-postgres`` is built on psycopg3,
not asyncpg, so we translate the SQLAlchemy URL (``postgresql+asyncpg://...``)
into a plain psycopg URL.
"""

from __future__ import annotations

import asyncio
import logging
import re

from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver
from psycopg_pool import AsyncConnectionPool

from app.core.config import get_settings

_log = logging.getLogger(__name__)

_pool: AsyncConnectionPool | None = None
_saver: AsyncPostgresSaver | None = None
_setup_done = False
_init_lock = asyncio.Lock()


def _psycopg_dsn() -> str:
    url = get_settings().database_url
    # SQLAlchemy form → plain libpq form expected by psycopg.
    return re.sub(r"^postgresql\+asyncpg://", "postgresql://", url)


async def get_checkpointer() -> AsyncPostgresSaver:
    """Return the singleton checkpointer, initialising it on first call."""
    global _pool, _saver, _setup_done  # noqa: PLW0603
    if _saver is not None and _setup_done:
        return _saver

    async with _init_lock:
        if _saver is None:
            _pool = AsyncConnectionPool(
                conninfo=_psycopg_dsn(),
                kwargs={"autocommit": True, "prepare_threshold": 0},
                min_size=1,
                max_size=4,
                open=False,
            )
            await _pool.open()
            _saver = AsyncPostgresSaver(conn=_pool)  # type: ignore[arg-type]
            _log.info("workflow checkpointer: connection pool ready")

        if not _setup_done:
            await _saver.setup()
            _setup_done = True
            _log.info("workflow checkpointer: tables ensured (langgraph setup)")

    return _saver


async def close_checkpointer() -> None:
    """Close the connection pool on shutdown."""
    global _pool, _saver, _setup_done  # noqa: PLW0603
    if _pool is not None:
        await _pool.close()
        _pool = None
    _saver = None
    _setup_done = False
