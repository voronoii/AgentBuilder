from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_session
from app.core.errors import AppError, ErrorCode
from app.repositories.settings import SettingsRepository
from app.schemas.settings import SettingBulkUpdate, SettingCreate, SettingRead, SettingUpdate

router = APIRouter(prefix="/settings", tags=["settings"])


def _mask_secret(setting: SettingRead) -> SettingRead:
    """Mask secret values in API responses — show only last 4 chars."""
    if setting.is_secret and setting.value:
        masked = "*" * 8 + setting.value[-4:]
        return setting.model_copy(update={"value": masked})
    return setting


@router.get("", response_model=list[SettingRead])
async def list_settings(
    session: Annotated[AsyncSession, Depends(get_session)],
) -> list[SettingRead]:
    repo = SettingsRepository(session)
    settings = await repo.list_all()
    reads = [SettingRead.model_validate(s) for s in settings]
    return [_mask_secret(r) for r in reads]


@router.post("", response_model=SettingRead, status_code=201)
async def create_setting(
    payload: SettingCreate,
    session: Annotated[AsyncSession, Depends(get_session)],
) -> SettingRead:
    repo = SettingsRepository(session)
    existing = await repo.get(payload.key)
    if existing is not None:
        raise AppError(
            status_code=409,
            code=ErrorCode.VALIDATION_FAILED,
            detail=f"Setting '{payload.key}' already exists",
        )
    setting = await repo.create(
        key=payload.key,
        value=payload.value,
        description=payload.description,
        category=payload.category,
        is_secret=payload.is_secret,
    )
    await session.commit()
    result = SettingRead.model_validate(setting)
    return _mask_secret(result)


@router.delete("/{key}")
async def delete_setting(
    key: str,
    session: Annotated[AsyncSession, Depends(get_session)],
) -> dict:
    repo = SettingsRepository(session)
    deleted = await repo.delete(key)
    if not deleted:
        raise AppError(
            status_code=404,
            code=ErrorCode.SETTING_NOT_FOUND,
            detail=f"Setting '{key}' not found",
        )
    await session.commit()
    return {"ok": True}


@router.put("/{key}", response_model=SettingRead)
async def update_setting(
    key: str,
    payload: SettingUpdate,
    session: Annotated[AsyncSession, Depends(get_session)],
) -> SettingRead:
    repo = SettingsRepository(session)
    setting = await repo.set_value(key, payload.value)
    await session.commit()
    result = SettingRead.model_validate(setting)
    return _mask_secret(result)


@router.put("", response_model=list[SettingRead])
async def bulk_update_settings(
    payload: SettingBulkUpdate,
    session: Annotated[AsyncSession, Depends(get_session)],
) -> list[SettingRead]:
    repo = SettingsRepository(session)
    settings = await repo.bulk_update(payload.settings)
    await session.commit()
    reads = [SettingRead.model_validate(s) for s in settings]
    return [_mask_secret(r) for r in reads]


# NOTE: raw-secret endpoint removed (2026-04-12 code review H3).
# Backend services access secrets via SettingsRepository.get_value() directly,
# not through HTTP. No unmasked secret value is exposed over the network.
