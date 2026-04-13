"""Agent node — runs a ReAct agent with optional MCP tools and KB tools."""

from __future__ import annotations

import contextlib
import logging
import uuid
from collections.abc import Callable
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.nodes.utils import get_input_text
from app.repositories.mcp import MCPRepository
from app.services.mcp.adapters import HttpSseAdapter, StdioAdapter, StreamableHttpAdapter
from app.services.mcp.discovery import _build_adapter  # reuse adapter factory
from app.services.providers.chat.registry import make_chat_model_sync, resolve_provider_credentials
from app.services.workflow.state import WorkflowState

_log = logging.getLogger(__name__)


async def _load_mcp_tools(
    tool_names: list[str], session: AsyncSession,
) -> tuple[list[Any], list[Any]]:
    """Load LangChain-compatible tools from registered MCP servers.

    Fetches all enabled MCP servers from the DB, connects to each, lists
    available tools, and wraps any tool whose name appears in tool_names as a
    LangChain StructuredTool.

    Args:
        tool_names: Names of the tools to load (as configured in the Agent node).
        session: Active async DB session.

    Returns:
        Tuple of (tools, adapters) — caller must close adapters after use.
    """
    if not tool_names:
        return [], []

    from langchain_core.tools import StructuredTool
    from mcp import ClientSession
    from pydantic import BaseModel, create_model

    repo = MCPRepository(session)
    servers = await repo.list_all()

    tools: list[Any] = []
    connected_adapters: list[Any] = []
    tool_name_set = set(tool_names)

    for server in servers:
        if not server.enabled:
            continue

        discovered_names = {t["name"] for t in (server.discovered_tools or [])}
        if not discovered_names.intersection(tool_name_set):
            continue

        try:
            adapter = _build_adapter(server, timeout=30.0)
            await adapter.connect()
            connected_adapters.append(adapter)
        except Exception as exc:
            _log.warning("agent node: skipping MCP server %s — connect failed: %s", server.name, exc)
            continue

        try:
            raw_tools = await adapter.list_tools()
        except Exception as exc:
            _log.warning("agent node: skipping MCP server %s — list_tools failed: %s", server.name, exc)
            with contextlib.suppress(Exception):
                await adapter.close()
            connected_adapters.remove(adapter)
            continue

        for raw_tool in raw_tools:
            t_name: str = raw_tool["name"]
            if t_name not in tool_name_set:
                continue

            t_description: str = raw_tool.get("description", "")
            input_schema: dict = raw_tool.get("input_schema", {})

            props: dict = input_schema.get("properties", {})
            required: list[str] = input_schema.get("required", [])
            field_definitions: dict = {}
            for field_name, field_schema in props.items():
                field_type = str
                if field_schema.get("type") == "integer":
                    field_type = int
                elif field_schema.get("type") == "number":
                    field_type = float
                elif field_schema.get("type") == "boolean":
                    field_type = bool
                default = ... if field_name in required else None
                field_definitions[field_name] = (field_type, default)

            ArgsSchema: type[BaseModel] = create_model(f"{t_name}_Args", **field_definitions)  # type: ignore[call-overload]

            _adapter = adapter
            _t_name = t_name

            async def _call_tool(
                _a: StdioAdapter | HttpSseAdapter | StreamableHttpAdapter = _adapter,
                _n: str = _t_name,
                **kwargs: Any,
            ) -> str:
                mcp_session: ClientSession | None = getattr(_a, "_session", None)
                if mcp_session is None:
                    return f"[MCP tool {_n} unavailable: adapter not connected]"
                try:
                    result = await mcp_session.call_tool(_n, arguments=kwargs)
                    content = result.content
                    if isinstance(content, list):
                        parts = []
                        for item in content:
                            if hasattr(item, "text"):
                                parts.append(item.text)
                            else:
                                parts.append(str(item))
                        return "\n".join(parts)
                    return str(content)
                except Exception as exc:
                    _log.error("MCP tool %s call failed: %s", _n, exc)
                    return f"[Tool error: {exc}]"

            lc_tool = StructuredTool.from_function(
                coroutine=_call_tool,
                name=t_name,
                description=t_description,
                args_schema=ArgsSchema,
            )
            tools.append(lc_tool)

    return tools, connected_adapters


async def _close_adapters(adapters: list[Any]) -> None:
    """Close all MCP adapters, suppressing individual errors."""
    for adapter in adapters:
        with contextlib.suppress(Exception):
            await adapter.close()


async def _resolve_kb_metadata(
    kb_configs: list[dict], session: AsyncSession,
) -> list[dict]:
    """Resolve KB configs to full metadata at compile time.

    Must be called during compilation (while the DB session is available)
    to avoid session conflicts at runtime.
    """
    if not kb_configs:
        return []

    from app.repositories.knowledge import KnowledgeRepository

    repo = KnowledgeRepository(session)
    resolved: list[dict] = []

    for cfg in kb_configs:
        kb_id_str: str = cfg.get("knowledgeBaseId", "")
        try:
            kb_uuid = uuid.UUID(kb_id_str)
        except (ValueError, AttributeError):
            _log.warning("agent node: invalid KB UUID '%s', skipping", kb_id_str)
            continue

        kb = await repo.get_kb(kb_uuid)
        if kb is None:
            _log.warning("agent node: KB '%s' not found, skipping", kb_id_str)
            continue

        resolved.append({
            "name": kb.name,
            "collection": kb.qdrant_collection,
            "emb_provider": kb.embedding_provider,
            "emb_model": kb.embedding_model,
            "top_k": int(cfg.get("topK", 5)),
            "score_threshold": float(cfg.get("scoreThreshold", 0.0)),
        })

    return resolved


def _build_kb_tools(resolved_kbs: list[dict]) -> list[Any]:
    """Build LangChain StructuredTools from pre-resolved KB metadata.

    Called at runtime — no DB session needed since all metadata was
    resolved at compile time by _resolve_kb_metadata().
    """
    if not resolved_kbs:
        return []

    from langchain_core.tools import StructuredTool
    from pydantic import BaseModel, Field

    from app.nodes.knowledge_base import search_knowledge_base

    tools: list[Any] = []

    for kb_meta in resolved_kbs:
        _collection = kb_meta["collection"]
        _emb_provider = kb_meta["emb_provider"]
        _emb_model = kb_meta["emb_model"]
        _top_k = kb_meta["top_k"]
        _threshold = kb_meta["score_threshold"] if kb_meta["score_threshold"] > 0.0 else None
        _kb_name = kb_meta["name"]

        class KBSearchArgs(BaseModel):
            query: str = Field(description="검색할 질문이나 키워드")

        async def _search_kb(
            query: str,
            collection: str = _collection,
            emb_provider: str = _emb_provider,
            emb_model: str = _emb_model,
            tk: int = _top_k,
            thresh: float | None = _threshold,
        ) -> str:
            chunks = await search_knowledge_base(
                query=query,
                collection_name=collection,
                embedding_provider_name=emb_provider,
                embedding_model=emb_model,
                top_k=tk,
                score_threshold=thresh,
            )
            if not chunks:
                return "검색 결과가 없습니다."
            return "\n\n---\n\n".join(chunks)

        safe_name = "".join(c if c.isalnum() or c == "_" else "_" for c in _kb_name)
        tool_name = f"search_kb_{safe_name}"

        lc_tool = StructuredTool.from_function(
            coroutine=_search_kb,
            name=tool_name,
            description=f"'{_kb_name}' 지식베이스에서 관련 정보를 검색합니다. 질문이나 키워드를 입력하면 관련 문서 내용을 반환합니다.",
            args_schema=KBSearchArgs,
        )
        tools.append(lc_tool)
        _log.info("agent node: loaded KB tool '%s' (collection=%s)", tool_name, _collection)

    return tools


async def make_agent_node(
    node_id: str,
    node_data: dict,
    session: AsyncSession,
    predecessor_ids: list[str] | None = None,
) -> Callable[[WorkflowState], dict]:
    """Factory that creates an Agent node callable.

    Builds a LangGraph ReAct agent backed by the configured chat model and
    optional MCP tools and KB tools, then invokes it with the current input.

    KB metadata is resolved at compile time (while the DB session is
    available) to avoid session conflicts at runtime.

    Args:
        node_id: Unique identifier of this node in the workflow graph.
        node_data: Frontend node configuration:
            - provider (str): "openai" | "anthropic" | "vllm"
            - model (str): Model identifier.
            - instruction (str): System prompt for the agent.
            - maxIterations (int): Max ReAct cycles (default 5).
            - tools (list[str]): MCP tool names to make available.
            - knowledgeBases (list[dict]): KB configs with knowledgeBaseId, topK, scoreThreshold.
        session: Active async DB session.

    Returns:
        Async callable compatible with LangGraph's StateGraph.add_node().
    """
    provider: str = node_data.get("provider", "openai")
    model_name: str = node_data.get("model", "gpt-4o")
    instruction: str = node_data.get("instruction", "") or ""
    max_iterations: int = int(node_data.get("maxIterations", 5))
    tool_names: list[str] = node_data.get("tools", []) or []
    kb_configs: list[dict] = node_data.get("knowledgeBases", []) or []

    _predecessors = predecessor_ids

    # Resolve all DB-dependent config at compile time
    resolved_kbs = await _resolve_kb_metadata(kb_configs, session)
    credentials = await resolve_provider_credentials(provider, session)

    async def agent_node(state: WorkflowState) -> dict:
        from langgraph.prebuilt import create_react_agent

        input_text = get_input_text(state, node_id, predecessor_ids=_predecessors)
        _log.debug(
            "agent [%s]: provider=%s model=%s tools=%s kb_count=%d input_len=%d",
            node_id, provider, model_name, tool_names, len(resolved_kbs), len(input_text),
        )

        chat_model = make_chat_model_sync(
            provider=provider,
            model=model_name,
            credentials=credentials,
            temperature=0.7,
            streaming=False,
        )

        mcp_adapters: list[Any] = []
        try:
            if tool_names:
                mcp_tools, mcp_adapters = await _load_mcp_tools(tool_names, session)
            else:
                mcp_tools = []

            # Build KB tools from pre-resolved metadata (no DB access needed)
            kb_tools = _build_kb_tools(resolved_kbs)
            tools = mcp_tools + kb_tools

            agent_kwargs: dict[str, Any] = {
                "model": chat_model,
                "tools": tools,
            }
            if instruction:
                agent_kwargs["prompt"] = instruction

            react_agent = create_react_agent(**agent_kwargs)

            # recursion_limit accounts for tool-call + tool-response pairs plus final answer
            recursion_limit = max_iterations * 2 + 1
            result = await react_agent.ainvoke(
                {"messages": [{"role": "user", "content": input_text}]},
                config={"recursion_limit": recursion_limit},
            )

            # Extract last AI message content
            agent_messages = result.get("messages", [])
            output: str = ""
            if agent_messages:
                last_msg = agent_messages[-1]
                output = last_msg.content if hasattr(last_msg, "content") else str(last_msg)

            _log.debug("agent [%s]: output_len=%d", node_id, len(output))
            return {
                "node_outputs": {node_id: output},
                "messages": [{"role": "assistant", "content": output}],
            }
        finally:
            await _close_adapters(mcp_adapters)

    agent_node.__name__ = f"agent_{node_id}"
    return agent_node
