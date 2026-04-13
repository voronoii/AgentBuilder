"""Adapter unit tests — mock subprocess/HTTP, no real MCP binary required."""
from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.services.mcp.adapters import HttpSseAdapter, StdioAdapter, _tool_to_dict


# ---------- _tool_to_dict ----------


def test_tool_to_dict_basic():
    tool = SimpleNamespace(name="read_file", description="Read a file", inputSchema=None)
    result = _tool_to_dict(tool)
    assert result == {"name": "read_file", "description": "Read a file", "input_schema": {}}


def test_tool_to_dict_with_schema():
    schema = MagicMock()
    schema.model_dump.return_value = {"type": "object", "properties": {}}
    tool = SimpleNamespace(name="search", description="", inputSchema=schema)
    result = _tool_to_dict(tool)
    assert result["input_schema"] == {"type": "object", "properties": {}}


# ---------- StdioAdapter (mocked) ----------


@pytest.mark.asyncio
async def test_stdio_adapter_list_tools():
    mock_tool = SimpleNamespace(name="read_file", description="reads a file", inputSchema=None)
    mock_list_result = SimpleNamespace(tools=[mock_tool])

    mock_session = AsyncMock()
    mock_session.initialize = AsyncMock()
    mock_session.list_tools = AsyncMock(return_value=mock_list_result)
    mock_session.__aenter__ = AsyncMock(return_value=mock_session)
    mock_session.__aexit__ = AsyncMock(return_value=False)

    mock_read = AsyncMock()
    mock_write = AsyncMock()

    mock_transport_cm = MagicMock()
    mock_transport_cm.__aenter__ = AsyncMock(return_value=(mock_read, mock_write))
    mock_transport_cm.__aexit__ = AsyncMock(return_value=False)

    with patch("app.services.mcp.adapters.stdio_client", return_value=mock_transport_cm), patch(
        "app.services.mcp.adapters.ClientSession", return_value=mock_session
    ):
        adapter = StdioAdapter(command="echo", args=[], timeout=5.0)
        await adapter.connect()
        tools = await adapter.list_tools()
        await adapter.close()

    assert len(tools) == 1
    assert tools[0]["name"] == "read_file"


@pytest.mark.asyncio
async def test_stdio_adapter_close_without_connect():
    adapter = StdioAdapter(command="echo", args=[])
    # Should not raise
    await adapter.close()


# ---------- HttpSseAdapter (mocked) ----------


@pytest.mark.asyncio
async def test_http_sse_adapter_list_tools():
    mock_tool = SimpleNamespace(name="fetch", description="fetches URL", inputSchema=None)
    mock_list_result = SimpleNamespace(tools=[mock_tool])

    mock_session = AsyncMock()
    mock_session.initialize = AsyncMock()
    mock_session.list_tools = AsyncMock(return_value=mock_list_result)
    mock_session.__aenter__ = AsyncMock(return_value=mock_session)
    mock_session.__aexit__ = AsyncMock(return_value=False)

    mock_read = AsyncMock()
    mock_write = AsyncMock()

    mock_transport_cm = MagicMock()
    mock_transport_cm.__aenter__ = AsyncMock(return_value=(mock_read, mock_write))
    mock_transport_cm.__aexit__ = AsyncMock(return_value=False)

    with patch("app.services.mcp.adapters.sse_client", return_value=mock_transport_cm), patch(
        "app.services.mcp.adapters.ClientSession", return_value=mock_session
    ):
        adapter = HttpSseAdapter(url="https://example.com/mcp", timeout=5.0)
        await adapter.connect()
        tools = await adapter.list_tools()
        await adapter.close()

    assert len(tools) == 1
    assert tools[0]["name"] == "fetch"
