"""PromptTemplate node — renders a Jinja2-style / {variable} template.

Takes the current user_input (and optionally predecessor node outputs) and
substitutes named variables in the template string.  The rendered string is
written to node_outputs and becomes the input for the next node.

Supported placeholder syntax: ``{variable_name}`` (Python str.format_map).
"""
from __future__ import annotations

import logging
import re
from collections.abc import Callable

from app.nodes.utils import get_input_text
from app.services.workflow.state import WorkflowState

_log = logging.getLogger(__name__)

# Matches {word} placeholders that are not doubled ({{ / }})
_PLACEHOLDER_RE = re.compile(r"(?<!\{)\{(\w+)\}(?!\})")


def make_prompt_template_node(
    node_id: str,
    node_data: dict,
    predecessor_ids: list[str] | None = None,
) -> Callable[[WorkflowState], dict]:
    """Factory that creates a PromptTemplate node callable.

    At run time the node builds a substitution mapping from:
      1. ``user_input`` — available as ``{user_input}``.
      2. All previous ``node_outputs`` — available by their node_id key.
      3. A fallback ``input`` alias pointing to the most recent predecessor output.

    Any placeholder that cannot be resolved is left as-is (no KeyError).

    Args:
        node_id: Unique identifier of this node in the workflow graph.
        node_data: Frontend node configuration:
            - template (str): Template string with ``{variable}`` placeholders.
            - variables (list[str]): Expected variable names (informational only).

    Returns:
        Async callable compatible with LangGraph's StateGraph.add_node().
    """
    template: str = node_data.get("template", "") or ""
    _predecessors = predecessor_ids

    async def prompt_template_node(state: WorkflowState) -> dict:
        predecessor_input = get_input_text(state, node_id, predecessor_ids=_predecessors)

        # Build substitution context
        sub_map: dict[str, str] = {
            "user_input": state.get("user_input", ""),
            "input": predecessor_input,
        }
        # Expose each prior node output by its node_id
        for prior_id, prior_val in state.get("node_outputs", {}).items():
            sub_map[prior_id] = str(prior_val)

        # Safe substitution: leave unresolved placeholders untouched
        rendered = _safe_format(template, sub_map)

        _log.debug(
            "prompt_template [%s]: rendered %d chars from template (%d chars)",
            node_id, len(rendered), len(template),
        )
        return {
            "node_outputs": {node_id: rendered},
        }

    prompt_template_node.__name__ = f"prompt_template_{node_id}"
    return prompt_template_node


def _safe_format(template: str, mapping: dict[str, str]) -> str:
    """Replace ``{key}`` placeholders using *mapping*, leaving unknowns intact."""

    def _replace(match: re.Match) -> str:  # type: ignore[type-arg]
        key = match.group(1)
        return mapping.get(key, match.group(0))  # fallback: keep original

    return _PLACEHOLDER_RE.sub(_replace, template)
