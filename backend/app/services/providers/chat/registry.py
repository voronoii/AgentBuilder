from __future__ import annotations

import logging
import os

from langchain_core.language_models import BaseChatModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import AppError, ErrorCode
from app.repositories.settings import SettingsRepository

_log = logging.getLogger(__name__)

_SUPPORTED_PROVIDERS = {"openai", "anthropic", "vllm", "openrouter"}


async def _resolve_key(
    repo: SettingsRepository,
    db_key: str,
    env_value: str | None,
) -> str | None:
    """Check DB first, fall back to env var."""
    db_val = await repo.get_value(db_key)
    if db_val:
        return db_val
    return env_value or None


async def resolve_provider_credentials(
    provider: str,
    session: AsyncSession,
) -> dict[str, str]:
    """Resolve API key / URL for a provider at compile time.

    Must be called while the DB session is still active (compile phase).
    Returns a dict with the resolved credential (e.g. {"api_key": "sk-..."}).

    Raises:
        AppError(SETTING_NOT_FOUND): If a required credential is not configured.
        AppError(VALIDATION_FAILED): If the provider is not supported.
    """
    if provider not in _SUPPORTED_PROVIDERS:
        raise AppError(
            status_code=400,
            code=ErrorCode.VALIDATION_FAILED,
            detail=f"Unsupported chat provider: {provider!r}. Must be one of {sorted(_SUPPORTED_PROVIDERS)}.",
        )

    repo = SettingsRepository(session)

    if provider == "openai":
        api_key = await _resolve_key(repo, "OPENAI_API_KEY", os.environ.get("AGENTBUILDER_OPENAI_API_KEY"))
        if not api_key:
            raise AppError(status_code=422, code=ErrorCode.SETTING_NOT_FOUND,
                           detail="OpenAI API key is not configured.")
        return {"api_key": api_key}

    if provider == "anthropic":
        api_key = await _resolve_key(repo, "ANTHROPIC_API_KEY", os.environ.get("AGENTBUILDER_ANTHROPIC_API_KEY"))
        if not api_key:
            raise AppError(status_code=422, code=ErrorCode.SETTING_NOT_FOUND,
                           detail="Anthropic API key is not configured.")
        return {"api_key": api_key}

    if provider == "openrouter":
        api_key = await _resolve_key(repo, "OPENROUTER_API_KEY", os.environ.get("AGENTBUILDER_OPENROUTER_API_KEY"))
        if not api_key:
            raise AppError(status_code=422, code=ErrorCode.SETTING_NOT_FOUND,
                           detail="OpenRouter API key is not configured.")
        return {"api_key": api_key}

    # vllm — DB → env var (pydantic-settings) → raw env
    from app.core.config import get_settings
    env_vllm = get_settings().vllm_base_url or os.environ.get("AGENTBUILDER_VLLM_BASE_URL")
    vllm_base_url = await _resolve_key(repo, "VLLM_BASE_URL", env_vllm)
    if not vllm_base_url:
        raise AppError(status_code=422, code=ErrorCode.SETTING_NOT_FOUND,
                       detail="vLLM base URL is not configured.")
    vllm_model = await _resolve_key(repo, "VLLM_DEFAULT_MODEL", None)
    return {"base_url": vllm_base_url, "default_model": vllm_model or ""}


def make_chat_model_sync(
    provider: str,
    model: str,
    credentials: dict[str, str],
    *,
    temperature: float = 0.7,
    streaming: bool = True,
) -> BaseChatModel:
    """Create a chat model using pre-resolved credentials (no DB access).

    This is the runtime-safe version — credentials are resolved at compile
    time by resolve_provider_credentials().
    """
    if provider == "openai":
        from langchain_openai import ChatOpenAI
        return ChatOpenAI(model=model, api_key=credentials["api_key"],
                          temperature=temperature, streaming=streaming)

    if provider == "anthropic":
        from langchain_anthropic import ChatAnthropic
        return ChatAnthropic(model=model, api_key=credentials["api_key"],
                             temperature=temperature, streaming=streaming)

    if provider == "openrouter":
        from langchain_openai import ChatOpenAI
        return ChatOpenAI(
            model=model, base_url="https://openrouter.ai/api/v1",
            api_key=credentials["api_key"], temperature=temperature,
            streaming=streaming,
            default_headers={"HTTP-Referer": "https://agentbuilder.local",
                             "X-OpenRouter-Title": "AgentBuilder"},
        )

    # vllm — resolve "default" to actual model via /v1/models if needed
    from langchain_openai import ChatOpenAI
    effective_model = model
    if model == "default":
        effective_model = credentials.get("default_model") or ""
    if not effective_model or effective_model == "default":
        # Auto-detect first available model from vLLM endpoint
        import httpx
        try:
            resp = httpx.get(f"{credentials['base_url']}/models", timeout=5.0)
            resp.raise_for_status()
            models = resp.json().get("data", [])
            if models:
                effective_model = models[0]["id"]
                _log.info("vLLM auto-detected model: %s", effective_model)
        except Exception:
            _log.warning("Failed to auto-detect vLLM model, using 'default'")
            effective_model = "default"
    return ChatOpenAI(model=effective_model, base_url=credentials["base_url"],
                      api_key="dummy", temperature=temperature, streaming=streaming)


async def make_chat_model(
    provider: str,
    model: str,
    session: AsyncSession,
    *,
    temperature: float = 0.7,
    streaming: bool = True,
) -> BaseChatModel:
    """Instantiate a LangChain chat model for the given provider.

    Convenience wrapper that resolves credentials and creates the model
    in one call. For compile/runtime separation, use
    resolve_provider_credentials() + make_chat_model_sync() instead.

    Args:
        provider: One of "openai", "anthropic", "vllm", "openrouter".
        model: Model identifier (e.g. "gpt-4o", "claude-sonnet-4-20250514").
        session: Active async DB session used to fetch API keys from settings.
        temperature: Sampling temperature (default 0.7).
        streaming: Whether to enable streaming (default True).

    Returns:
        A configured BaseChatModel instance.

    Raises:
        AppError(SETTING_NOT_FOUND): If a required API key or URL is not configured.
        AppError(VALIDATION_FAILED): If the provider is not supported.
    """
    credentials = await resolve_provider_credentials(provider, session)
    return make_chat_model_sync(provider, model, credentials,
                                temperature=temperature, streaming=streaming)
