"""Custom guardrail check — user-defined natural-language rule, LLM only."""
from __future__ import annotations

from langchain_core.language_models import BaseChatModel

from app.services.guardrail.llm_judge import judge
from app.services.guardrail.models import CheckResult, CheckType


async def run(text: str, llm: BaseChatModel, rule_description: str) -> CheckResult:
    """Run a custom guardrail defined by the user's natural-language description.

    Args:
        text: Input text to validate.
        llm: Judge LLM.
        rule_description: User-defined rule, e.g. "금융 투자 조언이나 특정 종목 추천".
    """
    if not rule_description or not rule_description.strip():
        return CheckResult(check_type=CheckType.CUSTOM, passed=True, reason="No custom rule defined")

    passed, reason = await judge(llm, text, "custom", rule_description.strip())
    return CheckResult(check_type=CheckType.CUSTOM, passed=passed, reason=reason)
