"""m2_005 mcp: add oauth_resource for RFC 8707 audience binding

Revision ID: m2_005
Revises: m2_004
Create Date: 2026-05-07
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "m2_005"
down_revision = "m2_004"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("mcp_servers", sa.Column("oauth_resource", sa.Text(), nullable=True))


def downgrade() -> None:
    op.drop_column("mcp_servers", "oauth_resource")
