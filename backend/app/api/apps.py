from __future__ import annotations

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, status
from fastapi.responses import Response
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_session
from app.core.errors import AppError, ErrorCode
from app.repositories.app import AppRepository
from app.schemas.app import AppConfig, AppCreate, AppRead, AppUpdate

router = APIRouter(prefix="/apps", tags=["apps"])


def _mask_key(key: str) -> str:
    return "sk-" + "\u2022" * 8 + key[-4:]


def _read_with_masked_key(app) -> dict:  # type: ignore[type-arg]
    data = AppRead.model_validate(app).model_dump()
    data["api_key"] = _mask_key(app.api_key)
    return data


# ---------- Publish ----------


@router.post("", status_code=status.HTTP_201_CREATED)
async def publish_app(
    payload: AppCreate,
    session: Annotated[AsyncSession, Depends(get_session)],
) -> dict:
    repo = AppRepository(session)
    existing = await repo.get_by_workflow(payload.workflow_id)
    if existing is not None:
        raise AppError(
            status_code=409,
            code=ErrorCode.APP_ALREADY_EXISTS,
            detail="이 워크플로우는 이미 게시되어 있습니다.",
        )
    app = await repo.create(payload)
    await session.commit()
    await session.refresh(app)
    # Return full api_key on creation
    return AppRead.model_validate(app).model_dump()


# ---------- List ----------


@router.get("", response_model=list[dict])
async def list_apps(
    session: Annotated[AsyncSession, Depends(get_session)],
) -> list[dict]:
    apps = await AppRepository(session).list_all()
    return [_read_with_masked_key(a) for a in apps]


# ---------- Get ----------


@router.get("/{app_id}")
async def get_app(
    app_id: uuid.UUID,
    session: Annotated[AsyncSession, Depends(get_session)],
) -> dict:
    app = await AppRepository(session).get(app_id)
    if app is None:
        raise AppError(
            status_code=404,
            code=ErrorCode.APP_NOT_FOUND,
            detail="앱을 찾을 수 없습니다.",
        )
    return _read_with_masked_key(app)


# ---------- Update ----------


@router.put("/{app_id}")
async def update_app(
    app_id: uuid.UUID,
    payload: AppUpdate,
    session: Annotated[AsyncSession, Depends(get_session)],
) -> dict:
    repo = AppRepository(session)
    app = await repo.update(app_id, payload)
    if app is None:
        raise AppError(
            status_code=404,
            code=ErrorCode.APP_NOT_FOUND,
            detail="앱을 찾을 수 없습니다.",
        )
    await session.commit()
    return _read_with_masked_key(app)


# ---------- Delete ----------


@router.delete("/{app_id}", status_code=status.HTTP_204_NO_CONTENT, response_class=Response)
async def delete_app(
    app_id: uuid.UUID,
    session: Annotated[AsyncSession, Depends(get_session)],
) -> Response:
    deleted = await AppRepository(session).delete(app_id)
    if not deleted:
        raise AppError(
            status_code=404,
            code=ErrorCode.APP_NOT_FOUND,
            detail="앱을 찾을 수 없습니다.",
        )
    await session.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)


# ---------- Regenerate Key ----------


@router.post("/{app_id}/regenerate-key")
async def regenerate_key(
    app_id: uuid.UUID,
    session: Annotated[AsyncSession, Depends(get_session)],
) -> dict:
    repo = AppRepository(session)
    app = await repo.regenerate_key(app_id)
    if app is None:
        raise AppError(
            status_code=404,
            code=ErrorCode.APP_NOT_FOUND,
            detail="앱을 찾을 수 없습니다.",
        )
    await session.commit()
    # Return full new api_key
    return AppRead.model_validate(app).model_dump()


# ---------- Toggle ----------


@router.put("/{app_id}/toggle")
async def toggle_app(
    app_id: uuid.UUID,
    session: Annotated[AsyncSession, Depends(get_session)],
) -> dict:
    repo = AppRepository(session)
    app = await repo.toggle_active(app_id)
    if app is None:
        raise AppError(
            status_code=404,
            code=ErrorCode.APP_NOT_FOUND,
            detail="앱을 찾을 수 없습니다.",
        )
    await session.commit()
    return _read_with_masked_key(app)


# ---------- Public Config ----------


@router.get("/{app_id}/config", response_model=AppConfig)
async def get_app_config(
    app_id: uuid.UUID,
    session: Annotated[AsyncSession, Depends(get_session)],
) -> AppConfig:
    app = await AppRepository(session).get(app_id)
    if app is None:
        raise AppError(
            status_code=404,
            code=ErrorCode.APP_NOT_FOUND,
            detail="앱을 찾을 수 없습니다.",
        )
    return AppConfig.model_validate(app)


# ---------- Internal API Key (Next.js server-side proxy) ----------


@router.get("/{app_id}/api-key")
async def get_api_key(
    app_id: uuid.UUID,
    session: Annotated[AsyncSession, Depends(get_session)],
) -> dict:
    app = await AppRepository(session).get(app_id)
    if app is None:
        raise AppError(
            status_code=404,
            code=ErrorCode.APP_NOT_FOUND,
            detail="앱을 찾을 수 없습니다.",
        )
    return {"api_key": app.api_key}
