"""LLM node — invokes a chat model and returns the response."""

from __future__ import annotations

import logging
from collections.abc import Callable
from typing import Any

from langchain_core.messages import HumanMessage, SystemMessage
from sqlalchemy.ext.asyncio import AsyncSession

from app.nodes.utils import get_input_text
from app.services.providers.chat.registry import make_chat_model_sync, resolve_provider_credentials
from app.services.workflow.state import WorkflowState

_log = logging.getLogger(__name__)


async def make_llm_node(
    node_id: str,
    node_data: dict,
    session: AsyncSession,
    predecessor_ids: list[str] | None = None,
) -> Callable[[WorkflowState], dict]:
    """Factory that creates an LLM node callable.

    Reads input from the most recent predecessor output, calls the configured
    chat model, and writes the response back to node_outputs.

    Args:
        node_id: Unique identifier of this node in the workflow graph.
        node_data: Frontend node configuration:
            - provider (str): "openai" | "anthropic" | "vllm"
            - model (str): Model identifier.
            - temperature (float): Sampling temperature (default 0.7).
            - maxTokens (int): Max tokens for the response (default 4096).
            - systemMessage (str): Optional system-level instruction.
        session: Active async DB session for API key resolution.
        predecessor_ids: Upstream node IDs for topology-aware input routing.

    Returns:
        Async callable compatible with LangGraph's StateGraph.add_node().
    """
    provider: str = node_data.get("provider", "openai")
    model_name: str = node_data.get("model", "gpt-4o")
    temperature: float = float(node_data.get("temperature", 0.7))
    max_tokens: int = int(node_data.get("maxTokens", 4096))
    system_message: str = node_data.get("systemMessage", "") or ""
    _predecessors = predecessor_ids

    # Resolve credentials at compile time (DB session is safe here)
    credentials = await resolve_provider_credentials(provider, session)

    async def llm_node(state: WorkflowState) -> dict:
        input_text = get_input_text(state, node_id, predecessor_ids=_predecessors)
        _log.debug(
            "llm [%s]: provider=%s model=%s input_len=%d",
            node_id, provider, model_name, len(input_text),
        )

        chat_model = make_chat_model_sync(
            provider=provider,
            model=model_name,
            credentials=credentials,
            temperature=temperature,
            streaming=False,
        )

        messages: list[Any] = []
        if system_message:
            messages.append(SystemMessage(content=system_message))
        messages.append(HumanMessage(content=input_text))

        response = await chat_model.ainvoke(messages, config={"max_tokens": max_tokens})
        output: str = response.content if hasattr(response, "content") else str(response)

        _log.debug("llm [%s]: output_len=%d", node_id, len(output))
        return {
            "node_outputs": {node_id: output},
            "messages": [{"role": "assistant", "content": output}],
        }

    llm_node.__name__ = f"llm_{node_id}"
    return llm_node
