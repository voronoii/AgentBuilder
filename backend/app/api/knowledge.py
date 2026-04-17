from __future__ import annotations

import json
import logging
import re
import shutil
import uuid
from pathlib import Path
from typing import Annotated

from fastapi import APIRouter, Depends, File, UploadFile, status
from fastapi.responses import Response
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from sse_starlette.sse import EventSourceResponse

from app.core.config import get_settings
from app.core.db import get_session
from app.core.errors import AppError, ErrorCode
from app.models.knowledge import KnowledgeBase
from app.repositories.knowledge import KnowledgeRepository
from app.schemas.knowledge import (
    DocumentRead,
    KnowledgeBaseCreate,
    KnowledgeBaseRead,
    SearchHit,
    SearchRequest,
    SearchResponse,
)
from app.services.knowledge.bootstrap import get_orchestrator, get_store
from app.services.knowledge.parsers import SUPPORTED_EXTENSIONS
from app.services.knowledge.progress import progress_bus
from app.services.providers.embedding import get_embedding_provider

_log = logging.getLogger(__name__)

router = APIRouter(prefix="/knowledge", tags=["knowledge"])

_SLUG = re.compile(r"[^a-z0-9]+")


def _slugify(name: str) -> str:
    return _SLUG.sub("_", name.lower()).strip("_") or "kb"


# ---------- Config ----------


@router.get("/config")
async def get_knowledge_config() -> dict:
    settings = get_settings()
    return {
        "supported_extensions": sorted(SUPPORTED_EXTENSIONS),
        "max_upload_mb": settings.max_upload_mb,
    }


# ---------- CRUD ----------


@router.post("", response_model=KnowledgeBaseRead, status_code=status.HTTP_201_CREATED)
async def create_kb(
    payload: KnowledgeBaseCreate,
    session: Annotated[AsyncSession, Depends(get_session)],
) -> KnowledgeBase:
    settings = get_settings()
    repo = KnowledgeRepository(session)
    collection = f"{settings.qdrant_collection_prefix}{_slugify(payload.name)}"
    try:
        kb = await repo.create_kb(payload, qdrant_collection=collection)
        await session.commit()
    except IntegrityError:
        raise AppError(
            status_code=409,
            code=ErrorCode.KNOWLEDGE_DUPLICATE_NAME,
            detail=f"'{payload.name}' 이름의 지식베이스가 이미 존재합니다.",
        )
    return kb


@router.get("", response_model=list[KnowledgeBaseRead])
async def list_kbs(
    session: Annotated[AsyncSession, Depends(get_session)],
) -> list[KnowledgeBase]:
    return await KnowledgeRepository(session).list_kbs()


@router.get("/{kb_id}", response_model=KnowledgeBaseRead)
async def get_kb(
    kb_id: uuid.UUID,
    session: Annotated[AsyncSession, Depends(get_session)],
) -> KnowledgeBase:
    kb = await KnowledgeRepository(session).get_kb(kb_id)
    if kb is None:
        raise AppError(
            status_code=404,
            code=ErrorCode.KNOWLEDGE_NOT_FOUND,
            detail="지식베이스를 찾을 수 없습니다.",
        )
    return kb


@router.delete("/{kb_id}", status_code=status.HTTP_204_NO_CONTENT, response_class=Response)
async def delete_kb(
    kb_id: uuid.UUID,
    session: Annotated[AsyncSession, Depends(get_session)],
) -> Response:
    repo = KnowledgeRepository(session)
    kb = await repo.get_kb(kb_id)
    if kb is None:
        raise AppError(status_code=404, code=ErrorCode.KNOWLEDGE_NOT_FOUND, detail="지식베이스를 찾을 수 없습니다.")

    # Clean up Qdrant collection
    try:
        await get_store().delete_collection(kb.qdrant_collection)
    except Exception:
        _log.warning("Failed to delete Qdrant collection %s", kb.qdrant_collection, exc_info=True)

    # Clean up uploaded files
    settings = get_settings()
    uploads_dir = Path(settings.uploads_dir) / str(kb_id)
    shutil.rmtree(uploads_dir, ignore_errors=True)

    # Delete DB rows (KB + documents via cascade)
    await repo.delete_kb(kb_id)
    await session.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)


# ---------- Documents ----------


@router.get("/{kb_id}/documents", response_model=list[DocumentRead])
async def list_documents(
    kb_id: uuid.UUID,
    session: Annotated[AsyncSession, Depends(get_session)],
) -> list:
    return await KnowledgeRepository(session).list_documents(kb_id)


@router.post(
    "/{kb_id}/documents",
    response_model=DocumentRead,
    status_code=status.HTTP_202_ACCEPTED,
)
async def upload_document(
    kb_id: uuid.UUID,
    session: Annotated[AsyncSession, Depends(get_session)],
    file: UploadFile = File(...),
) -> object:
    repo = KnowledgeRepository(session)
    kb = await repo.get_kb(kb_id)
    if kb is None:
        raise AppError(
            status_code=404,
            code=ErrorCode.KNOWLEDGE_NOT_FOUND,
            detail="지식베이스를 찾을 수 없습니다.",
        )

    filename = file.filename or "unnamed"
    ext = filename.rsplit(".", 1)[-1].lower() if "." in filename else ""
    if ext not in SUPPORTED_EXTENSIONS:
        raise AppError(
            status_code=415,
            code=ErrorCode.KNOWLEDGE_UNSUPPORTED_FILE,
            detail=f"지원하지 않는 파일 형식입니다: .{ext}",
        )

    settings = get_settings()
    uploads_dir = Path(settings.uploads_dir) / str(kb_id)
    uploads_dir.mkdir(parents=True, exist_ok=True)
    storage_path = uploads_dir / f"{uuid.uuid4().hex}_{filename}"

    max_bytes = settings.max_upload_mb * 1024 * 1024
    total_bytes = 0
    try:
        with storage_path.open("wb") as fout:
            while True:
                chunk = await file.read(65536)
                if not chunk:
                    break
                total_bytes += len(chunk)
                if total_bytes > max_bytes:
                    fout.close()
                    storage_path.unlink(missing_ok=True)
                    raise AppError(
                        status_code=413,
                        code=ErrorCode.KNOWLEDGE_FILE_TOO_LARGE,
                        detail=f"파일 크기가 최대 업로드 용량({settings.max_upload_mb}MB)을 초과했습니다.",
                    )
                fout.write(chunk)
    except AppError:
        raise
    except Exception:
        storage_path.unlink(missing_ok=True)
        raise

    doc = await repo.create_document(
        kb_id=kb_id,
        filename=filename,
        file_size=total_bytes,
        file_type=ext,
        storage_path=str(storage_path),
    )
    await session.commit()

    await get_orchestrator().enqueue(kb_id=kb_id, document_id=doc.id)
    return doc


@router.delete(
    "/{kb_id}/documents/{doc_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    response_class=Response,
)
async def delete_document(
    kb_id: uuid.UUID,
    doc_id: uuid.UUID,
    session: Annotated[AsyncSession, Depends(get_session)],
) -> Response:
    repo = KnowledgeRepository(session)
    kb = await repo.get_kb(kb_id)
    if kb is None:
        raise AppError(status_code=404, code=ErrorCode.KNOWLEDGE_NOT_FOUND, detail="지식베이스를 찾을 수 없습니다.")

    doc = await repo.delete_document(doc_id)
    if doc is None:
        raise AppError(status_code=404, code=ErrorCode.KNOWLEDGE_NOT_FOUND, detail="문서를 찾을 수 없습니다.")

    # Delete vectors for this document only
    try:
        await get_store().delete_by_document(kb.qdrant_collection, document_id=str(doc_id))
    except Exception:
        _log.warning("Failed to delete vectors for document %s", doc_id, exc_info=True)

    # Delete uploaded file
    if doc.storage_path:
        Path(doc.storage_path).unlink(missing_ok=True)

    await session.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get("/{kb_id}/documents/{doc_id}/chunks")
async def list_document_chunks(
    kb_id: uuid.UUID,
    doc_id: uuid.UUID,
    session: Annotated[AsyncSession, Depends(get_session)],
    limit: int = 3,
) -> dict:
    repo = KnowledgeRepository(session)
    kb = await repo.get_kb(kb_id)
    if kb is None:
        raise AppError(
            status_code=404,
            code=ErrorCode.KNOWLEDGE_NOT_FOUND,
            detail="지식베이스를 찾을 수 없습니다.",
        )
    points = await get_store().scroll_by_document(
        kb.qdrant_collection, document_id=str(doc_id), limit=max(1, min(limit, 10))
    )
    chunks = [
        {
            "chunk_index": int(p["payload"].get("chunk_index", 0)),
            "text": str(p["payload"].get("text", "")),
        }
        for p in points
    ]
    chunks.sort(key=lambda c: c["chunk_index"])
    return {"chunks": chunks}


# ---------- SSE ----------


@router.get("/{kb_id}/ingestion/stream")
async def ingestion_stream(kb_id: uuid.UUID) -> EventSourceResponse:
    async def _events():  # type: ignore[override]
        async for evt in progress_bus.subscribe(kb_id):
            yield {"event": "progress", "data": json.dumps(evt.to_dict())}

    return EventSourceResponse(_events(), ping=15)


# ---------- Search ----------


@router.post("/{kb_id}/search", response_model=SearchResponse)
async def search_kb(
    kb_id: uuid.UUID,
    payload: SearchRequest,
    session: Annotated[AsyncSession, Depends(get_session)],
) -> SearchResponse:
    kb = await KnowledgeRepository(session).get_kb(kb_id)
    if kb is None:
        raise AppError(
            status_code=404,
            code=ErrorCode.KNOWLEDGE_NOT_FOUND,
            detail="지식베이스를 찾을 수 없습니다.",
        )

    if kb.embedding_provider == "local_hf":
        embedder = get_embedding_provider("local_hf", model_path=kb.embedding_model)
    else:
        embedder = get_embedding_provider(kb.embedding_provider, model_name=kb.embedding_model)

    vectors = await embedder.embed_texts([payload.query])
    hits_raw = await get_store().search(
        kb.qdrant_collection,
        query=vectors[0],
        top_k=payload.top_k,
        score_threshold=payload.score_threshold,
    )
    hits = [
        SearchHit(
            score=float(h["score"]),
            text=str(h["payload"].get("text", "")),
            filename=str(h["payload"].get("filename", "")),
            chunk_index=int(h["payload"].get("chunk_index", 0)),
        )
        for h in hits_raw
    ]
    return SearchResponse(hits=hits)
