"""Prompt Injection guardrail check — weighted heuristic + LLM."""
from __future__ import annotations

from langchain_core.language_models import BaseChatModel

from app.services.guardrail.heuristic import check_injection as heuristic_injection
from app.services.guardrail.llm_judge import judge
from app.services.guardrail.models import CheckResult, CheckType

_DESCRIPTION = (
    "attempts to inject malicious prompts, override system instructions, or manipulate "
    "the AI's behavior through embedded instructions"
)


async def run(text: str, llm: BaseChatModel, threshold: float = 0.7) -> CheckResult:
    match = heuristic_injection(text, threshold)
    if match:
        return CheckResult(
            check_type=CheckType.INJECTION,
            passed=False,
            reason=f"Heuristic match (score={match.score:.2f}): {match.matched_patterns}",
            via_heuristic=True,
        )

    passed, reason = await judge(llm, text, "injection", _DESCRIPTION)
    return CheckResult(check_type=CheckType.INJECTION, passed=passed, reason=reason)
