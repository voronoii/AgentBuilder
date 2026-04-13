from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.mcp import MCPServer
from app.schemas.mcp import MCPServerCreate, MCPServerUpdate


class MCPRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create(self, payload: MCPServerCreate) -> MCPServer:
        server = MCPServer(
            name=payload.name,
            description=payload.description,
            transport=payload.transport,
            config=payload.config,
            env_vars=payload.env_vars,
        )
        self._session.add(server)
        await self._session.flush()
        return server

    async def list_all(self) -> list[MCPServer]:
        result = await self._session.execute(
            select(MCPServer).order_by(MCPServer.created_at.desc())
        )
        return list(result.scalars().all())

    async def get_by_id(self, server_id: uuid.UUID) -> MCPServer | None:
        return await self._session.get(MCPServer, server_id)

    async def update(self, server_id: uuid.UUID, payload: MCPServerUpdate) -> MCPServer | None:
        server = await self.get_by_id(server_id)
        if server is None:
            return None
        if payload.name is not None:
            server.name = payload.name
        if payload.description is not None:
            server.description = payload.description
        if payload.config is not None:
            server.config = payload.config
        if payload.env_vars is not None:
            server.env_vars = payload.env_vars
        if payload.enabled is not None:
            server.enabled = payload.enabled
        await self._session.flush()
        return server

    async def delete(self, server_id: uuid.UUID) -> None:
        server = await self.get_by_id(server_id)
        if server is not None:
            await self._session.delete(server)
            await self._session.flush()

    async def update_discovered_tools(
        self,
        server_id: uuid.UUID,
        tools: list[dict[str, Any]],
    ) -> None:
        server = await self.get_by_id(server_id)
        if server is None:
            return
        server.discovered_tools = tools
        server.last_discovered_at = datetime.now(tz=UTC)
        await self._session.flush()
