"""m2 mcp servers

Revision ID: m2_001
Revises: m1_001
Create Date: 2026-04-10
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "m2_001"
down_revision = "m1_001"
branch_labels = None
depends_on = None

mcp_transport = postgresql.ENUM(
    "stdio", "http_sse", name="mcp_transport", create_type=False
)


def upgrade() -> None:
    mcp_transport.create(op.get_bind(), checkfirst=True)

    op.create_table(
        "mcp_servers",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("name", sa.String(200), nullable=False, unique=True),
        sa.Column("description", sa.Text(), nullable=False, server_default=""),
        sa.Column("transport", mcp_transport, nullable=False),
        sa.Column("config", postgresql.JSON(), nullable=False, server_default="{}"),
        sa.Column("env_vars", postgresql.JSON(), nullable=False, server_default="{}"),
        sa.Column("enabled", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column(
            "discovered_tools",
            postgresql.JSON(),
            nullable=False,
            server_default="[]",
        ),
        sa.Column(
            "last_discovered_at",
            sa.DateTime(timezone=True),
            nullable=True,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
    )


def downgrade() -> None:
    op.drop_table("mcp_servers")
    mcp_transport.drop(op.get_bind(), checkfirst=True)
