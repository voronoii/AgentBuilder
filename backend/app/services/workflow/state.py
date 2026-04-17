"""Shared WorkflowState TypedDict used by the compiler and all node implementations.

Defined here to avoid circular imports between app.services.workflow.compiler
and app.nodes.*.
"""
from __future__ import annotations

import operator
from typing import Annotated, TypedDict


def _merge_dicts(a: dict, b: dict) -> dict:
    """Reducer that merges two dicts — safe for parallel node execution."""
    return {**a, **b}


class WorkflowState(TypedDict):
    """LangGraph state schema for MVP string-only inter-node data transfer.

    - user_input       : raw text from the ChatInput node.
    - messages         : accumulated HumanMessage / AIMessage objects for LLM context
                         (list with reducer that appends, so parallel branches are safe).
    - node_outputs     : mapping of node_id → last string output of that node.
                         Uses _merge_dicts reducer so parallel branches are safe.
    - final_output     : populated by the node immediately before ChatOutput; the
                         ChatOutput node copies this to the SSE stream.
    - guardrail_blocked: set to True by guardrail nodes when input is rejected.
                         Used by compiler conditional edges to route to END,
                         skipping all downstream processing nodes.
    """

    user_input: str
    messages: Annotated[list, operator.add]
    node_outputs: Annotated[dict, _merge_dicts]  # {node_id: str}
    final_output: str
    guardrail_blocked: bool
