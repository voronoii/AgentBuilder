"""m2_003 mcp_transport: re-add stdio (support all 3 transports)

Revision ID: m2_003
Revises: m2_002
Create Date: 2026-04-10
"""
from __future__ import annotations

from alembic import op

revision = "m2_003"
down_revision = "m2_002"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Recreate enum with all 3 values
    op.execute(
        "ALTER TABLE mcp_servers "
        "ALTER COLUMN transport TYPE text "
        "USING transport::text"
    )
    op.execute("DROP TYPE mcp_transport")
    op.execute("CREATE TYPE mcp_transport AS ENUM ('stdio', 'http_sse', 'streamable_http')")
    op.execute(
        "ALTER TABLE mcp_servers "
        "ALTER COLUMN transport TYPE mcp_transport "
        "USING transport::mcp_transport"
    )


def downgrade() -> None:
    # Remove stdio rows, then recreate enum without stdio
    op.execute("DELETE FROM mcp_servers WHERE transport = 'stdio'")
    op.execute(
        "ALTER TABLE mcp_servers "
        "ALTER COLUMN transport TYPE text "
        "USING transport::text"
    )
    op.execute("DROP TYPE mcp_transport")
    op.execute("CREATE TYPE mcp_transport AS ENUM ('http_sse', 'streamable_http')")
    op.execute(
        "ALTER TABLE mcp_servers "
        "ALTER COLUMN transport TYPE mcp_transport "
        "USING transport::mcp_transport"
    )
