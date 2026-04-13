"""MCP API endpoint tests — TestClient with SQLite + mocked discovery."""
from __future__ import annotations

import uuid
from unittest.mock import AsyncMock, patch

import pytest
from httpx import ASGITransport, AsyncClient

from app.core.db import get_session
from app.main import create_app
from app.models.mcp import MCPTransport


@pytest.fixture
async def client(db_session):
    app = create_app()
    app.dependency_overrides[get_session] = lambda: db_session

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        yield c


_STDIO_PAYLOAD = {
    "name": "filesystem",
    "description": "local FS",
    "transport": "stdio",
    "config": {"command": "npx", "args": ["@modelcontextprotocol/server-filesystem", "/tmp"]},
    "env_vars": {},
}

_HTTP_PAYLOAD = {
    "name": "web-search",
    "description": "web search",
    "transport": "http_sse",
    "config": {"url": "https://example.com/mcp", "headers": {}},
    "env_vars": {},
}


async def _no_discover(*args, **kwargs):
    """Stub: skip actual network discovery."""
    return []


@pytest.mark.asyncio
async def test_create_mcp_server(client):
    with patch("app.api.mcp._try_discover", new=AsyncMock(side_effect=_no_discover)):
        res = await client.post("/mcp", json=_STDIO_PAYLOAD)
    assert res.status_code == 201
    body = res.json()
    assert body["name"] == "filesystem"
    assert body["transport"] == "stdio"
    assert body["enabled"] is True


@pytest.mark.asyncio
async def test_list_mcp_servers_empty(client):
    res = await client.get("/mcp")
    assert res.status_code == 200
    assert res.json() == []


@pytest.mark.asyncio
async def test_list_mcp_servers_after_create(client):
    with patch("app.api.mcp._try_discover", new=AsyncMock(side_effect=_no_discover)):
        await client.post("/mcp", json=_STDIO_PAYLOAD)
        await client.post("/mcp", json=_HTTP_PAYLOAD)

    res = await client.get("/mcp")
    assert res.status_code == 200
    assert len(res.json()) == 2


@pytest.mark.asyncio
async def test_get_mcp_server_not_found(client):
    res = await client.get(f"/mcp/{uuid.uuid4()}")
    assert res.status_code == 404
    assert res.json()["code"] == "MCP_NOT_FOUND"


@pytest.mark.asyncio
async def test_get_mcp_server_found(client):
    with patch("app.api.mcp._try_discover", new=AsyncMock(side_effect=_no_discover)):
        created = (await client.post("/mcp", json=_STDIO_PAYLOAD)).json()

    res = await client.get(f"/mcp/{created['id']}")
    assert res.status_code == 200
    assert res.json()["id"] == created["id"]


@pytest.mark.asyncio
async def test_update_mcp_server(client):
    with patch("app.api.mcp._try_discover", new=AsyncMock(side_effect=_no_discover)):
        created = (await client.post("/mcp", json=_STDIO_PAYLOAD)).json()

    res = await client.put(
        f"/mcp/{created['id']}", json={"description": "updated", "enabled": False}
    )
    assert res.status_code == 200
    body = res.json()
    assert body["description"] == "updated"
    assert body["enabled"] is False


@pytest.mark.asyncio
async def test_delete_mcp_server(client):
    with patch("app.api.mcp._try_discover", new=AsyncMock(side_effect=_no_discover)):
        created = (await client.post("/mcp", json=_STDIO_PAYLOAD)).json()

    res = await client.delete(f"/mcp/{created['id']}")
    assert res.status_code == 204

    res2 = await client.get(f"/mcp/{created['id']}")
    assert res2.status_code == 404


@pytest.mark.asyncio
async def test_duplicate_name_returns_409(client):
    with patch("app.api.mcp._try_discover", new=AsyncMock(side_effect=_no_discover)):
        await client.post("/mcp", json=_STDIO_PAYLOAD)
        res = await client.post("/mcp", json=_STDIO_PAYLOAD)
    assert res.status_code == 409
    assert res.json()["code"] == "MCP_DUPLICATE_NAME"


@pytest.mark.asyncio
async def test_discover_endpoint(client, db_session):
    with patch("app.api.mcp._try_discover", new=AsyncMock(side_effect=_no_discover)):
        created = (await client.post("/mcp", json=_STDIO_PAYLOAD)).json()

    fake_tools = [{"name": "read_file", "description": "read", "input_schema": {}}]

    async def _fake_discover(server, session, *, timeout=30):
        from app.repositories.mcp import MCPRepository
        repo = MCPRepository(session)
        await repo.update_discovered_tools(server.id, fake_tools)

    with patch("app.api.mcp.discover_tools", new=AsyncMock(side_effect=_fake_discover)):
        res = await client.post(f"/mcp/{created['id']}/discover")

    assert res.status_code == 200
    body = res.json()
    assert len(body["discovered_tools"]) == 1
    assert body["discovered_tools"][0]["name"] == "read_file"
