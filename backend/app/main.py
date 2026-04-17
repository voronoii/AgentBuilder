from __future__ import annotations

import logging
from contextlib import asynccontextmanager
from typing import AsyncIterator

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.apps import router as apps_router
from app.api.health import router as health_router
from app.api.knowledge import router as knowledge_router
from app.api.mcp import router as mcp_router
from app.api.providers import router as providers_router
from app.api.runs import routers as run_routers
from app.api.serving import router as serving_router
from app.api.settings import router as settings_router
from app.api.workflow import router as workflow_router
from app.core.config import APP_VERSION, get_settings
from app.core.errors import register_exception_handlers
from app.core.request_id import RequestIdMiddleware

_log = logging.getLogger(__name__)


@asynccontextmanager
async def _lifespan(app: FastAPI) -> AsyncIterator[None]:  # noqa: ARG001
    # ── startup ────────────────────────────────────────────────────────

    # Auto-create tables for sqlite (test mode). No-op for postgres.
    from app.core.db import get_engine
    from app.models.base import Base

    url = str(get_engine().url)
    if url.startswith("sqlite"):
        async with get_engine().begin() as conn:
            await conn.run_sync(Base.metadata.create_all)

    # Mark stale processing documents as failed after restart.
    try:
        from app.core.db import get_sessionmaker
        from app.repositories.knowledge import KnowledgeRepository

        async with get_sessionmaker()() as session:
            changed = await KnowledgeRepository(session).mark_stale_processing_failed()
            await session.commit()
            if changed:
                _log.warning("startup recovery: marked %d stale documents as failed", changed)
    except Exception:  # noqa: BLE001
        _log.warning("startup recovery skipped (db not available)")

    # Mark all 'running' workflow runs as 'failed' after an unexpected restart.
    try:
        from app.core.db import get_sessionmaker
        from app.repositories.run import RunRepository

        async with get_sessionmaker()() as session:
            changed = await RunRepository(session).mark_stale_runs_failed()
            await session.commit()
            if changed:
                _log.warning(
                    "startup recovery: marked %d stale workflow runs as failed", changed
                )
    except Exception:  # noqa: BLE001
        _log.warning("startup runs recovery skipped (db not available)")

    yield
    # ── shutdown (nothing to do yet) ───────────────────────────────────


def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(
        title=settings.app_name,
        version=APP_VERSION,
        debug=settings.debug,
        lifespan=_lifespan,
    )

    # Middleware — order matters (outermost first)
    app.add_middleware(RequestIdMiddleware)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_methods=["*"],
        allow_headers=["*"],
        allow_credentials=True,
        expose_headers=["X-Request-ID"],
    )
    register_exception_handlers(app)

    # Root routes only. API versioning is intentionally deferred — see
    # docs/specs/2026-04-08-agentbuilder-design.md §11.1
    app.include_router(health_router)
    app.include_router(knowledge_router)
    app.include_router(mcp_router)
    app.include_router(workflow_router)
    app.include_router(providers_router)
    app.include_router(settings_router)
    app.include_router(apps_router)
    app.include_router(serving_router)
    for router in run_routers:
        app.include_router(router)

    return app


app = create_app()
