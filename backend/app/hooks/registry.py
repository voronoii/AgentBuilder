"""Registry that maps hook type strings to hook class constructors."""

from __future__ import annotations

import logging
from typing import Any

from app.hooks.protocol import AgentHook

_log = logging.getLogger(__name__)

_HOOK_TYPES: dict[str, type] = {}


def _register_defaults() -> None:
    from app.hooks.kb_citation_verifier import KBCitationVerifierHook
    from app.hooks.llm_verifier import LLMVerifierHook
    from app.hooks.tool_usage_checker import ToolUsageCheckerHook

    _HOOK_TYPES["tool_usage_checker"] = ToolUsageCheckerHook
    _HOOK_TYPES["kb_citation_verifier"] = KBCitationVerifierHook
    _HOOK_TYPES["llm_verifier"] = LLMVerifierHook


def build_hook(config: dict[str, Any]) -> AgentHook:
    """Instantiate a hook from a node_data config dict.

    Expected keys:
        type (str): hook type name (e.g. "tool_usage_checker")
        ... plus type-specific parameters in camelCase (converted to snake_case)
    """
    if not _HOOK_TYPES:
        _register_defaults()

    hook_type = config.get("type", "")
    cls = _HOOK_TYPES.get(hook_type)
    if cls is None:
        raise ValueError(f"Unknown hook type: {hook_type!r}")

    # Convert camelCase config keys to snake_case kwargs
    kwargs: dict[str, Any] = {}
    _CAMEL_TO_SNAKE = {
        "requiredTools": "required",
        "forbiddenTools": "forbidden",
        "kbId": "kb_id",
        "maxRetries": "max_retries",
        "onExhausted": "on_exhausted",
        "timeoutMs": "timeout_ms",
        "retryStrategy": "retry_strategy",
        "fallbackMessage": "fallback_message",
        "verifierProvider": "provider",
        "verifierModel": "model",
    }
    for key, value in config.items():
        if key == "type":
            continue
        snake_key = _CAMEL_TO_SNAKE.get(key, key)
        kwargs[snake_key] = value

    return cls(**kwargs)


def build_hooks_from_node_data(node_data: dict[str, Any]) -> list[AgentHook]:
    """Parse the hooks config from agent node_data.

    Supports the structured format:
        {"hooks": {"after_agent": [{...}, {...}]}}
    """
    hooks_config = node_data.get("hooks")
    if not hooks_config:
        return []

    # Structured format: {"after_agent": [...]}
    if isinstance(hooks_config, dict):
        after_agent = hooks_config.get("after_agent", [])
    else:
        after_agent = []

    hooks: list[AgentHook] = []
    for cfg in after_agent:
        try:
            hooks.append(build_hook(cfg))
        except (ValueError, TypeError) as exc:
            _log.warning("Skipping invalid hook config %s: %s", cfg, exc)

    return hooks
