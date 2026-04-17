"""Input Guardrail node — filters user input before it reaches LLM/Agent.

캔버스 배치: Chat Input → [Input Guardrail] → LLM / Agent

동작:
- 활성화된 체크를 순서대로 실행 (fail-fast: 첫 위반에서 중단)
- 통과 → 다음 노드로 원본 텍스트 전달
- 차단 → final_output에 거부 메시지 설정 후 워크플로우 조기 종료
        (분기 노드 구현 후 Pass/Fail 듀얼 출력으로 확장 예정)

node_data 필드:
    checks           (list[str])   활성 체크 목록. 예: ["pii", "injection", "jailbreak"]
    custom_rule      (str)         커스텀 가드레일 설명 (checks에 "custom" 포함 시)
    heuristic_threshold (float)    휴리스틱 임계값 (기본 0.7)
    provider         (str)         판정 LLM 프로바이더
    model            (str)         판정 LLM 모델명
    action           (str)         "block" | "warn" (현재는 block만 구현)
"""
from __future__ import annotations

import logging
from collections.abc import Callable

from langchain_core.language_models import BaseChatModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.nodes.utils import get_input_text
from app.services.guardrail.models import CheckResult, CheckType, GuardrailResult
from app.services.providers.chat.registry import make_chat_model_sync, resolve_provider_credentials
from app.services.workflow.state import WorkflowState

_log = logging.getLogger(__name__)

# Default check order — runs in this sequence (fail-fast stops at first hit)
_DEFAULT_CHECKS: list[str] = ["pii", "tokens", "jailbreak", "injection", "toxicity"]

# Denial prefix shown to end users when a check blocks the input
_BLOCK_PREFIX = "⚠️ 요청이 보안 정책에 의해 차단되었습니다."


async def make_input_guardrail_node(
    node_id: str,
    node_data: dict,
    session: AsyncSession,
    predecessor_ids: list[str] | None = None,
) -> Callable[[WorkflowState], dict]:
    """Factory: create an Input Guardrail LangGraph node.

    Credentials are resolved here (compile-time, DB session available).
    Runtime node function performs no DB access.
    """
    checks: list[str] = node_data.get("checks") or _DEFAULT_CHECKS
    custom_rule: str = node_data.get("custom_rule", "") or ""
    threshold: float = float(node_data.get("heuristic_threshold", 0.7))
    provider: str = node_data.get("provider", "openai")
    model_name: str = node_data.get("model", "gpt-4o-mini")

    credentials = await resolve_provider_credentials(provider, session)

    async def _run_checks(text: str, llm: BaseChatModel) -> GuardrailResult:
        """Execute enabled checks in order; stop on first failure."""
        results: list[CheckResult] = []

        for check_name in checks:
            result = await _dispatch(check_name, text, llm, threshold, custom_rule)
            results.append(result)
            if not result.passed:
                _log.info(
                    "input_guardrail [%s]: BLOCKED by %s (heuristic=%s)",
                    node_id, check_name, result.via_heuristic,
                )
                return GuardrailResult.fail(result.check_type, results)

        return GuardrailResult.ok(results)

    async def input_guardrail_node(state: WorkflowState) -> dict:
        input_text = get_input_text(state, node_id, predecessor_ids=predecessor_ids)

        if not input_text or not input_text.strip():
            _log.debug("input_guardrail [%s]: empty input, passing through", node_id)
            return {"node_outputs": {node_id: input_text}}

        llm = make_chat_model_sync(
            provider=provider,
            model=model_name,
            credentials=credentials,
            temperature=0.0,
            streaming=False,
        )

        guardrail_result = await _run_checks(input_text, llm)

        if guardrail_result.passed:
            _log.debug("input_guardrail [%s]: passed all checks", node_id)
            return {"node_outputs": {node_id: input_text}}

        # Blocked — set guardrail_blocked flag so compiler conditional edges
        # route directly to END, skipping all downstream processing nodes.
        rejection = f"{_BLOCK_PREFIX}\n{guardrail_result.rejection_message}"
        _log.info(
            "input_guardrail [%s]: blocking — check=%s",
            node_id, guardrail_result.failed_check,
        )
        return {
            "node_outputs": {node_id: rejection},
            "final_output": rejection,
            "guardrail_blocked": True,
        }

    input_guardrail_node.__name__ = f"input_guardrail_{node_id}"
    return input_guardrail_node


async def _dispatch(
    check_name: str,
    text: str,
    llm: BaseChatModel,
    threshold: float,
    custom_rule: str,
) -> CheckResult:
    """Route to the appropriate check module."""
    if check_name == CheckType.PII:
        from app.services.guardrail.checks.pii import run  # noqa: PLC0415
        return await run(text, llm)

    if check_name == CheckType.TOKENS:
        from app.services.guardrail.checks.tokens import run  # noqa: PLC0415
        return await run(text, llm)

    if check_name == CheckType.JAILBREAK:
        from app.services.guardrail.checks.jailbreak import run  # noqa: PLC0415
        return await run(text, llm, threshold)

    if check_name == CheckType.INJECTION:
        from app.services.guardrail.checks.injection import run  # noqa: PLC0415
        return await run(text, llm, threshold)

    if check_name == CheckType.TOXICITY:
        from app.services.guardrail.checks.toxicity import run  # noqa: PLC0415
        return await run(text, llm)

    if check_name == CheckType.CUSTOM:
        from app.services.guardrail.checks.custom import run  # noqa: PLC0415
        return await run(text, llm, custom_rule)

    # Unknown check — skip (pass)
    _log.warning("input_guardrail: unknown check_name '%s', skipping", check_name)
    return CheckResult(
        check_type=CheckType.CUSTOM,
        passed=True,
        reason=f"Unknown check '{check_name}' — skipped",
    )
