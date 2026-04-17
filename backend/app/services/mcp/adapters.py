"""MCP transport adapters — STDIO, HTTP/SSE, and Streamable HTTP.

Each adapter implements:
  connect()    — establish session with MCP server
  list_tools() — call list_tools and return raw tool dicts
  close()      — release resources

Design notes:
- Adapters are short-lived: connect → list_tools → close for discovery.
- M4 will reuse the same adapters for long-lived tool execution sessions.
- Timeout is enforced via asyncio.wait_for to avoid hanging connections.
"""

from __future__ import annotations

import asyncio
import logging
from typing import Any

from mcp import ClientSession, StdioServerParameters
from mcp.client.sse import sse_client
from mcp.client.stdio import stdio_client
from mcp.client.streamable_http import streamablehttp_client

_log = logging.getLogger(__name__)

_DEFAULT_TIMEOUT = 30  # seconds


def _tool_to_dict(tool: Any) -> dict[str, Any]:
    """Convert MCP Tool object to a plain dict for JSON storage."""
    schema: dict[str, Any] = {}
    if hasattr(tool, "inputSchema") and tool.inputSchema is not None:
        raw = tool.inputSchema
        schema = raw.model_dump() if hasattr(raw, "model_dump") else dict(raw)
    return {
        "name": str(tool.name),
        "description": str(getattr(tool, "description", "") or ""),
        "input_schema": schema,
    }


class StdioAdapter:
    """Launch a local MCP server via subprocess (STDIO transport)."""

    def __init__(
        self,
        command: str,
        args: list[str] | None = None,
        env: dict[str, str] | None = None,
        timeout: float = _DEFAULT_TIMEOUT,
    ) -> None:
        self._params = StdioServerParameters(
            command=command,
            args=args or [],
            env=env or {},
        )
        self._timeout = timeout
        self._session: ClientSession | None = None
        self._exit_stack: Any = None

    async def connect(self) -> None:
        from contextlib import AsyncExitStack

        self._exit_stack = AsyncExitStack()
        read, write = await asyncio.wait_for(
            self._exit_stack.enter_async_context(stdio_client(self._params)),
            timeout=self._timeout,
        )
        self._session = await asyncio.wait_for(
            self._exit_stack.enter_async_context(ClientSession(read, write)),
            timeout=self._timeout,
        )
        await asyncio.wait_for(self._session.initialize(), timeout=self._timeout)

    async def list_tools(self) -> list[dict[str, Any]]:
        if self._session is None:
            raise RuntimeError("StdioAdapter not connected — call connect() first")
        result = await asyncio.wait_for(self._session.list_tools(), timeout=self._timeout)
        return [_tool_to_dict(t) for t in result.tools]

    async def close(self) -> None:
        if self._exit_stack is not None:
            try:
                await self._exit_stack.aclose()
            except Exception:
                _log.debug("StdioAdapter.close: ignored error during cleanup", exc_info=True)
            finally:
                self._exit_stack = None
                self._session = None


class HttpSseAdapter:
    """Connect to a remote MCP server over HTTP/SSE transport."""

    def __init__(
        self,
        url: str,
        headers: dict[str, str] | None = None,
        env: dict[str, str] | None = None,
        timeout: float = _DEFAULT_TIMEOUT,
    ) -> None:
        self._url = url
        self._headers = headers or {}
        _ = env  # env_vars are informational for HTTP transports
        self._timeout = timeout
        self._session: ClientSession | None = None
        self._exit_stack: Any = None

    async def connect(self) -> None:
        from contextlib import AsyncExitStack

        self._exit_stack = AsyncExitStack()
        read, write = await asyncio.wait_for(
            self._exit_stack.enter_async_context(sse_client(self._url, headers=self._headers)),
            timeout=self._timeout,
        )
        self._session = await asyncio.wait_for(
            self._exit_stack.enter_async_context(ClientSession(read, write)),
            timeout=self._timeout,
        )
        await asyncio.wait_for(self._session.initialize(), timeout=self._timeout)

    async def list_tools(self) -> list[dict[str, Any]]:
        if self._session is None:
            raise RuntimeError("HttpSseAdapter not connected — call connect() first")
        result = await asyncio.wait_for(self._session.list_tools(), timeout=self._timeout)
        return [_tool_to_dict(t) for t in result.tools]

    async def close(self) -> None:
        if self._exit_stack is not None:
            try:
                await self._exit_stack.aclose()
            except Exception:
                _log.debug("HttpSseAdapter.close: ignored error during cleanup", exc_info=True)
            finally:
                self._exit_stack = None
                self._session = None


class StreamableHttpAdapter:
    """Connect to a remote MCP server over Streamable HTTP transport (MCP spec 2025-03-26+)."""

    def __init__(
        self,
        url: str,
        headers: dict[str, str] | None = None,
        env: dict[str, str] | None = None,
        timeout: float = _DEFAULT_TIMEOUT,
    ) -> None:
        self._url = url
        self._headers = headers or {}
        _ = env  # env_vars are informational for HTTP transports
        self._timeout = timeout
        self._session: ClientSession | None = None
        self._exit_stack: Any = None

    async def connect(self) -> None:
        from contextlib import AsyncExitStack

        self._exit_stack = AsyncExitStack()
        read, write, _ = await asyncio.wait_for(
            self._exit_stack.enter_async_context(
                streamablehttp_client(self._url, headers=self._headers)
            ),
            timeout=self._timeout,
        )
        self._session = await asyncio.wait_for(
            self._exit_stack.enter_async_context(ClientSession(read, write)),
            timeout=self._timeout,
        )
        await asyncio.wait_for(self._session.initialize(), timeout=self._timeout)

    async def list_tools(self) -> list[dict[str, Any]]:
        if self._session is None:
            raise RuntimeError("StreamableHttpAdapter not connected — call connect() first")
        result = await asyncio.wait_for(self._session.list_tools(), timeout=self._timeout)
        return [_tool_to_dict(t) for t in result.tools]

    async def close(self) -> None:
        if self._exit_stack is not None:
            try:
                await self._exit_stack.aclose()
            except Exception:
                _log.debug(
                    "StreamableHttpAdapter.close: ignored error during cleanup", exc_info=True
                )
            finally:
                self._exit_stack = None
                self._session = None
