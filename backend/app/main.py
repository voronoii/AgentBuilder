from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.health import router as health_router
from app.core.config import APP_VERSION, get_settings
from app.core.errors import register_exception_handlers
from app.core.request_id import RequestIdMiddleware


def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(
        title=settings.app_name,
        version=APP_VERSION,
        debug=settings.debug,
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
    # docs/specs/2026-04-08-agentbuilder-design.md §11.1 for the restoration
    # procedure (when external consumers, breaking changes, or multi-client
    # support arrive).
    app.include_router(health_router)

    return app


app = create_app()
