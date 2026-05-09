"""m2_004 mcp: oauth columns for streamable_http servers

Revision ID: m2_004
Revises: m7_001
Create Date: 2026-05-07
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "m2_004"
down_revision = "m7_001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("CREATE TYPE mcp_auth_type AS ENUM ('none', 'oauth')")
    op.add_column(
        "mcp_servers",
        sa.Column(
            "auth_type",
            sa.Enum("none", "oauth", name="mcp_auth_type", create_type=False),
            nullable=False,
            server_default="none",
        ),
    )
    op.add_column("mcp_servers", sa.Column("oauth_client_id", sa.String(length=500), nullable=True))
    op.add_column("mcp_servers", sa.Column("oauth_client_secret", sa.Text(), nullable=True))
    op.add_column("mcp_servers", sa.Column("oauth_authorize_url", sa.Text(), nullable=True))
    op.add_column("mcp_servers", sa.Column("oauth_token_url", sa.Text(), nullable=True))
    op.add_column("mcp_servers", sa.Column("oauth_scopes", sa.Text(), nullable=True))
    op.add_column("mcp_servers", sa.Column("oauth_access_token", sa.Text(), nullable=True))
    op.add_column("mcp_servers", sa.Column("oauth_refresh_token", sa.Text(), nullable=True))
    op.add_column(
        "mcp_servers",
        sa.Column("oauth_token_expires_at", sa.DateTime(timezone=True), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("mcp_servers", "oauth_token_expires_at")
    op.drop_column("mcp_servers", "oauth_refresh_token")
    op.drop_column("mcp_servers", "oauth_access_token")
    op.drop_column("mcp_servers", "oauth_scopes")
    op.drop_column("mcp_servers", "oauth_token_url")
    op.drop_column("mcp_servers", "oauth_authorize_url")
    op.drop_column("mcp_servers", "oauth_client_secret")
    op.drop_column("mcp_servers", "oauth_client_id")
    op.drop_column("mcp_servers", "auth_type")
    op.execute("DROP TYPE mcp_auth_type")
