"""Demo seed workflows for AgentBuilder.

Each entry is a dict that matches the WorkflowCreate schema:
  - name: str
  - description: str
  - nodes: list of ReactFlowNode-compatible dicts
  - edges: list of ReactFlowEdge-compatible dicts

Node `data` dict carries the node-type-specific config payload.
The `type` field on the node (React Flow node type) mirrors `data.type`
so the frontend renderer can pick the correct component.
"""

from __future__ import annotations

from typing import Any

# ---------------------------------------------------------------------------
# Demo 1: Simple Q&A Chatbot
# ChatInput → LLM → ChatOutput
# ---------------------------------------------------------------------------

_QA_CHATBOT_NODES: list[dict[str, Any]] = [
    {
        "id": "chat_input_1",
        "type": "chat_input",
        "position": {"x": 100, "y": 200},
        "data": {
            "type": "chat_input",
            "label": "Chat Input",
        },
    },
    {
        "id": "llm_1",
        "type": "llm",
        "position": {"x": 400, "y": 200},
        "data": {
            "type": "llm",
            "label": "LLM",
            "provider": "openrouter",
            "model": "meta-llama/llama-4-scout:free",
            "system_message": "당신은 친절하고 도움이 되는 AI 어시스턴트입니다.",
            "temperature": 0.7,
            "max_tokens": 1024,
        },
    },
    {
        "id": "chat_output_1",
        "type": "chat_output",
        "position": {"x": 700, "y": 200},
        "data": {
            "type": "chat_output",
            "label": "Chat Output",
        },
    },
]

_QA_CHATBOT_EDGES: list[dict[str, Any]] = [
    {
        "id": "e1",
        "source": "chat_input_1",
        "target": "llm_1",
        "sourceHandle": None,
        "targetHandle": None,
    },
    {
        "id": "e2",
        "source": "llm_1",
        "target": "chat_output_1",
        "sourceHandle": None,
        "targetHandle": None,
    },
]

DEMO_QA_CHATBOT: dict[str, Any] = {
    "name": "간단한 Q&A 챗봇",
    "description": "기본적인 질의응답 챗봇입니다. ChatInput → LLM → ChatOutput 구조.",
    "nodes": _QA_CHATBOT_NODES,
    "edges": _QA_CHATBOT_EDGES,
}


# ---------------------------------------------------------------------------
# Demo 2: RAG Knowledge Chatbot
# ChatInput → KnowledgeBase → PromptTemplate → LLM → ChatOutput
# ---------------------------------------------------------------------------

_RAG_CHATBOT_NODES: list[dict[str, Any]] = [
    {
        "id": "chat_input_1",
        "type": "chat_input",
        "position": {"x": 100, "y": 200},
        "data": {
            "type": "chat_input",
            "label": "Chat Input",
        },
    },
    {
        "id": "knowledge_base_1",
        "type": "knowledge_base",
        "position": {"x": 350, "y": 200},
        "data": {
            "type": "knowledge_base",
            "label": "Knowledge Base",
            # knowledgeBaseId must be configured by the user after import
            "knowledgeBaseId": None,
            "topK": 3,
        },
    },
    {
        "id": "prompt_template_1",
        "type": "prompt_template",
        "position": {"x": 600, "y": 200},
        "data": {
            "type": "prompt_template",
            "label": "Prompt Template",
            "template": (
                "다음 참고 자료를 바탕으로 질문에 답변해주세요.\n\n"
                "참고 자료:\n{{context}}\n\n"
                "질문: {{query}}"
            ),
        },
    },
    {
        "id": "llm_1",
        "type": "llm",
        "position": {"x": 850, "y": 200},
        "data": {
            "type": "llm",
            "label": "LLM",
            "provider": "openrouter",
            "model": "meta-llama/llama-4-scout:free",
            "temperature": 0.3,
            "max_tokens": 2048,
        },
    },
    {
        "id": "chat_output_1",
        "type": "chat_output",
        "position": {"x": 1100, "y": 200},
        "data": {
            "type": "chat_output",
            "label": "Chat Output",
        },
    },
]

_RAG_CHATBOT_EDGES: list[dict[str, Any]] = [
    {
        "id": "e1",
        "source": "chat_input_1",
        "target": "knowledge_base_1",
        "sourceHandle": None,
        "targetHandle": None,
    },
    {
        "id": "e2",
        "source": "knowledge_base_1",
        "target": "prompt_template_1",
        "sourceHandle": None,
        "targetHandle": None,
    },
    {
        "id": "e3",
        "source": "prompt_template_1",
        "target": "llm_1",
        "sourceHandle": None,
        "targetHandle": None,
    },
    {
        "id": "e4",
        "source": "llm_1",
        "target": "chat_output_1",
        "sourceHandle": None,
        "targetHandle": None,
    },
]

DEMO_RAG_CHATBOT: dict[str, Any] = {
    "name": "RAG 지식 챗봇",
    "description": (
        "지식베이스를 활용하는 RAG 챗봇입니다. "
        "ChatInput → KnowledgeBase → PromptTemplate → LLM → ChatOutput 구조."
    ),
    "nodes": _RAG_CHATBOT_NODES,
    "edges": _RAG_CHATBOT_EDGES,
}


# ---------------------------------------------------------------------------
# Public list — used by the seed endpoint
# ---------------------------------------------------------------------------

ALL_DEMOS: list[dict[str, Any]] = [
    DEMO_QA_CHATBOT,
    DEMO_RAG_CHATBOT,
]
