"""Node function registry — factory that maps UI node data to LangGraph
node callables.

Each returned callable has the signature::

    async def node_fn(state: WorkflowState) -> dict

The dict returned is merged into the WorkflowState by LangGraph.

Node implementations live in sibling modules (chat_input, chat_output, llm,
agent, knowledge_base, prompt_template).  Imports are deferred inside each
branch to keep startup cost low and avoid circular imports.
"""
from __future__ import annotations

import logging
from collections.abc import Callable
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import AppError, ErrorCode
from app.services.workflow.state import WorkflowState

_log = logging.getLogger(__name__)

NodeFunction = Callable[[WorkflowState], Any]

_SUPPORTED_TYPES = {
    "chat_input",
    "chat_output",
    "llm",
    "agent",
    "knowledge_base",
    "prompt_template",
}


async def create_node_function(
    node_id: str,
    node_data: dict,
    session: AsyncSession,
    predecessor_ids: list[str] | None = None,
) -> NodeFunction:
    """Factory: create and return a LangGraph-compatible async node function.

    Args:
        node_id:   The React Flow node ID (used as the LangGraph node name).
        node_data: The ``data`` sub-dict from the React Flow node object.
        session:   Active SQLAlchemy async session for DB / settings access.
        predecessor_ids: Ordered list of upstream node IDs (from compiler
                         edge analysis) for topology-aware input routing.

    Returns:
        An async callable ``f(state) -> dict`` suitable for
        ``StateGraph.add_node(node_id, f)``.

    Raises:
        AppError(COMPILATION_FAILED): If the node type is unknown or required
            factory is unavailable.
    """
    node_type = node_data.get("type", "")

    if node_type not in _SUPPORTED_TYPES:
        raise AppError(
            status_code=422,
            code=ErrorCode.COMPILATION_FAILED,
            detail=f"알 수 없는 노드 타입: '{node_type}' (node_id={node_id})",
        )

    _log.debug("create_node_function: node_id=%s type=%s", node_id, node_type)

    if node_type == "chat_input":
        from app.nodes.chat_input import make_chat_input_node  # noqa: PLC0415

        return make_chat_input_node(node_id, node_data)

    if node_type == "chat_output":
        from app.nodes.chat_output import make_chat_output_node  # noqa: PLC0415

        return make_chat_output_node(node_id, node_data)

    if node_type == "llm":
        from app.nodes.llm import make_llm_node  # noqa: PLC0415

        return await make_llm_node(node_id, node_data, session, predecessor_ids=predecessor_ids)

    if node_type == "agent":
        from app.nodes.agent import make_agent_node  # noqa: PLC0415

        return await make_agent_node(node_id, node_data, session, predecessor_ids=predecessor_ids)

    if node_type == "knowledge_base":
        from app.nodes.knowledge_base import make_knowledge_base_node  # noqa: PLC0415

        return await make_knowledge_base_node(node_id, node_data, session, predecessor_ids=predecessor_ids)

    if node_type == "prompt_template":
        from app.nodes.prompt_template import make_prompt_template_node  # noqa: PLC0415

        return make_prompt_template_node(node_id, node_data, predecessor_ids=predecessor_ids)

    # Should be unreachable after the guard above, but satisfies type checker.
    raise AppError(
        status_code=500,
        code=ErrorCode.INTERNAL_UNEXPECTED,
        detail=f"registry: unhandled node_type '{node_type}'",
    )
