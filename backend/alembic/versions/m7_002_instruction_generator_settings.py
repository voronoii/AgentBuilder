"""m7_002 seed instruction generator default provider/model

Revision ID: m7_002
Revises: m7_001
Create Date: 2026-05-09
"""
from __future__ import annotations

from alembic import op

revision = "m7_002"
down_revision = "m7_001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        """
        INSERT INTO app_settings (key, value, description, category, is_secret) VALUES
        ('INSTRUCTION_GENERATOR_PROVIDER', 'openrouter',
         'AI 지시문 생성에 사용할 기본 Provider',
         'prompt_generation', false),
        ('INSTRUCTION_GENERATOR_MODEL', 'openai/gpt-5.4',
         'AI 지시문 생성에 사용할 기본 Model',
         'prompt_generation', false)
        ON CONFLICT (key) DO NOTHING
        """
    )


def downgrade() -> None:
    op.execute(
        """
        DELETE FROM app_settings
        WHERE key IN ('INSTRUCTION_GENERATOR_PROVIDER', 'INSTRUCTION_GENERATOR_MODEL')
        """
    )
