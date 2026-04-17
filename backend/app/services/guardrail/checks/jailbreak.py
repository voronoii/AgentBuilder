"""Jailbreak guardrail check — weighted heuristic + LLM."""
from __future__ import annotations

from langchain_core.language_models import BaseChatModel

from app.services.guardrail.heuristic import check_jailbreak as heuristic_jailbreak
from app.services.guardrail.llm_judge import judge
from app.services.guardrail.models import CheckResult, CheckType

_DESCRIPTION = (
    "attempts to bypass AI safety guidelines, manipulate the model's behavior, "
    "or make it ignore its instructions"
)


async def run(text: str, llm: BaseChatModel, threshold: float = 0.7) -> CheckResult:
    match = heuristic_jailbreak(text, threshold)
    if match:
        return CheckResult(
            check_type=CheckType.JAILBREAK,
            passed=False,
            reason=f"Heuristic match (score={match.score:.2f}): {match.matched_patterns}",
            via_heuristic=True,
        )

    passed, reason = await judge(llm, text, "jailbreak", _DESCRIPTION)
    return CheckResult(check_type=CheckType.JAILBREAK, passed=passed, reason=reason)
