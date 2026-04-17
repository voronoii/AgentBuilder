"""Tool discovery service.

Connects to a registered MCP server, calls list_tools, and caches the result
in the database. Connection errors surface as AppError(MCP_DISCOVERY_FAILED).
"""

from __future__ import annotations

import contextlib
import logging
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import AppError, ErrorCode
from app.models.mcp import MCPServer, MCPTransport
from app.repositories.mcp import MCPRepository
from app.services.mcp.adapters import HttpSseAdapter, StdioAdapter, StreamableHttpAdapter

_log = logging.getLogger(__name__)


def _build_adapter(
    server: MCPServer, timeout: float
) -> StdioAdapter | HttpSseAdapter | StreamableHttpAdapter:
    cfg: dict[str, Any] = server.config or {}
    env: dict[str, str] = server.env_vars or {}

    if server.transport == MCPTransport.STDIO:
        command = cfg.get("command", "")
        if not command:
            raise AppError(
                status_code=422,
                code=ErrorCode.MCP_DISCOVERY_FAILED,
                detail="STDIO server config missing 'command'",
            )
        args: list[str] = cfg.get("args", [])
        return StdioAdapter(command=command, args=args, env=env, timeout=timeout)

    # HTTP-based transports (SSE and Streamable HTTP) share the same config shape
    url = cfg.get("url", "")
    if not url:
        raise AppError(
            status_code=422,
            code=ErrorCode.MCP_DISCOVERY_FAILED,
            detail=f"{server.transport} server config missing 'url'",
        )
    headers: dict[str, str] = cfg.get("headers", {})

    if server.transport == MCPTransport.STREAMABLE_HTTP:
        return StreamableHttpAdapter(url=url, headers=headers, env=env, timeout=timeout)

    # HTTP_SSE
    return HttpSseAdapter(url=url, headers=headers, env=env, timeout=timeout)


async def discover_tools(
    server: MCPServer,
    session: AsyncSession,
    *,
    timeout: float = 30.0,
) -> list[dict[str, Any]]:
    """Connect to MCP server, list tools, cache in DB. Returns tool dicts."""
    adapter = _build_adapter(server, timeout)

    try:
        await adapter.connect()
        tools = await adapter.list_tools()
    except AppError:
        raise
    except Exception as exc:
        _log.warning(
            "MCP discovery failed for server %s (%s): %s",
            server.name,
            server.id,
            exc,
        )
        raise AppError(
            status_code=502,
            code=ErrorCode.MCP_DISCOVERY_FAILED,
            detail=f"failed to connect to MCP server '{server.name}': {exc}",
        ) from exc
    finally:
        with contextlib.suppress(Exception):
            await adapter.close()

    repo = MCPRepository(session)
    await repo.update_discovered_tools(server.id, tools)
    _log.info("Discovered %d tools from MCP server '%s'", len(tools), server.name)
    return tools
