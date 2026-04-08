from __future__ import annotations

from fastapi import APIRouter, Depends

from app.core.config import Settings, get_settings

router = APIRouter(tags=["health"])

APP_VERSION = "0.0.1"


@router.get("/health")
async def health(settings: Settings = Depends(get_settings)) -> dict[str, str]:
    """Process-level liveness. Does NOT touch the database (M1 will add /ready)."""
    return {
        "status": "ok",
        "app": settings.app_name,
        "version": APP_VERSION,
    }
