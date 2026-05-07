"""Format Validation guardrail check — rules-based, no LLM needed.

출력 가드레일 전용: LLM 응답이 사용자가 지정한 형식 조건을 만족하는지 검증.
LLM 호출 없이 비용 없음 — 순수 Python 규칙 기반.

지원 검증 규칙 (format_rules dict):
  json          : bool  — 응답이 유효한 JSON이어야 함
  min_length    : int   — 최소 문자 수
  max_length    : int   — 최대 문자 수
  must_contain  : list[str] — 반드시 포함해야 할 문자열 목록
  must_not_contain: list[str] — 포함하면 안 되는 문자열 목록
  starts_with   : str   — 특정 접두사로 시작해야 함
  ends_with     : str   — 특정 접미사로 끝나야 함
"""
from __future__ import annotations

import json
import logging

from app.services.guardrail.models import CheckResult, CheckType

_log = logging.getLogger(__name__)


def run(text: str, format_rules: dict) -> CheckResult:
    """Run format validation synchronously (no I/O).

    Args:
        text: LLM output text to validate.
        format_rules: Dict of rule_name → rule_value. Unknown keys are ignored.

    Returns:
        CheckResult with passed=True if all rules pass.
    """
    if not format_rules:
        return CheckResult(
            check_type=CheckType.FORMAT,
            passed=True,
            reason="No format rules configured",
        )

    violations: list[str] = []

    # JSON validity
    if format_rules.get("json"):
        try:
            json.loads(text.strip())
        except (json.JSONDecodeError, ValueError):
            violations.append("응답이 유효한 JSON 형식이 아닙니다")

    # Length constraints
    length = len(text)
    if "min_length" in format_rules:
        min_len = int(format_rules["min_length"])
        if length < min_len:
            violations.append(f"응답 길이({length}자)가 최소 {min_len}자 미만입니다")

    if "max_length" in format_rules:
        max_len = int(format_rules["max_length"])
        if length > max_len:
            violations.append(f"응답 길이({length}자)가 최대 {max_len}자를 초과합니다")

    # Content presence
    for required in format_rules.get("must_contain", []):
        if required not in text:
            violations.append(f"응답에 필수 문자열 '{required}'이(가) 없습니다")

    for forbidden in format_rules.get("must_not_contain", []):
        if forbidden in text:
            violations.append(f"응답에 금지 문자열 '{forbidden}'이(가) 포함되어 있습니다")

    # Prefix / suffix
    if "starts_with" in format_rules:
        prefix = format_rules["starts_with"]
        if not text.lstrip().startswith(prefix):
            violations.append(f"응답이 '{prefix}'(으)로 시작하지 않습니다")

    if "ends_with" in format_rules:
        suffix = format_rules["ends_with"]
        if not text.rstrip().endswith(suffix):
            violations.append(f"응답이 '{suffix}'(으)로 끝나지 않습니다")

    if violations:
        _log.debug("format_validator: %d violation(s): %s", len(violations), violations)
        return CheckResult(
            check_type=CheckType.FORMAT,
            passed=False,
            reason="; ".join(violations),
            via_heuristic=True,  # rules-based = heuristic (no LLM)
        )

    return CheckResult(
        check_type=CheckType.FORMAT,
        passed=True,
        reason="All format rules passed",
        via_heuristic=True,
    )
