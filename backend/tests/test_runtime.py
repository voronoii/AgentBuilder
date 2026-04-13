"""Unit tests for WorkflowRuntime._map_event (pure function, no DB/async needed).

All tests call _map_event directly with hand-crafted raw event dicts and
assert on the returned internal event schema.
"""
from __future__ import annotations

import pytest

from app.services.workflow.runtime import _map_event


# ---------------------------------------------------------------------------
# Helper — minimal chunk with a .content attribute
# ---------------------------------------------------------------------------


class _FakeChunk:
    def __init__(self, content: str = "") -> None:
        self.content = content


# ---------------------------------------------------------------------------
# on_chat_model_stream → llm_token
# ---------------------------------------------------------------------------


def test_map_event_chat_model_stream_returns_llm_token() -> None:
    chunk = _FakeChunk("Hello")
    raw = {
        "event": "on_chat_model_stream",
        "name": "ChatOpenAI",
        "data": {"chunk": chunk},
        "metadata": {"langgraph_node": "llm1"},
    }
    result = _map_event(raw)
    assert result is not None
    assert result["event_type"] == "llm_token"
    assert result["payload"]["token"] == "Hello"
    assert result["node_id"] == "llm1"


def test_map_event_chat_model_stream_empty_chunk() -> None:
    chunk = _FakeChunk("")
    raw = {
        "event": "on_chat_model_stream",
        "name": "ChatOpenAI",
        "data": {"chunk": chunk},
        "metadata": {},
    }
    result = _map_event(raw)
    assert result is not None
    assert result["event_type"] == "llm_token"
    assert result["payload"]["token"] == ""


def test_map_event_chat_model_stream_no_chunk() -> None:
    raw = {
        "event": "on_chat_model_stream",
        "name": "ChatOpenAI",
        "data": {},
        "metadata": {},
    }
    result = _map_event(raw)
    assert result is not None
    assert result["event_type"] == "llm_token"
    assert result["payload"]["token"] == ""


# ---------------------------------------------------------------------------
# on_chain_start → node_start
# ---------------------------------------------------------------------------


def test_map_event_chain_start_returns_node_start() -> None:
    raw = {
        "event": "on_chain_start",
        "name": "llm_node",
        "data": {},
        "metadata": {"langgraph_node": "llm1"},
    }
    result = _map_event(raw)
    assert result is not None
    assert result["event_type"] == "node_start"
    assert result["node_id"] == "llm1"
    assert result["payload"]["node_name"] == "llm_node"


def test_map_event_chain_start_without_node_id_is_ignored() -> None:
    """on_chain_start at graph level (no langgraph_node) should be ignored."""
    raw = {
        "event": "on_chain_start",
        "name": "LangGraph",
        "data": {},
        "metadata": {},  # no langgraph_node
    }
    result = _map_event(raw)
    # node_id is None → the condition `if event_name == "on_chain_start" and node_id`
    # is False, falls through to the bottom None return.
    assert result is None


# ---------------------------------------------------------------------------
# on_chain_end → node_end (or workflow_end)
# ---------------------------------------------------------------------------


def test_map_event_chain_end_with_node_id_returns_node_end() -> None:
    raw = {
        "event": "on_chain_end",
        "name": "llm_node",
        "data": {"output": {"final_output": "Great answer"}},
        "metadata": {"langgraph_node": "llm1"},
    }
    result = _map_event(raw)
    assert result is not None
    assert result["event_type"] == "node_end"
    assert result["node_id"] == "llm1"
    assert result["payload"]["output"] == "Great answer"


def test_map_event_chain_end_without_node_id_returns_workflow_end() -> None:
    """on_chain_end at graph level (no langgraph_node) → workflow_end."""
    raw = {
        "event": "on_chain_end",
        "name": "LangGraph",
        "data": {"output": {"final_output": "Done"}},
        "metadata": {},
    }
    result = _map_event(raw)
    assert result is not None
    assert result["event_type"] == "workflow_end"
    assert result["node_id"] is None
    assert result["payload"]["output"] == "Done"


def test_map_event_chain_end_non_dict_output() -> None:
    """When output is not a dict, final_output defaults to empty string."""
    raw = {
        "event": "on_chain_end",
        "name": "llm_node",
        "data": {"output": "plain string"},
        "metadata": {"langgraph_node": "llm1"},
    }
    result = _map_event(raw)
    assert result is not None
    assert result["event_type"] == "node_end"
    assert result["payload"]["output"] == ""


# ---------------------------------------------------------------------------
# on_tool_start → tool_call
# ---------------------------------------------------------------------------


def test_map_event_tool_start_returns_tool_call() -> None:
    raw = {
        "event": "on_tool_start",
        "name": "search_tool",
        "data": {"input": {"query": "test"}},
        "metadata": {"langgraph_node": "agent1"},
    }
    result = _map_event(raw)
    assert result is not None
    assert result["event_type"] == "tool_call"
    assert result["node_id"] == "agent1"
    assert result["payload"]["tool_name"] == "search_tool"
    assert result["payload"]["input"] == {"query": "test"}


# ---------------------------------------------------------------------------
# on_tool_end → tool_result
# ---------------------------------------------------------------------------


def test_map_event_tool_end_returns_tool_result() -> None:
    raw = {
        "event": "on_tool_end",
        "name": "search_tool",
        "data": {"output": "found results"},
        "metadata": {"langgraph_node": "agent1"},
    }
    result = _map_event(raw)
    assert result is not None
    assert result["event_type"] == "tool_result"
    assert result["node_id"] == "agent1"
    assert result["payload"]["tool_name"] == "search_tool"
    assert result["payload"]["output"] == "found results"


def test_map_event_tool_end_non_string_output_is_stringified() -> None:
    raw = {
        "event": "on_tool_end",
        "name": "json_tool",
        "data": {"output": {"key": "value"}},
        "metadata": {},
    }
    result = _map_event(raw)
    assert result is not None
    assert result["event_type"] == "tool_result"
    # output is str() of the dict
    assert "key" in result["payload"]["output"]


# ---------------------------------------------------------------------------
# Unknown / ignored events
# ---------------------------------------------------------------------------


def test_map_event_unknown_event_returns_none() -> None:
    raw = {
        "event": "on_llm_start",
        "name": "OpenAI",
        "data": {},
        "metadata": {},
    }
    result = _map_event(raw)
    assert result is None


def test_map_event_on_chain_stream_is_ignored() -> None:
    raw = {
        "event": "on_chain_stream",
        "name": "something",
        "data": {"chunk": {}},
        "metadata": {"langgraph_node": "llm1"},
    }
    result = _map_event(raw)
    assert result is None


def test_map_event_completely_empty_dict_returns_none() -> None:
    result = _map_event({})
    assert result is None


def test_map_event_missing_fields_handled_gracefully() -> None:
    """Event dicts with missing keys should not raise KeyError."""
    raw = {"event": "on_tool_end"}  # no name, data, metadata
    result = _map_event(raw)
    assert result is not None
    assert result["event_type"] == "tool_result"
    assert result["payload"]["tool_name"] == ""
    assert result["payload"]["output"] == ""
