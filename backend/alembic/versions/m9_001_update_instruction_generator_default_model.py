"""m9_001 change INSTRUCTION_GENERATOR_MODEL default from gpt-5.4 to gpt-5.2

The previously seeded `openai/gpt-5.4` was rejected by OpenRouter at runtime
("model not found"). Switching the fallback to `openai/gpt-5.2`, which is the
OpenAI-family model verified during M4 and known to be served by OpenRouter.

Note: only updates rows whose value is still the original default. Users who
manually changed the model via the Settings UI keep their choice.

Revision ID: m9_001
Revises: m8_001
Create Date: 2026-05-09
"""
from __future__ import annotations

from alembic import op

revision = "m9_001"
down_revision = "m8_001"
branch_labels = None
depends_on = None


_OLD_MODEL = "openai/gpt-5.4"
_NEW_MODEL = "openai/gpt-5.2"


def upgrade() -> None:
    op.execute(
        f"""
        UPDATE app_settings
        SET value = '{_NEW_MODEL}'
        WHERE key = 'INSTRUCTION_GENERATOR_MODEL' AND value = '{_OLD_MODEL}'
        """
    )


def downgrade() -> None:
    op.execute(
        f"""
        UPDATE app_settings
        SET value = '{_OLD_MODEL}'
        WHERE key = 'INSTRUCTION_GENERATOR_MODEL' AND value = '{_NEW_MODEL}'
        """
    )
