"""Unit tests for WorkflowValidator.

All tests operate on plain dicts — no DB or async I/O required.
"""
from __future__ import annotations

import pytest

from app.services.workflow.validator import ValidationError, WorkflowValidator


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _node(node_id: str, node_type: str, **data_extra) -> dict:
    """Build a minimal React Flow node dict."""
    return {"id": node_id, "data": {"type": node_type, **data_extra}}


def _edge(source: str, target: str) -> dict:
    return {"source": source, "target": target}


def _codes(errors: list[ValidationError]) -> list[str]:
    return [e.code for e in errors]


@pytest.fixture
def validator() -> WorkflowValidator:
    return WorkflowValidator()


# ---------------------------------------------------------------------------
# I/O node checks
# ---------------------------------------------------------------------------


def test_missing_chat_input_raises_error(validator: WorkflowValidator) -> None:
    nodes = [_node("out1", "chat_output")]
    edges: list[dict] = []
    errors = validator.validate(nodes, edges)
    assert "MISSING_CHAT_INPUT" in _codes(errors)


def test_missing_chat_output_raises_error(validator: WorkflowValidator) -> None:
    nodes = [_node("in1", "chat_input")]
    edges: list[dict] = []
    errors = validator.validate(nodes, edges)
    assert "MISSING_CHAT_OUTPUT" in _codes(errors)


def test_multiple_chat_input_nodes_raises_error(validator: WorkflowValidator) -> None:
    nodes = [
        _node("in1", "chat_input"),
        _node("in2", "chat_input"),
        _node("out1", "chat_output"),
    ]
    edges = [_edge("in1", "out1"), _edge("in2", "out1")]
    errors = validator.validate(nodes, edges)
    assert "MULTIPLE_CHAT_INPUT" in _codes(errors)


def test_multiple_chat_output_nodes_raises_error(validator: WorkflowValidator) -> None:
    nodes = [
        _node("in1", "chat_input"),
        _node("out1", "chat_output"),
        _node("out2", "chat_output"),
    ]
    edges = [_edge("in1", "out1"), _edge("in1", "out2")]
    errors = validator.validate(nodes, edges)
    assert "MULTIPLE_CHAT_OUTPUT" in _codes(errors)


# ---------------------------------------------------------------------------
# Isolated node check
# ---------------------------------------------------------------------------


def test_isolated_node_produces_error(validator: WorkflowValidator) -> None:
    nodes = [
        _node("in1", "chat_input"),
        _node("llm1", "llm", provider="openai", model="gpt-4o"),
        _node("out1", "chat_output"),
        _node("orphan", "llm", provider="openai", model="gpt-4o"),  # no edges
    ]
    edges = [_edge("in1", "llm1"), _edge("llm1", "out1")]
    errors = validator.validate(nodes, edges)
    codes = _codes(errors)
    assert "ISOLATED_NODE" in codes
    # Confirm it's specifically the orphan node
    isolated = [e for e in errors if e.code == "ISOLATED_NODE"]
    assert isolated[0].node_id == "orphan"


# ---------------------------------------------------------------------------
# Cycle detection
# ---------------------------------------------------------------------------


def test_cycle_detection_raises_error(validator: WorkflowValidator) -> None:
    # in1 → llm1 → llm2 → llm1 (cycle between llm1 and llm2)
    nodes = [
        _node("in1", "chat_input"),
        _node("llm1", "llm", provider="openai", model="gpt-4o"),
        _node("llm2", "llm", provider="openai", model="gpt-4o"),
        _node("out1", "chat_output"),
    ]
    edges = [
        _edge("in1", "llm1"),
        _edge("llm1", "llm2"),
        _edge("llm2", "llm1"),  # creates cycle
        _edge("llm2", "out1"),
    ]
    errors = validator.validate(nodes, edges)
    assert "CYCLE_DETECTED" in _codes(errors)


# ---------------------------------------------------------------------------
# Valid workflows
# ---------------------------------------------------------------------------


def test_valid_simple_workflow_has_no_errors(validator: WorkflowValidator) -> None:
    nodes = [
        _node("in1", "chat_input"),
        _node("llm1", "llm", provider="openai", model="gpt-4o"),
        _node("out1", "chat_output"),
    ]
    edges = [_edge("in1", "llm1"), _edge("llm1", "out1")]
    errors = validator.validate(nodes, edges)
    assert errors == []


def test_valid_complex_workflow_with_multiple_paths(validator: WorkflowValidator) -> None:
    # in1 → llm1 → pt1 → out1
    #      ↘ llm2 ↗
    nodes = [
        _node("in1", "chat_input"),
        _node("llm1", "llm", provider="openai", model="gpt-4o"),
        _node("llm2", "llm", provider="openai", model="gpt-4o"),
        _node("pt1", "prompt_template", template="Summarize: {input}"),
        _node("out1", "chat_output"),
    ]
    edges = [
        _edge("in1", "llm1"),
        _edge("in1", "llm2"),
        _edge("llm1", "pt1"),
        _edge("llm2", "pt1"),
        _edge("pt1", "out1"),
    ]
    errors = validator.validate(nodes, edges)
    assert errors == []


# ---------------------------------------------------------------------------
# Required fields
# ---------------------------------------------------------------------------


def test_llm_missing_provider_produces_error(validator: WorkflowValidator) -> None:
    nodes = [
        _node("in1", "chat_input"),
        _node("llm1", "llm", model="gpt-4o"),  # provider missing
        _node("out1", "chat_output"),
    ]
    edges = [_edge("in1", "llm1"), _edge("llm1", "out1")]
    errors = validator.validate(nodes, edges)
    missing = [e for e in errors if e.code == "MISSING_REQUIRED_FIELD"]
    assert any("provider" in e.message for e in missing)


def test_llm_missing_model_produces_error(validator: WorkflowValidator) -> None:
    nodes = [
        _node("in1", "chat_input"),
        _node("llm1", "llm", provider="openai"),  # model missing
        _node("out1", "chat_output"),
    ]
    edges = [_edge("in1", "llm1"), _edge("llm1", "out1")]
    errors = validator.validate(nodes, edges)
    missing = [e for e in errors if e.code == "MISSING_REQUIRED_FIELD"]
    assert any("model" in e.message for e in missing)


def test_knowledge_base_missing_id_produces_error(validator: WorkflowValidator) -> None:
    nodes = [
        _node("in1", "chat_input"),
        _node("kb1", "knowledge_base"),  # knowledgeBaseId missing
        _node("out1", "chat_output"),
    ]
    edges = [_edge("in1", "kb1"), _edge("kb1", "out1")]
    errors = validator.validate(nodes, edges)
    codes = _codes(errors)
    assert "MISSING_REQUIRED_FIELD" in codes


# ---------------------------------------------------------------------------
# Edge validity
# ---------------------------------------------------------------------------


def test_edge_with_nonexistent_source_raises_error(validator: WorkflowValidator) -> None:
    nodes = [
        _node("in1", "chat_input"),
        _node("out1", "chat_output"),
    ]
    edges = [_edge("ghost_node", "out1")]
    errors = validator.validate(nodes, edges)
    assert "INVALID_EDGE_SOURCE" in _codes(errors)


def test_edge_with_nonexistent_target_raises_error(validator: WorkflowValidator) -> None:
    nodes = [
        _node("in1", "chat_input"),
        _node("out1", "chat_output"),
    ]
    edges = [_edge("in1", "nowhere")]
    errors = validator.validate(nodes, edges)
    assert "INVALID_EDGE_TARGET" in _codes(errors)


# ---------------------------------------------------------------------------
# ChatInput→ChatOutput path
# ---------------------------------------------------------------------------


def test_no_path_from_input_to_output_raises_error(validator: WorkflowValidator) -> None:
    # in1 → llm1  (dead end)   out1 (isolated, no incoming from llm1)
    nodes = [
        _node("in1", "chat_input"),
        _node("llm1", "llm", provider="openai", model="gpt-4o"),
        _node("out1", "chat_output"),
    ]
    # llm1 → out1 edge is missing; llm1 connects nowhere useful, out1 has no incoming
    edges = [_edge("in1", "llm1"), _edge("out1", "in1")]  # out1→in1 doesn't help
    errors = validator.validate(nodes, edges)
    assert "NO_INPUT_OUTPUT_PATH" in _codes(errors)


def test_direct_input_to_output_path_passes_path_check(validator: WorkflowValidator) -> None:
    # Minimal: in1 directly to out1 — path check should pass.
    # (Other checks like ISOLATED nodes etc. won't fire because both nodes are connected.)
    nodes = [
        _node("in1", "chat_input"),
        _node("out1", "chat_output"),
    ]
    edges = [_edge("in1", "out1")]
    errors = validator.validate(nodes, edges)
    # Path check itself should not fire
    assert "NO_INPUT_OUTPUT_PATH" not in _codes(errors)
