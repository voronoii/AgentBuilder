from __future__ import annotations

from fastapi import FastAPI

from app.api.health import router as health_router
from app.core.config import get_settings


def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(
        title=settings.app_name,
        version="0.0.1",
        debug=settings.debug,
    )

    # Top-level health (load balancers, docker healthchecks)
    app.include_router(health_router)

    # Versioned API surface — every future router lives under /api/v1
    app.include_router(health_router, prefix="/api/v1")

    return app


app = create_app()
