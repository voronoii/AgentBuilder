from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.settings import AppSetting


class SettingsRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def list_all(self) -> list[AppSetting]:
        result = await self._session.execute(
            select(AppSetting).order_by(AppSetting.category, AppSetting.key)
        )
        return list(result.scalars().all())

    async def get(self, key: str) -> AppSetting | None:
        return await self._session.get(AppSetting, key)

    async def get_value(self, key: str) -> str | None:
        """Return the value for a key, or None if not found or empty."""
        setting = await self.get(key)
        if setting is None or not setting.value:
            return None
        return setting.value

    async def set_value(self, key: str, value: str) -> AppSetting:
        setting = await self.get(key)
        if setting is None:
            setting = AppSetting(key=key, value=value)
            self._session.add(setting)
        else:
            setting.value = value
        await self._session.flush()
        await self._session.refresh(setting)
        return setting

    async def create(
        self,
        key: str,
        value: str = "",
        description: str = "",
        category: str = "general",
        is_secret: bool = False,
    ) -> AppSetting:
        existing = await self.get(key)
        if existing is not None:
            raise ValueError(f"Setting '{key}' already exists")
        setting = AppSetting(
            key=key,
            value=value,
            description=description,
            category=category,
            is_secret=is_secret,
        )
        self._session.add(setting)
        await self._session.flush()
        await self._session.refresh(setting)
        return setting

    async def delete(self, key: str) -> bool:
        setting = await self.get(key)
        if setting is None:
            return False
        await self._session.delete(setting)
        await self._session.flush()
        return True

    async def bulk_update(self, updates: dict[str, str]) -> list[AppSetting]:
        results: list[AppSetting] = []
        for key, value in updates.items():
            s = await self.set_value(key, value)
            results.append(s)
        return results
