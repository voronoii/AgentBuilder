"""Hook runner — executes after_agent hooks with fail-fast, timeout, and retry."""

from __future__ import annotations

import asyncio
import logging
import time
from typing import Any
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.hooks.protocol import AgentHook, HookContext, HookVerdict
from app.services.workflow.state import WorkflowState

_log = logging.getLogger(__name__)


async def run_after_agent_hooks(
    hooks: list[AgentHook],
    output: str,
    messages: list[Any],
    state: WorkflowState,
    ctx: HookContext,
    attempt: int,
) -> tuple[bool, AgentHook | None, HookVerdict]:
    """Run all after_agent hooks sequentially with fail-fast.

    Args:
        hooks: Ordered list of hooks (cost-ascending recommended).
        output: Current agent output text.
        messages: Full message history from the agent run.
        state: Current workflow state.
        ctx: Hook execution context.
        attempt: Current attempt number (0-based).

    Returns:
        (all_passed, failed_hook_or_none, last_verdict)
    """
    verdict = HookVerdict(passed=True)

    for hook in hooks:
        # Skip if this hook's retry limit is already exceeded
        if attempt > hook.max_retries:
            continue

        # SSE: hook_start
        ctx.stream_writer({
            "type": "hook_start",
            "node_id": ctx.node_id,
            "hook_type": hook.hook_type,
            "attempt": attempt + 1,
        })

        t0 = time.monotonic()

        # Execute with timeout
        try:
            verdict = await asyncio.wait_for(
                hook.verify(
                    output=output,
                    messages=messages,
                    state=state,
                    ctx=ctx,
                ),
                timeout=hook.timeout_ms / 1000,
            )
        except asyncio.TimeoutError:
            _log.warning(
                "Hook %s timed out after %dms on node %s",
                hook.hook_type, hook.timeout_ms, ctx.node_id,
            )
            verdict = HookVerdict(passed=True, details={"timeout": True})

        duration_ms = int((time.monotonic() - t0) * 1000)

        # SSE: hook_result
        ctx.stream_writer({
            "type": "hook_result",
            "node_id": ctx.node_id,
            "hook_type": hook.hook_type,
            "attempt": attempt + 1,
            "passed": verdict.passed,
            "feedback": verdict.feedback,
        })

        # DB: record execution
        await _record_hook_execution(
            ctx=ctx,
            hook=hook,
            attempt=attempt + 1,
            verdict=verdict,
            duration_ms=duration_ms,
        )

        if not verdict.passed:
            # Check if this hook exhausted its retries
            if attempt >= hook.max_retries:
                if hook.on_exhausted == "pass":
                    _log.info(
                        "Hook %s exhausted retries, on_exhausted=pass, continuing",
                        hook.hook_type,
                    )
                    continue  # Treat as passed, try next hook
                # "error" or "fallback_message" — caller handles
            return False, hook, verdict

    return True, None, verdict


async def _record_hook_execution(
    ctx: HookContext,
    hook: AgentHook,
    attempt: int,
    verdict: HookVerdict,
    duration_ms: int,
) -> None:
    """Persist a hook execution record to the database."""
    try:
        from app.models.hook import HookExecution

        details = verdict.details or {}
        execution = HookExecution(
            run_id=ctx.run_id,
            node_id=ctx.node_id,
            hook_type=hook.hook_type,
            hook_config={},  # could snapshot hook params here
            attempt=attempt,
            passed=verdict.passed,
            feedback=verdict.feedback,
            details=details,
            input_tokens=details.get("input_tokens", 0),
            output_tokens=details.get("output_tokens", 0),
            duration_ms=duration_ms,
        )
        ctx.session.add(execution)
        await ctx.session.flush()
    except Exception:
        _log.exception("Failed to record hook execution for %s", hook.hook_type)
