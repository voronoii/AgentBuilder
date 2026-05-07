"""m7_001 create hook_executions table

Revision ID: m7_001
Revises: m6_001
Create Date: 2026-04-20
"""
from __future__ import annotations

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision = "m7_001"
down_revision = "m6_001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "hook_executions",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("run_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("node_id", sa.String(200), nullable=False),
        sa.Column("hook_type", sa.String(100), nullable=False),
        sa.Column("hook_config", postgresql.JSON(), nullable=False, server_default="{}"),
        sa.Column("attempt", sa.Integer(), nullable=False),
        sa.Column("passed", sa.Boolean(), nullable=False),
        sa.Column("feedback", sa.Text(), nullable=True),
        sa.Column("details", postgresql.JSON(), nullable=True),
        sa.Column("input_tokens", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("output_tokens", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("duration_ms", sa.Integer(), nullable=False, server_default="0"),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
    )
    op.create_index("ix_hook_exec_run_node", "hook_executions", ["run_id", "node_id"])
    op.create_index("ix_hook_exec_type_created", "hook_executions", ["hook_type", "created_at"])


def downgrade() -> None:
    op.drop_index("ix_hook_exec_type_created", table_name="hook_executions")
    op.drop_index("ix_hook_exec_run_node", table_name="hook_executions")
    op.drop_table("hook_executions")
