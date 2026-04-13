from __future__ import annotations

import logging
from typing import Annotated

import httpx
from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.db import get_session
from app.repositories.settings import SettingsRepository

_log = logging.getLogger(__name__)

router = APIRouter(prefix="/providers", tags=["providers"])


class ProviderModelInfo(BaseModel):
    id: str
    name: str


class ProviderInfo(BaseModel):
    id: str
    name: str
    enabled: bool
    models: list[ProviderModelInfo]


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


@router.get("", response_model=list[ProviderInfo])
async def list_providers(
    session: Annotated[AsyncSession, Depends(get_session)],
) -> list[dict]:
    """Return provider list with enabled status from DB settings + env vars.

    Actual model instantiation (make_chat_model) is implemented in M4.
    """
    settings = get_settings()
    repo = SettingsRepository(session)

    openai_key = await _resolve_key(repo, "OPENAI_API_KEY", settings.openai_api_key)
    anthropic_key = await _resolve_key(
        repo, "ANTHROPIC_API_KEY", settings.anthropic_api_key
    )
    env_vllm = settings.vllm_base_url
    vllm_url = await _resolve_key(repo, "VLLM_BASE_URL", env_vllm)
    openrouter_key = await _resolve_key(repo, "OPENROUTER_API_KEY", None)

    # Dynamically fetch available models from vLLM endpoint
    vllm_models: list[dict[str, str]] = [{"id": "default", "name": "Default Model"}]
    if vllm_url:
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                resp = await client.get(f"{vllm_url}/models")
                resp.raise_for_status()
                data = resp.json().get("data", [])
                if data:
                    vllm_models = [
                        {"id": m["id"], "name": m["id"]}
                        for m in data
                    ]
        except Exception:
            _log.warning("Failed to fetch models from vLLM at %s", vllm_url, exc_info=True)

    return [
        {
            "id": "openai",
            "name": "OpenAI",
            "enabled": bool(openai_key),
            "models": [
                {"id": "gpt-5.4-mini", "name": "GPT-5.4 Mini"},
                {"id": "gpt-4o", "name": "GPT-4o"},
                {"id": "gpt-4o-mini", "name": "GPT-4o Mini"},
                {"id": "gpt-4-turbo", "name": "GPT-4 Turbo"},
            ],
        },
        {
            "id": "anthropic",
            "name": "Anthropic",
            "enabled": bool(anthropic_key),
            "models": [
                {"id": "claude-sonnet-4-20250514", "name": "Claude Sonnet 4"},
                {"id": "claude-haiku-4-20250414", "name": "Claude Haiku 4"},
            ],
        },
        {
            "id": "openrouter",
            "name": "OpenRouter",
            "enabled": bool(openrouter_key),
            "models": [
                {"id": "openai/gpt-5.2", "name": "GPT-5.2 (OpenAI)"},
                {"id": "openai/gpt-4.1-mini", "name": "GPT-4.1 Mini (OpenAI)"},
                {"id": "openai/gpt-4.1-nano", "name": "GPT-4.1 Nano (OpenAI)"},
                {"id": "anthropic/claude-sonnet-4-20250514", "name": "Claude Sonnet 4"},
                {"id": "google/gemini-2.5-flash", "name": "Gemini 2.5 Flash"},
                {"id": "google/gemini-3-flash-preview", "name": "Gemini 3 Flash"},
                {"id": "meta-llama/llama-4-maverick", "name": "Llama 4 Maverick"},
                {"id": "nvidia/nemotron-3-super-120b-a12b:free", "name": "Nemotron 3 Super 120B (free)"},
                {"id": "arcee-ai/trinity-large-preview:free", "name": "Trinity Large (free)"},
                {"id": "z-ai/glm-4.5-air:free", "name": "GLM 4.5 Air (free)"},
            ],
        },
        {
            "id": "vllm",
            "name": "vLLM (Local)",
            "enabled": bool(vllm_url),
            "models": vllm_models,
        },
    ]
