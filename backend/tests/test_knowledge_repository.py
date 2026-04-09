from __future__ import annotations

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.repositories.knowledge import KnowledgeRepository
from app.schemas.knowledge import KnowledgeBaseCreate


@pytest.mark.asyncio
async def test_create_and_list_kb(db_session: AsyncSession) -> None:
    repo = KnowledgeRepository(db_session)
    created = await repo.create_kb(
        KnowledgeBaseCreate(
            name="mydocs",
            description="",
            embedding_provider="fastembed",
            embedding_model="intfloat/multilingual-e5-small",
            embedding_dim=384,
            chunk_size=1000,
            chunk_overlap=200,
        ),
        qdrant_collection="kb_mydocs",
    )
    assert created.id is not None
    listed = await repo.list_kbs()
    assert len(listed) == 1 and listed[0].name == "mydocs"
    fetched = await repo.get_kb(created.id)
    assert fetched is not None
    await repo.delete_kb(created.id)
    assert await repo.get_kb(created.id) is None
