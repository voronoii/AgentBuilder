from __future__ import annotations

from importlib.metadata import PackageNotFoundError
from importlib.metadata import version as _pkg_version

from pydantic_settings import BaseSettings, SettingsConfigDict


def _resolve_app_version() -> str:
    """Single source of truth — read version from pyproject.toml via installed metadata.

    Falls back to "0.0.0" when the package is not installed (e.g. running tests
    from a fresh checkout without `pip install -e .`).
    """
    try:
        return _pkg_version("agentbuilder-backend")
    except PackageNotFoundError:
        return "0.0.0"


APP_VERSION: str = _resolve_app_version()


class Settings(BaseSettings):
    """All runtime configuration. Read once at startup; do not mutate."""

    model_config = SettingsConfigDict(
        env_prefix="AGENTBUILDER_",
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # App
    app_name: str = "AgentBuilder"
    debug: bool = False

    # API server
    api_host: str = "0.0.0.0"
    api_port: int = 8000

    # Database
    database_url: str = "postgresql+asyncpg://agentbuilder:agentbuilder@postgres:5432/agentbuilder"

    # Vector DB
    qdrant_url: str = "http://qdrant:6333"

    # Embedding defaults (see spec §5, §6.4)
    default_embedding_provider: str = "local_hf"
    default_embedding_model_path: str = "/models/snowflake-arctic-embed-l-v2.0-ko"
    default_embedding_dim: int = 1024

    # Uploads and ingestion
    uploads_dir: str = "/app/uploads"
    ingestion_max_concurrency: int = 2
    max_upload_mb: int = 50

    # Qdrant
    qdrant_collection_prefix: str = "kb_"

    # CORS — JSON list in env, e.g. '["http://localhost:23000"]'
    cors_origins: list[str] = [
        "http://localhost:23000",
        "http://localhost:3000",
    ]

    # MCP tool system
    mcp_discovery_timeout: int = 30  # seconds per discovery attempt

    # Optional API keys for chat providers (loaded if present)
    openai_api_key: str | None = None
    anthropic_api_key: str | None = None

    # vLLM (OpenAI-compatible local model serving)
    vllm_base_url: str | None = None


_settings_cache: Settings | None = None


def get_settings() -> Settings:
    """Cached singleton — parsed once, reused on every call."""
    global _settings_cache  # noqa: PLW0603
    if _settings_cache is None:
        _settings_cache = Settings()
    return _settings_cache
