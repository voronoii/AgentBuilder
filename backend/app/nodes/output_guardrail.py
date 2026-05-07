"""Output Guardrail node — filters LLM/Agent output before it reaches Chat Output.

캔버스 배치: LLM / Agent → [Output Guardrail] → Chat Output

동작:
- 활성화된 체크를 순서대로 실행 (fail-fast: 첫 위반에서 중단)
- pii_exposure + action="mask": 차단 대신 PII를 마스킹 후 통과
- block → guardrail_blocked=True 설정 → compiler conditional edge로 END 라우팅
- warn  → 경고 접두사 추가 후 통과 (guardrail_blocked=False)

node_data 필드:
    checks           (list[str])   활성 체크 목록. 예: ["harmful", "pii_exposure"]
    custom_rule      (str)         커스텀 가드레일 설명 (checks에 "custom" 포함 시)
    action           (str)         "block" | "warn" | "mask"
                                    mask는 pii_exposure에만 적용; 나머지는 block으로 처리
    provider         (str)         판정 LLM 프로바이더
    model            (str)         판정 LLM 모델명
    format_rules     (dict)        형식 검증 규칙 (checks에 "format" 포함 시)
                                    예: {"json": true, "max_length": 2000}
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

_DEFAULT_CHECKS: list[str] = ["harmful", "pii_exposure"]
_BLOCK_PREFIX = "⚠️ AI 응답이 보안 정책에 의해 차단되었습니다."
_WARN_PREFIX = "⚠️ 주의: AI 응답에 잠재적으로 문제가 있는 내용이 포함될 수 있습니다.\n\n"


async def make_output_guardrail_node(
    node_id: str,
    node_data: dict,
    session: AsyncSession,
    predecessor_ids: list[str] | None = None,
) -> Callable[[WorkflowState], dict]:
    """Factory: create an Output Guardrail LangGraph node."""
    checks: list[str] = node_data.get("checks") or _DEFAULT_CHECKS
    custom_rule: str = node_data.get("custom_rule", "") or ""
    action: str = node_data.get("action", "block") or "block"
    provider: str = node_data.get("provider", "openai")
    model_name: str = node_data.get("model", "gpt-4o-mini")
    format_rules: dict = node_data.get("format_rules") or {}

    credentials = await resolve_provider_credentials(provider, session)

    async def _run_checks(
        text: str, llm: BaseChatModel
    ) -> tuple[GuardrailResult, str]:
        """Execute checks in order. Returns (result, output_text).

        output_text may differ from input when pii_exposure + mask is used.
        """
        results: list[CheckResult] = []
        current_text = text  # may be mutated by mask action

        for check_name in checks:
            result, current_text = await _dispatch(
                check_name, current_text, llm, action, custom_rule, format_rules
            )
            results.append(result)
            if not result.passed:
                _log.info(
                    "output_guardrail [%s]: BLOCKED by %s (heuristic=%s)",
                    node_id, check_name, result.via_heuristic,
                )
                return GuardrailResult.fail(result.check_type, results), current_text

        return GuardrailResult.ok(results), current_text

    async def output_guardrail_node(state: WorkflowState) -> dict:
        output_text = get_input_text(state, node_id, predecessor_ids=predecessor_ids)

        if not output_text or not output_text.strip():
            _log.debug("output_guardrail [%s]: empty output, passing through", node_id)
            return {"node_outputs": {node_id: output_text}}

        llm = make_chat_model_sync(
            provider=provider,
            model=model_name,
            credentials=credentials,
            temperature=0.0,
            streaming=False,
        )

        guardrail_result, processed_text = await _run_checks(output_text, llm)

        if guardrail_result.passed:
            _log.debug("output_guardrail [%s]: passed all checks", node_id)
            return {"node_outputs": {node_id: processed_text}}

        # Failed — apply configured action
        if action == "warn":
            warned_output = f"{_WARN_PREFIX}{output_text}"
            _log.info(
                "output_guardrail [%s]: warn mode — passing with warning prefix, check=%s",
                node_id, guardrail_result.failed_check,
            )
            return {"node_outputs": {node_id: warned_output}}

        # block (default)
        rejection = f"{_BLOCK_PREFIX}\n{guardrail_result.rejection_message}"
        _log.info(
            "output_guardrail [%s]: blocking — check=%s",
            node_id, guardrail_result.failed_check,
        )
        return {
            "node_outputs": {node_id: rejection},
            "final_output": rejection,
            "guardrail_blocked": True,
        }

    output_guardrail_node.__name__ = f"output_guardrail_{node_id}"
    return output_guardrail_node


async def _dispatch(
    check_name: str,
    text: str,
    llm: BaseChatModel,
    action: str,
    custom_rule: str,
    format_rules: dict,
) -> tuple[CheckResult, str]:
    """Route to the appropriate output check module.

    Returns (CheckResult, output_text). output_text may be masked for pii_exposure.
    """
    if check_name == CheckType.HARMFUL:
        from app.services.guardrail.checks.harmful import run  # noqa: PLC0415
        return await run(text, llm), text

    if check_name == CheckType.PII_EXPOSURE:
        from app.services.guardrail.checks.pii_mask import run  # noqa: PLC0415
        result, out = await run(text, llm, action=action)
        return result, out

    if check_name == CheckType.FORMAT:
        from app.services.guardrail.checks.format_validator import run  # noqa: PLC0415
        return run(text, format_rules), text

    if check_name == CheckType.CUSTOM:
        from app.services.guardrail.checks.custom import run  # noqa: PLC0415
        return await run(text, llm, custom_rule), text

    # Unknown check — skip
    _log.warning("output_guardrail: unknown check_name '%s', skipping", check_name)
    return CheckResult(
        check_type=CheckType.CUSTOM,
        passed=True,
        reason=f"Unknown check '{check_name}' — skipped",
    ), text
