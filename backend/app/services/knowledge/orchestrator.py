from __future__ import annotations

import asyncio
import logging
import uuid
from collections.abc import Callable
from contextlib import AbstractAsyncContextManager
from pathlib import Path
from typing import Any, Protocol

from app.models.knowledge import DocumentStatus, KnowledgeBase
from app.repositories.knowledge import KnowledgeRepository
from app.services.knowledge.ingestion import IngestionContext, run_ingestion
from app.services.knowledge.parsers import get_parser_for
from app.services.knowledge.progress import ProgressEvent, progress_bus

_log = logging.getLogger(__name__)


class _Store(Protocol):
    async def upsert(self, name: str, *, points: list[dict[str, Any]]) -> None: ...

    async def delete_by_document(self, name: str, *, document_id: str) -> None: ...


SessionFactory = Callable[[], AbstractAsyncContextManager[Any]]
EmbedderFactory = Callable[[KnowledgeBase], Any]


class IngestionOrchestrator:
    def __init__(
        self,
        *,
        sessionmaker: SessionFactory,
        embedder_factory: EmbedderFactory,
        store: _Store,
        max_concurrency: int = 2,
    ) -> None:
        self._sessionmaker = sessionmaker
        self._embedder_factory = embedder_factory
        self._store = store
        self._sem = asyncio.Semaphore(max_concurrency)
        self._tasks: set[asyncio.Task[None]] = set()

    async def enqueue(self, *, kb_id: uuid.UUID, document_id: uuid.UUID) -> None:
        task = asyncio.create_task(self._run_one(kb_id, document_id))
        self._tasks.add(task)
        task.add_done_callback(self._tasks.discard)

    async def wait_idle(self) -> None:
        if self._tasks:
            await asyncio.gather(*self._tasks, return_exceptions=True)

    async def _run_one(self, kb_id: uuid.UUID, document_id: uuid.UUID) -> None:
        async with self._sem:
            try:
                await self._execute(kb_id, document_id)
            except Exception as exc:  # noqa: BLE001
                _log.exception("ingestion failed for %s", document_id)
                await self._fail(kb_id, document_id, str(exc))

    async def _execute(self, kb_id: uuid.UUID, document_id: uuid.UUID) -> None:
        # Phase 1 — load from DB, mark processing
        async with self._sessionmaker() as session:
            repo = KnowledgeRepository(session)
            kb = await repo.get_kb(kb_id)
            doc = await repo.get_document(document_id)
            if kb is None or doc is None:
                raise RuntimeError("kb or doc missing")
            await repo.set_document_status(document_id, status=DocumentStatus.PROCESSING)
            snapshot = (
                kb.qdrant_collection,
                kb.chunk_size,
                kb.chunk_overlap,
                Path(doc.storage_path),
            )

        collection, chunk_size, chunk_overlap, file_path = snapshot

        # Phase 2 — heavy work outside DB session
        embedder = self._embedder_factory(kb)
        parser = get_parser_for(file_path)

        def _progress(done: int, total: int) -> None:
            asyncio.ensure_future(
                progress_bus.publish(
                    ProgressEvent(
                        kb_id=kb_id,
                        document_id=document_id,
                        status="processing",
                        chunks_done=done,
                        chunks_total=total,
                    )
                )
            )

        ctx = IngestionContext(
            kb_id=kb_id,
            document_id=document_id,
            collection_name=collection,
            file_path=file_path,
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap,
            parser=parser,
            embedder=embedder,
            store=self._store,
            on_progress=_progress,
        )
        chunk_count = await run_ingestion(ctx)

        # Phase 3 — mark done
        async with self._sessionmaker() as session:
            repo = KnowledgeRepository(session)
            await repo.set_document_status(
                document_id, status=DocumentStatus.DONE, chunk_count=chunk_count
            )

        await progress_bus.publish(
            ProgressEvent(
                kb_id=kb_id,
                document_id=document_id,
                status="done",
                chunks_done=chunk_count,
                chunks_total=chunk_count,
            )
        )

    async def _fail(self, kb_id: uuid.UUID, document_id: uuid.UUID, msg: str) -> None:
        try:
            async with self._sessionmaker() as session:
                repo = KnowledgeRepository(session)
                await repo.set_document_status(
                    document_id, status=DocumentStatus.FAILED, error=msg
                )
        except Exception:  # noqa: BLE001
            _log.exception("failed to record failure for %s", document_id)
        await progress_bus.publish(
            ProgressEvent(
                kb_id=kb_id,
                document_id=document_id,
                status="failed",
                error=msg,
            )
        )
