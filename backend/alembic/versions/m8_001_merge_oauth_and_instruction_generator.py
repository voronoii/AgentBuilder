"""m8_001 merge oauth (m2_005) and instruction generator (m7_002) heads

Two independent branches sprouted from m7_001 and need to be unified:
- m7_001 → m2_004 → m2_005   (MCP OAuth schema additions)
- m7_001 → m7_002             (instruction generator app_settings seed)

This is a no-op merge — the two branches touch unrelated tables (mcp_servers
columns vs app_settings rows) so there is no data/schema conflict to resolve.

Revision ID: m8_001
Revises: m2_005, m7_002
Create Date: 2026-05-09
"""
from __future__ import annotations

revision = "m8_001"
down_revision = ("m2_005", "m7_002")
branch_labels = None
depends_on = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
