from __future__ import annotations

import logging
import uuid
from typing import Annotated

from fastapi import APIRouter, BackgroundTasks, Depends, status
from fastapi.responses import Response
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.db import get_session
from app.core.errors import AppError, ErrorCode
from app.models.mcp import MCPServer
from app.repositories.mcp import MCPRepository
from app.schemas.mcp import MCPServerCreate, MCPServerRead, MCPServerUpdate
from app.services.mcp.discovery import discover_tools

_log = logging.getLogger(__name__)

router = APIRouter(prefix="/mcp", tags=["mcp"])


# ---------- helpers ----------


async def _get_or_404(server_id: uuid.UUID, session: AsyncSession) -> MCPServer:
    server = await MCPRepository(session).get_by_id(server_id)
    if server is None:
        raise AppError(
            status_code=404,
            code=ErrorCode.MCP_NOT_FOUND,
            detail=f"MCP server {server_id} not found",
        )
    return server


async def _try_discover(server_id: uuid.UUID, timeout: float) -> None:
    """Attempt discovery in a fresh DB session (non-fatal for registration).

    Uses its own session to avoid reusing the request-scoped session
    which may already be closed by the time this background task runs.
    """
    from app.core.db import get_sessionmaker  # noqa: PLC0415

    try:
        async with get_sessionmaker()() as session:
            server = await MCPRepository(session).get_by_id(server_id)
            if server is None:
                _log.warning("Auto-discovery: server %s not found", server_id)
                return
            await discover_tools(server, session, timeout=timeout)
            await session.commit()
    except AppError as exc:
        _log.warning("Auto-discovery failed for server %s: %s", server_id, exc.detail)
    except Exception as exc:  # noqa: BLE001
        _log.warning("Auto-discovery failed for server %s: %s", server_id, exc)


# ---------- CRUD ----------


@router.post("", response_model=MCPServerRead, status_code=status.HTTP_201_CREATED)
async def create_mcp_server(
    payload: MCPServerCreate,
    session: Annotated[AsyncSession, Depends(get_session)],
    background_tasks: BackgroundTasks,
) -> MCPServer:
    repo = MCPRepository(session)
    try:
        server = await repo.create(payload)
        await session.commit()
    except IntegrityError as exc:
        raise AppError(
            status_code=409,
            code=ErrorCode.MCP_DUPLICATE_NAME,
            detail=f"MCP server with name '{payload.name}' already exists",
        ) from exc
    # Trigger discovery in background so registration always succeeds
    settings = get_settings()
    background_tasks.add_task(_try_discover, server.id, float(settings.mcp_discovery_timeout))
    return server


@router.get("", response_model=list[MCPServerRead])
async def list_mcp_servers(
    session: Annotated[AsyncSession, Depends(get_session)],
) -> list[MCPServer]:
    return await MCPRepository(session).list_all()


@router.get("/{server_id}", response_model=MCPServerRead)
async def get_mcp_server(
    server_id: uuid.UUID,
    session: Annotated[AsyncSession, Depends(get_session)],
) -> MCPServer:
    return await _get_or_404(server_id, session)


@router.put("/{server_id}", response_model=MCPServerRead)
async def update_mcp_server(
    server_id: uuid.UUID,
    payload: MCPServerUpdate,
    session: Annotated[AsyncSession, Depends(get_session)],
) -> MCPServer:
    repo = MCPRepository(session)
    await _get_or_404(server_id, session)
    try:
        server = await repo.update(server_id, payload)
        await session.commit()
    except IntegrityError as exc:
        raise AppError(
            status_code=409,
            code=ErrorCode.MCP_DUPLICATE_NAME,
            detail=f"MCP server with name '{payload.name}' already exists",
        ) from exc
    assert server is not None  # guaranteed by _get_or_404
    await session.refresh(server)
    return server


@router.delete("/{server_id}", status_code=status.HTTP_204_NO_CONTENT, response_class=Response)
async def delete_mcp_server(
    server_id: uuid.UUID,
    session: Annotated[AsyncSession, Depends(get_session)],
) -> Response:
    await MCPRepository(session).delete(server_id)
    await session.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)


# ---------- Discovery ----------


@router.post("/{server_id}/discover", response_model=MCPServerRead)
async def rediscover_tools(
    server_id: uuid.UUID,
    session: Annotated[AsyncSession, Depends(get_session)],
) -> MCPServer:
    """Manually trigger tool discovery for a registered MCP server."""
    server = await _get_or_404(server_id, session)
    settings = get_settings()
    await discover_tools(server, session, timeout=float(settings.mcp_discovery_timeout))
    await session.commit()
    # Reload to get updated fields
    updated = await MCPRepository(session).get_by_id(server_id)
    assert updated is not None
    return updated
