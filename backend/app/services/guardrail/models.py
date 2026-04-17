"""Guardrail data models — CheckType enum and GuardrailResult dataclass."""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum


class CheckType(StrEnum):
    PII = "pii"
    TOKENS = "tokens"
    JAILBREAK = "jailbreak"
    INJECTION = "injection"
    TOXICITY = "toxicity"
    CUSTOM = "custom"


# Human-readable labels used in log messages and rejection explanations
CHECK_LABELS: dict[CheckType, str] = {
    CheckType.PII: "PII",
    CheckType.TOKENS: "Tokens/Passwords",
    CheckType.JAILBREAK: "Jailbreak",
    CheckType.INJECTION: "Prompt Injection",
    CheckType.TOXICITY: "Offensive Content",
    CheckType.CUSTOM: "Custom Guardrail",
}

# Fixed rejection messages (Langflow pattern — deterministic, no LLM reason leakage)
REJECTION_MESSAGES: dict[CheckType, str] = {
    CheckType.PII: (
        "입력에 개인 식별 정보(PII)가 포함되어 있습니다. "
        "이름, 주소, 전화번호, 이메일, 주민번호, 카드번호 등의 개인정보는 처리할 수 없습니다."
    ),
    CheckType.TOKENS: (
        "입력에 API 토큰, 비밀번호, API 키 등의 민감한 자격 증명이 포함되어 있습니다."
    ),
    CheckType.JAILBREAK: (
        "입력이 AI 안전 지침을 우회하거나 모델 동작을 조작하려는 시도를 포함합니다."
    ),
    CheckType.INJECTION: (
        "입력에 시스템 지침을 재정의하거나 AI 동작을 조작하려는 프롬프트 인젝션 시도가 감지되었습니다."
    ),
    CheckType.TOXICITY: (
        "입력에 공격적이거나 혐오스럽거나 부적절한 내용이 포함되어 있습니다."
    ),
    CheckType.CUSTOM: "입력이 커스텀 가드레일 기준을 위반했습니다.",
}


@dataclass(frozen=True)
class CheckResult:
    """Result of a single guardrail check."""

    check_type: CheckType
    passed: bool
    reason: str = ""          # internal reason (from heuristic or LLM) — not exposed to end users
    via_heuristic: bool = False


@dataclass
class GuardrailResult:
    """Aggregated result after running all enabled checks."""

    passed: bool
    failed_check: CheckType | None = None           # first check that failed (fail-fast)
    rejection_message: str = ""                     # end-user-facing message
    check_results: list[CheckResult] = field(default_factory=list)

    @classmethod
    def ok(cls, check_results: list[CheckResult]) -> "GuardrailResult":
        return cls(passed=True, check_results=check_results)

    @classmethod
    def fail(cls, failed: CheckType, check_results: list[CheckResult]) -> "GuardrailResult":
        return cls(
            passed=False,
            failed_check=failed,
            rejection_message=REJECTION_MESSAGES[failed],
            check_results=check_results,
        )
