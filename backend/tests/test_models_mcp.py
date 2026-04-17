"""Unit tests for MCPServer model — SQLite in-memory."""
from __future__ import annotations

import pytest
from sqlalchemy import select

from app.models.mcp import MCPServer, MCPTransport


@pytest.mark.asyncio
async def test_create_stdio_server(db_session):
    server = MCPServer(
        name="filesystem",
        description="local filesystem",
        transport=MCPTransport.STDIO,
        config={"command": "npx", "args": ["@modelcontextprotocol/server-filesystem", "/tmp"]},
        env_vars={},
    )
    db_session.add(server)
    await db_session.flush()

    result = await db_session.get(MCPServer, server.id)
    assert result is not None
    assert result.name == "filesystem"
    assert result.transport == MCPTransport.STDIO
    assert result.enabled is True
    assert result.discovered_tools == []
    assert result.last_discovered_at is None


@pytest.mark.asyncio
async def test_create_http_sse_server(db_session):
    server = MCPServer(
        name="web-search",
        transport=MCPTransport.HTTP_SSE,
        config={"url": "https://example.com/mcp", "headers": {"Authorization": "Bearer tok"}},
        env_vars={},
    )
    db_session.add(server)
    await db_session.flush()

    result = await db_session.get(MCPServer, server.id)
    assert result is not None
    assert result.transport == MCPTransport.HTTP_SSE
    assert result.config["url"] == "https://example.com/mcp"


@pytest.mark.asyncio
async def test_unique_name_constraint(db_session):
    from sqlalchemy.exc import IntegrityError

    db_session.add(MCPServer(name="dup", transport=MCPTransport.STDIO, config={}, env_vars={}))
    await db_session.flush()

    db_session.add(MCPServer(name="dup", transport=MCPTransport.STDIO, config={}, env_vars={}))
    with pytest.raises(IntegrityError):
        await db_session.flush()


@pytest.mark.asyncio
async def test_list_all(db_session):
    for i in range(3):
        db_session.add(
            MCPServer(
                name=f"server-{i}",
                transport=MCPTransport.STDIO,
                config={},
                env_vars={},
            )
        )
    await db_session.flush()

    result = await db_session.execute(select(MCPServer))
    servers = list(result.scalars().all())
    assert len(servers) == 3
