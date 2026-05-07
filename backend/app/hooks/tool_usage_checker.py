"""Hook: verify that the agent used (or avoided) specific tools."""

from __future__ import annotations

import logging
from typing import Any

from app.hooks.protocol import AgentHook, HookContext, HookVerdict
from app.services.workflow.state import WorkflowState

_log = logging.getLogger(__name__)


class ToolUsageCheckerHook:
    """Check ToolMessage history for required / forbidden tool usage."""

    hook_type = "tool_usage_checker"

    def __init__(
        self,
        *,
        required: list[str] | None = None,
        forbidden: list[str] | None = None,
        max_retries: int = 1,
        on_exhausted: str = "error",
        timeout_ms: int = 5_000,
        retry_strategy: str = "accumulate",
        fallback_message: str = "",
    ) -> None:
        self.required = required or []
        self.forbidden = forbidden or []
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
        from langchain_core.messages import ToolMessage

        used_tools = {m.name for m in messages if isinstance(m, ToolMessage)}

        missing = set(self.required) - used_tools
        if missing:
            return HookVerdict(
                passed=False,
                feedback=f"다음 도구를 반드시 사용하세요: {', '.join(sorted(missing))}",
                details={"missing_tools": sorted(missing), "used_tools": sorted(used_tools)},
            )

        violated = set(self.forbidden) & used_tools
        if violated:
            return HookVerdict(
                passed=False,
                feedback=f"다음 도구를 사용하지 마세요: {', '.join(sorted(violated))}. 다른 방법으로 답변하세요.",
                details={"forbidden_used": sorted(violated)},
            )

        return HookVerdict(passed=True, details={"used_tools": sorted(used_tools)})
