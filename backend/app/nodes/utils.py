"""Shared utility functions used by workflow nodes."""

from __future__ import annotations

from app.services.workflow.state import WorkflowState


def get_input_text(
    state: WorkflowState,
    node_id: str | None = None,
    predecessor_ids: list[str] | None = None,
) -> str:
    """Get input text for a node from predecessor outputs.

    When predecessor_ids is provided (from compiler edge analysis), reads
    outputs from those specific nodes. Otherwise falls back to the last
    value in node_outputs or user_input.

    Args:
        state: Current workflow state.
        node_id: The calling node's own ID (for logging/debugging).
        predecessor_ids: Ordered list of upstream node IDs whose outputs
                         to collect. Provided by the compiler at build time.

    Returns:
        String input for the node to process.
    """
    outputs = state.get("node_outputs", {})

    if predecessor_ids:
        parts = [outputs[pid] for pid in predecessor_ids if pid in outputs]
        if parts:
            return "\n\n".join(parts)

    # Fallback: last-inserted value (linear graph) or user_input
    if outputs:
        return list(outputs.values())[-1]
    return state.get("user_input", "")
