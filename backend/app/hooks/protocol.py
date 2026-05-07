"""Core protocol and data types for the Agent Hook system."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any, Protocol, runtime_checkable
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.services.workflow.state import WorkflowState


@dataclass(frozen=True)
class HookVerdict:
    """Result of a single hook verification."""

    passed: bool
    feedback: str | None = None
    details: dict[str, Any] | None = None


@dataclass(frozen=True)
class HookContext:
    """Runtime context injected into every hook invocation."""

    run_id: UUID
    node_id: str
    workflow_owner_id: UUID
    session: AsyncSession
    stream_writer: Callable[[dict[str, Any]], None]


@runtime_checkable
class AgentHook(Protocol):
    """Protocol that all hook types must satisfy."""

    hook_type: str
    max_retries: int
    on_exhausted: str        # "pass" | "error" | "fallback_message"
    timeout_ms: int
    retry_strategy: str      # "accumulate" | "clean"
    fallback_message: str    # used when on_exhausted == "fallback_message"

    async def verify(
        self,
        output: str,
        messages: list[Any],
        state: WorkflowState,
        ctx: HookContext,
    ) -> HookVerdict: ...
