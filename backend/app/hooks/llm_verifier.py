"""Hook: use a separate LLM to judge the agent output against criteria."""

from __future__ import annotations

import logging
from typing import Any

from app.hooks.protocol import AgentHook, HookContext, HookVerdict
from app.services.workflow.state import WorkflowState

_log = logging.getLogger(__name__)

_VERIFIER_SYSTEM_PROMPT = (
    "당신은 AI 응답 검증자입니다. 아래 기준에 따라 응답을 검증하세요.\n\n"
    "검증 기준:\n{criteria}\n\n"
    "반드시 아래 형식으로만 답하세요:\n"
    "PASS: <통과 이유>\n"
    "또는\n"
    "FAIL: <실패 이유 및 구체적 수정 안내>"
)


class LLMVerifierHook:
    """Invoke a separate LLM to judge output quality."""

    hook_type = "llm_verifier"

    def __init__(
        self,
        *,
        criteria: str,
        provider: str,
        model: str,
        credentials: dict[str, str] | None = None,
        max_retries: int = 1,
        on_exhausted: str = "error",
        timeout_ms: int = 60_000,
        retry_strategy: str = "accumulate",
        fallback_message: str = "",
    ) -> None:
        self.criteria = criteria
        self.provider = provider
        self.model = model
        self.credentials = credentials or {}
        self.max_retries = max_retries
        self.on_exhausted = on_exhausted
        self.timeout_ms = timeout_ms
        self.retry_strategy = retry_strategy
        self.fallback_message = fallback_message

    async def verify(
        self,
        output: str,
        messages: list[Any],
        state: WorkflowState,
        ctx: HookContext,
    ) -> HookVerdict:
        from langchain_core.messages import HumanMessage, SystemMessage

        from app.services.providers.chat.registry import (
            make_chat_model_sync,
            resolve_provider_credentials,
        )

        # Resolve credentials if not provided at construction
        creds = self.credentials
        if not creds:
            creds = await resolve_provider_credentials(self.provider, ctx.session)

        verifier_model = make_chat_model_sync(
            provider=self.provider,
            model=self.model,
            credentials=creds,
            temperature=0.0,
            streaming=False,
        )

        result = await verifier_model.ainvoke([
            SystemMessage(content=_VERIFIER_SYSTEM_PROMPT.format(criteria=self.criteria)),
            HumanMessage(content=f"검증 대상 응답:\n{output}"),
        ])

        text = result.content.strip()
        passed = text.upper().startswith("PASS")
        feedback: str | None = None
        if ":" in text:
            feedback = text.split(":", 1)[1].strip()

        usage = getattr(result, "usage_metadata", None) or {}
        input_tokens = usage.get("input_tokens", 0)
        output_tokens = usage.get("output_tokens", 0)

        return HookVerdict(
            passed=passed,
            feedback=feedback if not passed else None,
            details={
                "input_tokens": input_tokens,
                "output_tokens": output_tokens,
                "raw_verdict": text[:200],
            },
        )
