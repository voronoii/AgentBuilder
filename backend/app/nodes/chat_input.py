"""ChatInput node — entry point that surfaces user_input into node_outputs."""

from __future__ import annotations

import logging
from collections.abc import Callable

from app.services.workflow.state import WorkflowState

_log = logging.getLogger(__name__)


def make_chat_input_node(
    node_id: str,
    node_data: dict,  # noqa: ARG001
) -> Callable[[WorkflowState], dict]:
    """Factory that creates a ChatInput node callable.

    The ChatInput node reads user_input from state and publishes it to
    node_outputs under its own node_id, making it available to downstream
    nodes that inspect node_outputs.

    Args:
        node_id: Unique identifier of this node in the workflow graph.
        node_data: Frontend node configuration (label, type — not used here).

    Returns:
        Async callable compatible with LangGraph's StateGraph.add_node().
    """

    async def chat_input_node(state: WorkflowState) -> dict:
        user_input = state.get("user_input", "")
        _log.debug("chat_input [%s]: forwarding %d chars", node_id, len(user_input))
        return {
            "node_outputs": {node_id: user_input},
            "messages": [{"role": "user", "content": user_input}],
        }

    chat_input_node.__name__ = f"chat_input_{node_id}"
    return chat_input_node
