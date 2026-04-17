"""m1 knowledge base and documents

Revision ID: m1_001
Revises: d8d1352b2a1f
Create Date: 2026-04-09
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "m1_001"
down_revision = "d8d1352b2a1f"
branch_labels = None
depends_on = None

document_status = postgresql.ENUM(
    "pending", "processing", "done", "failed", name="document_status", create_type=False
)


def upgrade() -> None:
    document_status.create(op.get_bind(), checkfirst=True)

    op.create_table(
        "knowledge_bases",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("name", sa.String(200), nullable=False, unique=True),
        sa.Column("description", sa.Text(), nullable=False, server_default=""),
        sa.Column("embedding_provider", sa.String(50), nullable=False),
        sa.Column("embedding_model", sa.String(500), nullable=False),
        sa.Column("embedding_dim", sa.Integer(), nullable=False),
        sa.Column("qdrant_collection", sa.String(200), nullable=False, unique=True),
        sa.Column("chunk_size", sa.Integer(), nullable=False, server_default="1000"),
        sa.Column("chunk_overlap", sa.Integer(), nullable=False, server_default="200"),
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

    op.create_table(
        "documents",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "knowledge_base_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("knowledge_bases.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
        sa.Column("filename", sa.String(500), nullable=False),
        sa.Column("file_size", sa.BigInteger(), nullable=False),
        sa.Column("file_type", sa.String(20), nullable=False),
        sa.Column("storage_path", sa.String(1000), nullable=False),
        sa.Column(
            "status",
            document_status,
            nullable=False,
            server_default="pending",
            index=True,
        ),
        sa.Column("error", sa.Text(), nullable=True),
        sa.Column("chunk_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
    )


def downgrade() -> None:
    op.drop_table("documents")
    op.drop_table("knowledge_bases")
    document_status.drop(op.get_bind(), checkfirst=True)
