"""m2_002 mcp_transport: add streamable_http, drop stdio

Revision ID: m2_002
Revises: m2_001
Create Date: 2026-04-10
"""
from __future__ import annotations

from alembic import op

revision = "m2_002"
down_revision = "m2_001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Add new value to the existing ENUM type
    op.execute("ALTER TYPE mcp_transport ADD VALUE IF NOT EXISTS 'streamable_http'")

    # Remove rows that use 'stdio' (none expected in production at this stage)
    op.execute("DELETE FROM mcp_servers WHERE transport = 'stdio'")

    # Rename 'stdio' out of the enum is not directly supported in Postgres.
    # Instead we create a new enum without 'stdio', swap the column, then drop old.
    op.execute("ALTER TYPE mcp_transport RENAME TO mcp_transport_old")
    op.execute("CREATE TYPE mcp_transport AS ENUM ('http_sse', 'streamable_http')")
    op.execute(
        "ALTER TABLE mcp_servers "
        "ALTER COLUMN transport TYPE mcp_transport "
        "USING transport::text::mcp_transport"
    )
    op.execute("DROP TYPE mcp_transport_old")


def downgrade() -> None:
    # Restore 'stdio', remove 'streamable_http'
    op.execute("DELETE FROM mcp_servers WHERE transport = 'streamable_http'")
    op.execute("ALTER TYPE mcp_transport RENAME TO mcp_transport_old")
    op.execute("CREATE TYPE mcp_transport AS ENUM ('stdio', 'http_sse')")
    op.execute(
        "ALTER TABLE mcp_servers "
        "ALTER COLUMN transport TYPE mcp_transport "
        "USING transport::text::mcp_transport"
    )
    op.execute("DROP TYPE mcp_transport_old")
