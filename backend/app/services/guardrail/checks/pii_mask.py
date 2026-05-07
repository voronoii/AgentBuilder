"""PII Exposure guardrail check for output — regex detect + LLM + optional masking.

출력 가드레일 전용: LLM 응답에 포함된 PII를 탐지하고,
action="mask" 시 차단 대신 패턴을 마스킹 처리 후 통과.

입력 가드레일의 pii.py와 차이:
- 입력: PII 포함 시 즉시 차단 (block only)
- 출력: block / mask 선택 가능. mask 시 regex 치환 후 masked_text 반환.
"""
from __future__ import annotations

import re

from langchain_core.language_models import BaseChatModel

from app.services.guardrail.heuristic import check_pii as heuristic_pii
from app.services.guardrail.llm_judge import judge
from app.services.guardrail.models import CheckResult, CheckType

_DESCRIPTION = (
    "personal identifiable information (PII) such as names, phone numbers, "
    "email addresses, social security numbers, credit card numbers, or any "
    "other personal data that should not be exposed in AI responses"
)

# Masking substitution patterns — order matters (more specific first)
_MASK_PATTERNS: list[tuple[str, str]] = [
    # 주민등록번호: XXXXXX-XXXXXXX
    (r"\b(\d{6})[-\s]?([1-4]\d{6})\b", r"\1-*******"),
    # 신용/체크카드: XXXX-XXXX-XXXX-XXXX
    (r"\b(\d{4})[-\s](\d{4})[-\s](\d{4})[-\s](\d{4})\b", r"\1-****-****-\4"),
    # 이메일: user@domain.com → u***@domain.com
    (r"\b([A-Za-z0-9])[A-Za-z0-9._%+\-]*(@[A-Za-z0-9.\-]+\.[A-Za-z]{2,})\b", r"\1***\2"),
    # 전화번호 (한국): 010-XXXX-XXXX
    (r"\b(0[1-9]\d)[-\s]?(\d{3,4})[-\s]?(\d{4})\b", r"\1-****-\3"),
]


def _mask_pii(text: str) -> str:
    """Apply all masking patterns to text. Returns masked copy."""
    masked = text
    for pattern, replacement in _MASK_PATTERNS:
        masked = re.sub(pattern, replacement, masked)
    return masked


async def run(
    text: str,
    llm: BaseChatModel,
    action: str = "block",
) -> tuple[CheckResult, str]:
    """Run PII exposure check.

    Args:
        text: LLM output text to check.
        llm: Judge LLM instance.
        action: "block" | "mask". When "mask", PII is replaced with placeholders
                and the result is passed through (passed=True with masked text).

    Returns:
        (CheckResult, output_text) — output_text is masked if action="mask" and
        PII was found, otherwise identical to input.
    """
    match = heuristic_pii(text)

    if match:
        if action == "mask":
            masked = _mask_pii(text)
            return (
                CheckResult(
                    check_type=CheckType.PII_EXPOSURE,
                    passed=True,  # pass through — content was masked
                    reason=f"PII masked (heuristic score={match.score:.2f})",
                    via_heuristic=True,
                ),
                masked,
            )
        return (
            CheckResult(
                check_type=CheckType.PII_EXPOSURE,
                passed=False,
                reason=f"Heuristic match (score={match.score:.2f}): {match.matched_patterns}",
                via_heuristic=True,
            ),
            text,
        )

    # LLM stage
    passed, reason = await judge(llm, text, "pii_exposure", _DESCRIPTION)

    if not passed and action == "mask":
        # LLM detected PII — apply best-effort masking
        masked = _mask_pii(text)
        return (
            CheckResult(
                check_type=CheckType.PII_EXPOSURE,
                passed=True,
                reason=f"PII masked (LLM-detected): {reason}",
            ),
            masked,
        )

    return (
        CheckResult(check_type=CheckType.PII_EXPOSURE, passed=passed, reason=reason),
        text,
    )
