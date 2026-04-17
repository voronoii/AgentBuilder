"""Heuristic guardrail engine — weighted regex scoring.

Langflow 대비 개선:
- Jailbreak / Injection 뿐 아니라 PII, Tokens 패턴도 정규식 1차 필터로 포착
- 명확한 패턴(주민번호, 카드번호, API 키 형식)은 LLM 호출 없이 즉시 차단 → 비용 절감

반환값:
- score >= threshold → 즉시 차단 (LLM 판정 생략)
- score < threshold  → LLM 판정으로 진행
"""
from __future__ import annotations

import re
from dataclasses import dataclass


@dataclass(frozen=True)
class HeuristicMatch:
    score: float
    matched_patterns: list[str]


# ── Jailbreak / Prompt Injection ──────────────────────────────────────────────

_JAILBREAK_STRONG: dict[str, float] = {
    r"ignore\s+.*instruct": 0.8,
    r"forget\s+.*instruct": 0.8,
    r"disregard\s+.*instruct": 0.8,
    r"ignore\s+.*previous": 0.7,
    r"\bjailbreak\b": 0.9,
    r"pretend\s+you\s+are\s+(un)?restricted": 0.8,
    r"ignore\s+(all\s+)?safety": 0.8,
}

_JAILBREAK_WEAK: dict[str, float] = {
    r"\bbypass\b": 0.2,
    r"system\s*prompt": 0.3,
    r"\bact\s+as\b": 0.15,
    r"\bno\s+rules\b": 0.2,
    r"without\s+restriction": 0.25,
    r"ignore\s+filter": 0.3,
}

_INJECTION_STRONG: dict[str, float] = {
    r"ignore\s+(all\s+)?previous\s+instructions?": 0.9,
    r"forget\s+(all\s+)?previous\s+instructions?": 0.9,
    r"you\s+are\s+now\s+a?\s*(different|new)\s+ai": 0.85,
    r"output\s+(the\s+)?system\s+prompt": 0.9,
    r"reveal\s+(your\s+)?instructions?": 0.8,
    r"print\s+(your\s+)?system\s+prompt": 0.9,
}

_INJECTION_WEAK: dict[str, float] = {
    r"override\s+(system|instructions?)": 0.3,
    r"new\s+instructions?:": 0.25,
    r"end\s+of\s+(system\s+)?prompt": 0.25,
}

# ── PII — clear regex patterns (no LLM needed for these) ─────────────────────

_PII_STRONG: dict[str, float] = {
    # 주민등록번호: 6자리-7자리
    r"\b\d{6}[-\s]?[1-4]\d{6}\b": 1.0,
    # 신용/체크카드: 4자리 4묶음
    r"\b(?:\d{4}[-\s]){3}\d{4}\b": 1.0,
    # 여권번호 (한국): M + 8자리
    r"\b[A-Z][A-Z0-9]{8}\b": 0.6,
}

_PII_WEAK: dict[str, float] = {
    # 이메일
    r"\b[A-Za-z0-9._%+\-]+@[A-Za-z0-9.\-]+\.[A-Za-z]{2,}\b": 0.5,
    # 전화번호 (한국)
    r"\b0[1-9]\d[-\s]?\d{3,4}[-\s]?\d{4}\b": 0.6,
}

# ── Tokens / API Keys ─────────────────────────────────────────────────────────

_TOKEN_STRONG: dict[str, float] = {
    # OpenAI key: sk- 으로 시작하는 48자 이상
    r"\bsk-[A-Za-z0-9]{20,}\b": 1.0,
    # Anthropic key: sk-ant-
    r"\bsk-ant-[A-Za-z0-9\-_]{20,}\b": 1.0,
    # AWS Access Key
    r"\bAKIA[0-9A-Z]{16}\b": 1.0,
    # GitHub token: ghp_, gho_, github_pat_
    r"\b(?:ghp|gho|ghu|ghs|ghr)_[A-Za-z0-9_]{36,}\b": 1.0,
    r"\bgithub_pat_[A-Za-z0-9_]{20,}\b": 1.0,
    # Generic Bearer token pattern
    r"\bBearer\s+[A-Za-z0-9\-._~+/]+=*\b": 0.8,
}

_TOKEN_WEAK: dict[str, float] = {
    # 'password' 라는 단어 + '=' or ':' + 비공백 문자열
    r"password\s*[:=]\s*\S{6,}": 0.5,
    r"api[_\-]?key\s*[:=]\s*\S{8,}": 0.6,
    r"secret\s*[:=]\s*\S{8,}": 0.5,
}


def _score(text: str, strong: dict[str, float], weak: dict[str, float]) -> HeuristicMatch:
    """Compute weighted score against strong+weak patterns."""
    lower = text.lower()
    total = 0.0
    matched: list[str] = []

    for pattern, weight in {**strong, **weak}.items():
        if re.search(pattern, lower if pattern.islower() else text, re.IGNORECASE):
            total += weight
            matched.append(pattern)

    return HeuristicMatch(score=min(total, 1.0), matched_patterns=matched)


def check_jailbreak(text: str, threshold: float = 0.7) -> HeuristicMatch | None:
    """Returns HeuristicMatch if score >= threshold, else None."""
    result = _score(text, _JAILBREAK_STRONG, _JAILBREAK_WEAK)
    return result if result.score >= threshold else None


def check_injection(text: str, threshold: float = 0.7) -> HeuristicMatch | None:
    result = _score(text, _INJECTION_STRONG, _INJECTION_WEAK)
    return result if result.score >= threshold else None


def check_pii(text: str) -> HeuristicMatch | None:
    """PII heuristic — strong patterns alone are sufficient for hard block.
    Returns match if any strong pattern fires, or weak score >= 0.6.
    """
    strong_result = _score(text, _PII_STRONG, {})
    if strong_result.matched_patterns:
        return strong_result

    weak_result = _score(text, {}, _PII_WEAK)
    return weak_result if weak_result.score >= 0.6 else None


def check_tokens(text: str) -> HeuristicMatch | None:
    """Token/credential heuristic — strong patterns alone are sufficient."""
    strong_result = _score(text, _TOKEN_STRONG, {})
    if strong_result.matched_patterns:
        return strong_result

    weak_result = _score(text, {}, _TOKEN_WEAK)
    return weak_result if weak_result.score >= 0.6 else None
