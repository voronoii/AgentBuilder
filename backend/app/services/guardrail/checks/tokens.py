"""Tokens/Passwords guardrail check — regex 1차 필터 + LLM 2차 판정."""
from __future__ import annotations

from langchain_core.language_models import BaseChatModel

from app.services.guardrail.heuristic import check_tokens as heuristic_tokens
from app.services.guardrail.llm_judge import judge
from app.services.guardrail.models import CheckResult, CheckType

_DESCRIPTION = (
    "API tokens, passwords, API keys, access keys, secret keys, authentication credentials, "
    "or any other sensitive credentials or secrets"
)


async def run(text: str, llm: BaseChatModel) -> CheckResult:
    match = heuristic_tokens(text)
    if match:
        return CheckResult(
            check_type=CheckType.TOKENS,
            passed=False,
            reason=f"Heuristic match (score={match.score:.2f}): {match.matched_patterns}",
            via_heuristic=True,
        )

    passed, reason = await judge(llm, text, "tokens", _DESCRIPTION)
    return CheckResult(check_type=CheckType.TOKENS, passed=passed, reason=reason)
