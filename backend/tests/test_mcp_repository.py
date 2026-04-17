"""MCPRepository CRUD tests — SQLite in-memory."""
from __future__ import annotations

import pytest

from app.models.mcp import MCPTransport
from app.repositories.mcp import MCPRepository
from app.schemas.mcp import MCPServerCreate, MCPServerUpdate


def _stdio_payload(name: str = "test-server") -> MCPServerCreate:
    return MCPServerCreate(
        name=name,
        description="test",
        transport=MCPTransport.STDIO,
        config={"command": "echo", "args": []},
        env_vars={"FOO": "bar"},
    )


@pytest.mark.asyncio
async def test_create_and_get(db_session):
    repo = MCPRepository(db_session)
    server = await repo.create(_stdio_payload())
    await db_session.flush()

    found = await repo.get_by_id(server.id)
    assert found is not None
    assert found.name == "test-server"
    assert found.env_vars == {"FOO": "bar"}


@pytest.mark.asyncio
async def test_list_all_empty(db_session):
    repo = MCPRepository(db_session)
    results = await repo.list_all()
    assert results == []


@pytest.mark.asyncio
async def test_list_all_multiple(db_session):
    repo = MCPRepository(db_session)
    for i in range(3):
        await repo.create(_stdio_payload(f"srv-{i}"))
    await db_session.flush()

    results = await repo.list_all()
    assert len(results) == 3


@pytest.mark.asyncio
async def test_update_fields(db_session):
    repo = MCPRepository(db_session)
    server = await repo.create(_stdio_payload())
    await db_session.flush()

    updated = await repo.update(
        server.id,
        MCPServerUpdate(description="updated", enabled=False),
    )
    assert updated is not None
    assert updated.description == "updated"
    assert updated.enabled is False


@pytest.mark.asyncio
async def test_delete(db_session):
    repo = MCPRepository(db_session)
    server = await repo.create(_stdio_payload())
    await db_session.flush()

    await repo.delete(server.id)
    await db_session.flush()

    assert await repo.get_by_id(server.id) is None


@pytest.mark.asyncio
async def test_update_discovered_tools(db_session):
    repo = MCPRepository(db_session)
    server = await repo.create(_stdio_payload())
    await db_session.flush()

    tools = [{"name": "read_file", "description": "Read a file", "input_schema": {}}]
    await repo.update_discovered_tools(server.id, tools)
    await db_session.flush()

    updated = await repo.get_by_id(server.id)
    assert updated is not None
    assert len(updated.discovered_tools) == 1
    assert updated.discovered_tools[0]["name"] == "read_file"
    assert updated.last_discovered_at is not None
