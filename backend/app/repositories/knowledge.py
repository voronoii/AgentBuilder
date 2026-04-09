from __future__ import annotations

import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.knowledge import Document, DocumentStatus, KnowledgeBase
from app.schemas.knowledge import KnowledgeBaseCreate


class KnowledgeRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create_kb(
        self, payload: KnowledgeBaseCreate, *, qdrant_collection: str
    ) -> KnowledgeBase:
        kb = KnowledgeBase(
            name=payload.name,
            description=payload.description,
            embedding_provider=payload.embedding_provider,
            embedding_model=payload.embedding_model,
            embedding_dim=payload.embedding_dim,
            qdrant_collection=qdrant_collection,
            chunk_size=payload.chunk_size,
            chunk_overlap=payload.chunk_overlap,
        )
        self._session.add(kb)
        await self._session.flush()
        return kb

    async def list_kbs(self) -> list[KnowledgeBase]:
        result = await self._session.execute(
            select(KnowledgeBase).order_by(KnowledgeBase.created_at.desc())
        )
        return list(result.scalars().all())

    async def get_kb(self, kb_id: uuid.UUID) -> KnowledgeBase | None:
        return await self._session.get(KnowledgeBase, kb_id)

    async def delete_kb(self, kb_id: uuid.UUID) -> None:
        kb = await self.get_kb(kb_id)
        if kb is not None:
            await self._session.delete(kb)
            await self._session.flush()

    async def create_document(
        self, *, kb_id: uuid.UUID, filename: str, file_size: int, file_type: str, storage_path: str
    ) -> Document:
        doc = Document(
            knowledge_base_id=kb_id,
            filename=filename,
            file_size=file_size,
            file_type=file_type,
            storage_path=storage_path,
            status=DocumentStatus.PENDING,
        )
        self._session.add(doc)
        await self._session.flush()
        return doc

    async def list_documents(self, kb_id: uuid.UUID) -> list[Document]:
        result = await self._session.execute(
            select(Document)
            .where(Document.knowledge_base_id == kb_id)
            .order_by(Document.created_at.desc())
        )
        return list(result.scalars().all())

    async def get_document(self, doc_id: uuid.UUID) -> Document | None:
        return await self._session.get(Document, doc_id)

    async def set_document_status(
        self,
        doc_id: uuid.UUID,
        *,
        status: DocumentStatus,
        error: str | None = None,
        chunk_count: int | None = None,
    ) -> None:
        doc = await self.get_document(doc_id)
        if doc is None:
            return
        doc.status = status
        if error is not None:
            doc.error = error
        if chunk_count is not None:
            doc.chunk_count = chunk_count
        await self._session.flush()

    async def mark_stale_processing_failed(self) -> int:
        result = await self._session.execute(
            select(Document).where(Document.status == DocumentStatus.PROCESSING)
        )
        docs = list(result.scalars().all())
        for d in docs:
            d.status = DocumentStatus.FAILED
            d.error = "interrupted by server restart"
        await self._session.flush()
        return len(docs)
