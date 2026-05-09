"""Shared WorkflowState TypedDict used by the compiler and all node implementations.

Defined here to avoid circular imports between app.services.workflow.compiler
and app.nodes.*.
"""
from __future__ import annotations

from typing import Annotated, TypedDict

from langgraph.graph.message import add_messages


def _merge_dicts(a: dict, b: dict) -> dict:
    """Reducer that merges two dicts — safe for parallel node execution."""
    return {**a, **b}


class WorkflowState(TypedDict):
    """LangGraph state schema for MVP string-only inter-node data transfer.

    - user_input       : raw text from the ChatInput node.
    - messages         : conversation history (HumanMessage / AIMessage / dict).
                         Uses LangGraph's ``add_messages`` reducer which dedupes
                         by id and normalises dicts into BaseMessage instances —
                         the canonical multi-turn pattern. The checkpointer
                         persists this list across turns when ``thread_id`` is
                         supplied via run config.
    - node_outputs     : mapping of node_id → last string output of that node.
                         Uses _merge_dicts reducer so parallel branches are safe.
    - final_output     : populated by the node immediately before ChatOutput; the
                         ChatOutput node copies this to the SSE stream.
    - guardrail_blocked: set to True by guardrail nodes when input is rejected.
                         Used by compiler conditional edges to route to END,
                         skipping all downstream processing nodes.
    """

    user_input: str
    messages: Annotated[list, add_messages]
    node_outputs: Annotated[dict, _merge_dicts]  # {node_id: str}
    final_output: str
    guardrail_blocked: bool
