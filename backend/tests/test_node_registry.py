"""Unit tests for app.nodes.registry.create_node_function.

Heavy node types (llm, agent, knowledge_base) are mocked at the module level
so these tests run without credentials or DB state.
"""
from __future__ import annotations

from collections.abc import Callable
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import AppError, ErrorCode
from app.nodes.registry import create_node_function
from app.services.workflow.state import WorkflowState


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _mock_session() -> AsyncSession:
    return MagicMock(spec=AsyncSession)


def _base_state(**extra) -> WorkflowState:
    base: WorkflowState = {
        "user_input": "hello",
        "messages": [],
        "node_outputs": {},
        "final_output": "",
    }
    base.update(extra)  # type: ignore[typeddict-item]
    return base


# ---------------------------------------------------------------------------
# Known node types — should return a callable
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_create_node_function_chat_input_is_callable() -> None:
    fn = await create_node_function(
        node_id="in1",
        node_data={"type": "chat_input"},
        session=_mock_session(),
    )
    assert callable(fn)


@pytest.mark.asyncio
async def test_create_node_function_chat_output_is_callable() -> None:
    fn = await create_node_function(
        node_id="out1",
        node_data={"type": "chat_output"},
        session=_mock_session(),
    )
    assert callable(fn)


@pytest.mark.asyncio
async def test_create_node_function_llm_is_callable() -> None:
    async def _fake_make_llm_node(node_id, node_data, session, *, predecessor_ids=None):
        async def _fn(state): return {"node_outputs": {node_id: "ok"}}
        return _fn

    with patch("app.nodes.llm.make_llm_node", new=_fake_make_llm_node):
        fn = await create_node_function(
            node_id="llm1",
            node_data={"type": "llm", "provider": "openai", "model": "gpt-4o"},
            session=_mock_session(),
        )
    assert callable(fn)


@pytest.mark.asyncio
async def test_create_node_function_prompt_template_is_callable() -> None:
    # prompt_template is synchronous — no provider calls needed
    fn = await create_node_function(
        node_id="pt1",
        node_data={"type": "prompt_template", "template": "Hello {input}"},
        session=_mock_session(),
    )
    assert callable(fn)


# ---------------------------------------------------------------------------
# Unknown node type — should raise
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_create_node_function_unknown_type_raises_app_error() -> None:
    with pytest.raises(AppError) as exc_info:
        await create_node_function(
            node_id="x1",
            node_data={"type": "nonexistent_type"},
            session=_mock_session(),
        )
    assert exc_info.value.code == ErrorCode.COMPILATION_FAILED
    assert "nonexistent_type" in exc_info.value.detail


@pytest.mark.asyncio
async def test_create_node_function_empty_type_raises_app_error() -> None:
    with pytest.raises(AppError) as exc_info:
        await create_node_function(
            node_id="x2",
            node_data={},  # no "type" key
            session=_mock_session(),
        )
    assert exc_info.value.code == ErrorCode.COMPILATION_FAILED


# ---------------------------------------------------------------------------
# chat_input callable behaviour
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_chat_input_node_callable_returns_user_input_in_outputs() -> None:
    fn = await create_node_function(
        node_id="in1",
        node_data={"type": "chat_input"},
        session=_mock_session(),
    )
    state = _base_state(user_input="What is 2+2?")
    result = await fn(state)
    assert isinstance(result, dict)
    assert result["node_outputs"]["in1"] == "What is 2+2?"
    assert result["messages"] == [{"role": "user", "content": "What is 2+2?"}]


# ---------------------------------------------------------------------------
# chat_output callable behaviour
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_chat_output_node_callable_sets_final_output() -> None:
    fn = await create_node_function(
        node_id="out1",
        node_data={"type": "chat_output"},
        session=_mock_session(),
    )
    state = _base_state(node_outputs={"llm1": "The answer is 42."})
    result = await fn(state)
    assert isinstance(result, dict)
    assert result["final_output"] == "The answer is 42."


@pytest.mark.asyncio
async def test_chat_output_node_with_predecessor_ids_selects_correct_output() -> None:
    """When predecessor_ids is passed through node_data, the right output is selected."""
    # We exercise this by calling make_chat_output_node directly since
    # create_node_function delegates to it and predecessor_ids only comes from
    # the compiler-supplied argument (not node_data). We test the factory directly.
    from app.nodes.chat_output import make_chat_output_node

    fn = make_chat_output_node(
        "out1",
        {"type": "chat_output"},
        predecessor_ids=["llm1"],
    )
    state = _base_state(
        node_outputs={"llm1": "response from llm1", "llm2": "should be ignored"}
    )
    result = await fn(state)
    assert result["final_output"] == "response from llm1"
