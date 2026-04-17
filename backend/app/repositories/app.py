from __future__ import annotations

import secrets
import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.app import PublishedApp
from app.schemas.app import AppCreate, AppUpdate


class AppRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create(self, payload: AppCreate) -> PublishedApp:
        app = PublishedApp(
            workflow_id=payload.workflow_id,
            name=payload.name,
            description=payload.description,
            icon_url=payload.icon_url,
            welcome_message=payload.welcome_message,
            placeholder_text=payload.placeholder_text,
        )
        self._session.add(app)
        await self._session.flush()
        return app

    async def list_all(self) -> list[PublishedApp]:
        result = await self._session.execute(
            select(PublishedApp).order_by(PublishedApp.updated_at.desc())
        )
        return list(result.scalars().all())

    async def get(self, app_id: uuid.UUID) -> PublishedApp | None:
        return await self._session.get(PublishedApp, app_id)

    async def get_by_workflow(self, workflow_id: uuid.UUID) -> PublishedApp | None:
        result = await self._session.execute(
            select(PublishedApp).where(PublishedApp.workflow_id == workflow_id)
        )
        return result.scalar_one_or_none()

    async def get_by_api_key(self, api_key: str) -> PublishedApp | None:
        result = await self._session.execute(
            select(PublishedApp).where(PublishedApp.api_key == api_key)
        )
        return result.scalar_one_or_none()

    async def update(self, app_id: uuid.UUID, payload: AppUpdate) -> PublishedApp | None:
        app = await self.get(app_id)
        if app is None:
            return None
        for field, value in payload.model_dump(exclude_unset=True).items():
            setattr(app, field, value)
        await self._session.flush()
        await self._session.refresh(app)
        return app

    async def toggle_active(self, app_id: uuid.UUID) -> PublishedApp | None:
        app = await self.get(app_id)
        if app is None:
            return None
        app.is_active = not app.is_active
        await self._session.flush()
        await self._session.refresh(app)
        return app

    async def regenerate_key(self, app_id: uuid.UUID) -> PublishedApp | None:
        app = await self.get(app_id)
        if app is None:
            return None
        app.api_key = f"sk-{secrets.token_urlsafe(32)}"
        await self._session.flush()
        await self._session.refresh(app)
        return app

    async def delete(self, app_id: uuid.UUID) -> bool:
        app = await self.get(app_id)
        if app is None:
            return False
        await self._session.delete(app)
        await self._session.flush()
        return True
