"""Agent Hook system — deepagents-inspired middleware for agent behavior control."""

from app.hooks.protocol import AgentHook, HookContext, HookVerdict

__all__ = ["AgentHook", "HookContext", "HookVerdict"]
