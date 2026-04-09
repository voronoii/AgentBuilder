from __future__ import annotations

import pytest

from app.core.config import APP_VERSION, Settings


def test_settings_defaults_when_no_env():
    settings = Settings()
    assert settings.app_name == "AgentBuilder"
    assert settings.api_host == "0.0.0.0"
    assert settings.api_port == 8000
    assert settings.database_url.startswith("postgresql+asyncpg://")
    assert settings.qdrant_url == "http://qdrant:6333"


def test_settings_reads_env_vars(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("AGENTBUILDER_API_PORT", "9001")
    monkeypatch.setenv(
        "AGENTBUILDER_DATABASE_URL",
        "postgresql+asyncpg://u:p@db:5432/x",
    )
    settings = Settings()
    assert settings.api_port == 9001
    assert settings.database_url == "postgresql+asyncpg://u:p@db:5432/x"


def test_settings_default_embedding_path():
    settings = Settings()
    assert settings.default_embedding_provider == "local_hf"
    assert settings.default_embedding_model_path == (
        "/models/snowflake-arctic-embed-l-v2.0-ko"
    )


def test_app_version_resolved_from_metadata():
    """APP_VERSION is read from installed package metadata (pyproject.toml)."""
    # When running tests in an editable install, version should match pyproject
    assert APP_VERSION
    assert APP_VERSION != "0.0.0"  # fallback only fires if package missing
    # Semantic version shape: at least one dot
    assert "." in APP_VERSION
