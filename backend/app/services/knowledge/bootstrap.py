from __future__ import annotations

from contextlib import asynccontextmanager
from typing import Any

from app.core.config import get_settings
from app.core.db import get_sessionmaker
from app.models.knowledge import KnowledgeBase
from app.services.knowledge.orchestrator import IngestionOrchestrator
from app.services.knowledge.qdrant import QdrantStore
from app.services.providers.embedding import get_embedding_provider

_orchestrator: IngestionOrchestrator | None = None
_store_singleton: Any = None


def _embedder_for(kb: KnowledgeBase) -> Any:
    if kb.embedding_provider == "local_hf":
        return get_embedding_provider("local_hf", model_path=kb.embedding_model)
    return get_embedding_provider(kb.embedding_provider, model_name=kb.embedding_model)


class _NoopStore:
    async def upsert(self, *a: Any, **kw: Any) -> None: ...

    async def delete_by_document(self, *a: Any, **kw: Any) -> None: ...

    async def ensure_collection(self, *a: Any, **kw: Any) -> None: ...

    async def search(self, *a: Any, **kw: Any) -> list[dict[str, Any]]:
        return []

    async def scroll_by_document(self, *a: Any, **kw: Any) -> list[dict[str, Any]]:
        return []


def get_store() -> Any:
    global _store_singleton
    if _store_singleton is None:
        try:
            _store_singleton = QdrantStore(url=get_settings().qdrant_url)
        except Exception:
            _store_singleton = _NoopStore()
    return _store_singleton


def build_orchestrator() -> IngestionOrchestrator:
    settings = get_settings()
    store = get_store()
    sm = get_sessionmaker()

    @asynccontextmanager
    async def _session_factory():
        async with sm() as session:
            try:
                yield session
                await session.commit()
            except Exception:
                await session.rollback()
                raise

    return IngestionOrchestrator(
        sessionmaker=_session_factory,
        embedder_factory=_embedder_for,
        store=store,
        max_concurrency=settings.ingestion_max_concurrency,
    )


def get_orchestrator() -> IngestionOrchestrator:
    global _orchestrator
    if _orchestrator is None:
        _orchestrator = build_orchestrator()
    return _orchestrator


def reset_orchestrator() -> None:
    global _orchestrator, _store_singleton
    _orchestrator = None
    _store_singleton = None
