"""ChatOutput node — collects predecessor outputs and sets final_output."""

from __future__ import annotations

import logging
from collections.abc import Callable

from app.services.workflow.state import WorkflowState

_log = logging.getLogger(__name__)


def make_chat_output_node(
    node_id: str,
    node_data: dict,  # noqa: ARG001
    predecessor_ids: list[str] | None = None,
) -> Callable[[WorkflowState], dict]:
    """Factory that creates a ChatOutput node callable.

    Gathers outputs from predecessor nodes (if specified) and concatenates
    them into final_output. When predecessor_ids is not given it falls back
    to the most recently written node_output value.

    Args:
        node_id: Unique identifier of this node in the workflow graph.
        node_data: Frontend node configuration (label, type — not used here).
        predecessor_ids: Ordered list of upstream node IDs whose outputs to
                         collect.  If None or empty, the last node_output is used.

    Returns:
        Async callable compatible with LangGraph's StateGraph.add_node().
    """
    _predecessor_ids: list[str] = predecessor_ids or []

    async def chat_output_node(state: WorkflowState) -> dict:
        outputs = state.get("node_outputs", {})

        if _predecessor_ids:
            result_parts = [outputs[pid] for pid in _predecessor_ids if pid in outputs]
            final = "\n".join(result_parts) if result_parts else ""
        else:
            # Fallback: take the most recently added output
            final = list(outputs.values())[-1] if outputs else ""

        _log.debug("chat_output [%s]: final_output length=%d", node_id, len(final))
        return {
            "final_output": final,
            "node_outputs": {node_id: final},
        }

    chat_output_node.__name__ = f"chat_output_{node_id}"
    return chat_output_node
