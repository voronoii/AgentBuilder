from __future__ import annotations

from fastapi import FastAPI

from app.api.health import router as health_router
from app.core.config import APP_VERSION, get_settings


def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(
        title=settings.app_name,
        version=APP_VERSION,
        debug=settings.debug,
    )

    # Root routes only. API versioning is intentionally deferred — see
    # docs/specs/2026-04-08-agentbuilder-design.md §11.1 for the restoration
    # procedure (when external consumers, breaking changes, or multi-client
    # support arrive).
    app.include_router(health_router)

    return app


app = create_app()
