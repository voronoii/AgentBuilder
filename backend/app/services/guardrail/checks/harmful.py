"""Harmful Response guardrail check — LLM-as-judge only.

출력 가드레일 전용: LLM이 생성한 응답이 유해/부적절한지 판정.
정규식 1차 필터 없음 — 유해 콘텐츠 패턴은 형태가 너무 다양해 규칙 기반 탐지가 어렵.
"""
from __future__ import annotations

from langchain_core.language_models import BaseChatModel

from app.services.guardrail.llm_judge import judge
from app.services.guardrail.models import CheckResult, CheckType

_DESCRIPTION = (
    "harmful, dangerous, violent, sexually explicit, hateful, discriminatory, "
    "or otherwise inappropriate content that should not be delivered to users. "
    "Normal AI assistant responses that are helpful and informative are NOT harmful."
)


async def run(text: str, llm: BaseChatModel) -> CheckResult:
    """Run harmful response check: LLM judge only."""
    passed, reason = await judge(llm, text, "harmful", _DESCRIPTION)
    return CheckResult(check_type=CheckType.HARMFUL, passed=passed, reason=reason)
