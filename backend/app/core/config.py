from __future__ import annotations

from pydantic_settings import BaseSettings, SettingsConfigDict


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
    database_url: str = (
        "postgresql+asyncpg://agentbuilder:agentbuilder@postgres:5432/agentbuilder"
    )

    # Vector DB
    qdrant_url: str = "http://qdrant:6333"

    # Embedding defaults (see spec §5, §6.4)
    default_embedding_provider: str = "local_hf"
    default_embedding_model_path: str = "/models/snowflake-arctic-embed-l-v2.0-ko"
    default_embedding_dim: int = 1024

    # Optional API keys for chat providers (loaded if present)
    openai_api_key: str | None = None
    anthropic_api_key: str | None = None


def get_settings() -> Settings:
    """Factory used by FastAPI dependency injection."""
    return Settings()
