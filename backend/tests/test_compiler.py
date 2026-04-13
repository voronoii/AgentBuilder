"""Unit tests for WorkflowCompiler.

Uses the db_session fixture from conftest.py for the SQLAlchemy session.
create_node_function is mocked to return lightweight async lambdas so tests
run without any LLM provider credentials.
"""
from __future__ import annotations

from typing import Any
from unittest.mock import AsyncMock, patch

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import AppError, ErrorCode
from app.services.workflow.compiler import WorkflowCompiler


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _node(node_id: str, node_type: str, **data_extra) -> dict:
    return {"id": node_id, "data": {"type": node_type, **data_extra}}


def _edge(source: str, target: str) -> dict:
    return {"source": source, "target": target}


def _make_stub_node_fn(node_id: str):
    """Return a lightweight async callable that mimics a real node function."""

    async def _stub(state) -> dict:
        return {"node_outputs": {node_id: "test_output"}}

    _stub.__name__ = f"stub_{node_id}"
    return _stub


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def simple_workflow():
    """Minimal valid workflow: chat_input → llm1 → chat_output."""
    nodes = [
        _node("in1", "chat_input"),
        _node("llm1", "llm", provider="openai", model="gpt-4o"),
        _node("out1", "chat_output"),
    ]
    edges = [_edge("in1", "llm1"), _edge("llm1", "out1")]
    return nodes, edges


@pytest.fixture
def multi_sink_workflow():
    """Workflow with two parallel sink nodes: in1 → llm1, llm2 → out1.
    Both llm1 and llm2 feed out1 but only llm1 and llm2 are sinks to END
    (since out1 is the chat_output terminal, excluded from the processing set).
    """
    nodes = [
        _node("in1", "chat_input"),
        _node("llm1", "llm", provider="openai", model="gpt-4o"),
        _node("llm2", "llm", provider="openai", model="gpt-4o"),
        _node("out1", "chat_output"),
    ]
    edges = [
        _edge("in1", "llm1"),
        _edge("in1", "llm2"),
        _edge("llm1", "out1"),
        _edge("llm2", "out1"),
    ]
    return nodes, edges


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_valid_compilation_returns_compiled_graph(
    db_session: AsyncSession,
    simple_workflow,
) -> None:
    """Compiling a valid workflow should return a LangGraph CompiledGraph."""
    nodes, edges = simple_workflow
    with patch(
        "app.nodes.registry.create_node_function",
        new=AsyncMock(side_effect=lambda **kw: _make_stub_node_fn(kw["node_id"])),
    ):
        compiled = await WorkflowCompiler(db_session).compile(nodes, edges)

    # LangGraph compiled graphs have an `astream_events` method.
    assert hasattr(compiled, "astream_events") or hasattr(compiled, "invoke")


@pytest.mark.asyncio
async def test_invalid_workflow_raises_compilation_failed(
    db_session: AsyncSession,
) -> None:
    """A workflow missing ChatInput should raise AppError(COMPILATION_FAILED)."""
    nodes = [_node("out1", "chat_output")]
    edges: list[dict] = []
    with pytest.raises(AppError) as exc_info:
        await WorkflowCompiler(db_session).compile(nodes, edges)
    assert exc_info.value.code == ErrorCode.COMPILATION_FAILED


@pytest.mark.asyncio
async def test_validation_error_propagates_details(
    db_session: AsyncSession,
) -> None:
    """AppError.extra should contain the validation_errors list."""
    nodes = [_node("in1", "chat_input")]  # missing chat_output
    edges: list[dict] = []
    with pytest.raises(AppError) as exc_info:
        await WorkflowCompiler(db_session).compile(nodes, edges)
    extra = exc_info.value.extra
    assert "validation_errors" in extra
    assert len(extra["validation_errors"]) >= 1


@pytest.mark.asyncio
async def test_single_sink_connects_to_end(
    db_session: AsyncSession,
    simple_workflow,
) -> None:
    """_find_sink_nodes returns the last processing node when there is one path."""
    nodes, edges = simple_workflow
    compiler = WorkflowCompiler(db_session)
    node_map = {n["id"]: n for n in nodes}
    processing_ids = compiler._topological_sort(
        node_map=node_map,
        edges=edges,
        exclude={"in1", "out1"},
    )
    sink_ids = compiler._find_sink_nodes(processing_ids, edges, set(processing_ids))
    assert sink_ids == ["llm1"]


@pytest.mark.asyncio
async def test_multiple_sinks_all_connect_to_end(
    db_session: AsyncSession,
    multi_sink_workflow,
) -> None:
    """When two parallel branches have no outgoing processing edges, both are sinks."""
    nodes, edges = multi_sink_workflow
    compiler = WorkflowCompiler(db_session)
    node_map = {n["id"]: n for n in nodes}
    processing_ids = compiler._topological_sort(
        node_map=node_map,
        edges=edges,
        exclude={"in1", "out1"},
    )
    sink_ids = compiler._find_sink_nodes(processing_ids, edges, set(processing_ids))
    assert set(sink_ids) == {"llm1", "llm2"}


@pytest.mark.asyncio
async def test_passthrough_only_workflow_is_rejected(
    db_session: AsyncSession,
) -> None:
    """ChatInput→ChatOutput with no processing nodes must raise COMPILATION_FAILED."""
    nodes = [
        _node("in1", "chat_input"),
        _node("out1", "chat_output"),
    ]
    edges = [_edge("in1", "out1")]
    # Validation will pass (valid structure), but the compiler should raise because
    # there are no processing nodes.
    with pytest.raises(AppError) as exc_info:
        await WorkflowCompiler(db_session).compile(nodes, edges)
    assert exc_info.value.code == ErrorCode.COMPILATION_FAILED
    assert "처리 노드" in exc_info.value.detail
