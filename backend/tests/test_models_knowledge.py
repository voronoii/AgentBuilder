from __future__ import annotations

import uuid

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.knowledge import Document, DocumentStatus, KnowledgeBase


@pytest.mark.asyncio
async def test_create_kb_with_document(db_session: AsyncSession) -> None:
    kb = KnowledgeBase(
        name="docs",
        description="",
        embedding_provider="local_hf",
        embedding_model="/models/snowflake-arctic-embed-l-v2.0-ko",
        embedding_dim=1024,
        qdrant_collection="kb_docs",
        chunk_size=1000,
        chunk_overlap=200,
    )
    db_session.add(kb)
    await db_session.flush()

    doc = Document(
        knowledge_base_id=kb.id,
        filename="a.txt",
        file_size=12,
        file_type="txt",
        status=DocumentStatus.PENDING,
        storage_path="/app/uploads/a.txt",
    )
    db_session.add(doc)
    await db_session.flush()

    assert isinstance(kb.id, uuid.UUID)
    assert doc.status == DocumentStatus.PENDING
    assert doc.knowledge_base_id == kb.id
