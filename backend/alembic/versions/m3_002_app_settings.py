"""m3_002 create app_settings table

Revision ID: m3_002
Revises: m3_001
Create Date: 2026-04-10
"""
from __future__ import annotations

import sqlalchemy as sa

from alembic import op

revision = "m3_002"
down_revision = "m3_001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "app_settings",
        sa.Column("key", sa.String(100), primary_key=True),
        sa.Column("value", sa.Text(), nullable=False, server_default=""),
        sa.Column("description", sa.Text(), nullable=False, server_default=""),
        sa.Column(
            "category", sa.String(50), nullable=False, server_default="general"
        ),
        sa.Column("is_secret", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
    )
    op.create_index("ix_app_settings_category", "app_settings", ["category"])

    # Seed default keys so the UI can show them immediately
    op.execute(
        """
        INSERT INTO app_settings (key, value, description, category, is_secret) VALUES
        ('OPENAI_API_KEY', '', 'OpenAI API Key', 'api_keys', true),
        ('ANTHROPIC_API_KEY', '', 'Anthropic API Key', 'api_keys', true),
        ('VLLM_BASE_URL', 'http://localhost:8080/v1', 'vLLM OpenAI-compatible endpoint', 'endpoints', false)
        """
    )


def downgrade() -> None:
    op.drop_table("app_settings")
