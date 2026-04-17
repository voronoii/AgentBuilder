"""PII guardrail check — regex 1차 필터 + LLM 2차 판정."""
from __future__ import annotations

from langchain_core.language_models import BaseChatModel

from app.services.guardrail.heuristic import check_pii as heuristic_pii
from app.services.guardrail.llm_judge import judge
from app.services.guardrail.models import CheckResult, CheckType

_DESCRIPTION = (
    "personal identifiable information (PII) such as names, addresses, phone numbers, "
    "email addresses, social security numbers, credit card numbers, or any other personal data"
)


async def run(text: str, llm: BaseChatModel) -> CheckResult:
    """Run PII check: heuristic first, LLM if heuristic misses."""
    match = heuristic_pii(text)
    if match:
        return CheckResult(
            check_type=CheckType.PII,
            passed=False,
            reason=f"Heuristic match (score={match.score:.2f}): {match.matched_patterns}",
            via_heuristic=True,
        )

    passed, reason = await judge(llm, text, "pii", _DESCRIPTION)
    return CheckResult(check_type=CheckType.PII, passed=passed, reason=reason)
