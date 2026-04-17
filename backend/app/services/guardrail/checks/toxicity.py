"""Toxicity / Offensive Content guardrail check — LLM only."""
from __future__ import annotations

from langchain_core.language_models import BaseChatModel

from app.services.guardrail.llm_judge import judge
from app.services.guardrail.models import CheckResult, CheckType

_DESCRIPTION = (
    "offensive, hateful, discriminatory, violent, sexually explicit, or otherwise "
    "inappropriate content that violates content policies"
)


async def run(text: str, llm: BaseChatModel) -> CheckResult:
    passed, reason = await judge(llm, text, "toxicity", _DESCRIPTION)
    return CheckResult(check_type=CheckType.TOXICITY, passed=passed, reason=reason)
