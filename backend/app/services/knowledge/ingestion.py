from __future__ import annotations

import uuid
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Protocol

from app.services.knowledge.chunker import chunk_text
from app.services.knowledge.parsers.base import Parser


class _Embedder(Protocol):
    dimension: int

    async def embed_texts(self, texts: list[str]) -> list[list[float]]: ...


class _Store(Protocol):
    async def upsert(self, name: str, *, points: list[dict[str, Any]]) -> None: ...

    async def delete_by_document(self, name: str, *, document_id: str) -> None: ...


ProgressFn = Callable[[int, int], None]


@dataclass
class IngestionContext:
    kb_id: uuid.UUID
    document_id: uuid.UUID
    collection_name: str
    file_path: Path
    chunk_size: int
    chunk_overlap: int
    parser: Parser
    embedder: _Embedder
    store: _Store
    on_progress: ProgressFn
    batch_size: int = 32


async def run_ingestion(ctx: IngestionContext) -> int:
    """Parse -> chunk -> embed in batches -> upsert. Idempotent: clears prior
    points for this document_id before writing new ones.

    Returns the number of chunks upserted.
    """
    parsed = await ctx.parser.parse(ctx.file_path)
    chunks = chunk_text(
        parsed.text,
        chunk_size=ctx.chunk_size,
        chunk_overlap=ctx.chunk_overlap,
    )
    total = len(chunks)
    if total == 0:
        ctx.on_progress(0, 0)
        return 0

    await ctx.store.delete_by_document(
        ctx.collection_name, document_id=str(ctx.document_id)
    )

    done = 0
    for start in range(0, total, ctx.batch_size):
        batch = chunks[start : start + ctx.batch_size]
        vectors = await ctx.embedder.embed_texts([c.text for c in batch])
        points = [
            {
                "id": _point_id(ctx.document_id, c.index),
                "vector": v,
                "payload": {
                    "document_id": str(ctx.document_id),
                    "kb_id": str(ctx.kb_id),
                    "chunk_index": c.index,
                    "text": c.text,
                    "filename": parsed.metadata.get("filename", ""),
                },
            }
            for c, v in zip(batch, vectors, strict=True)
        ]
        await ctx.store.upsert(ctx.collection_name, points=points)
        done += len(batch)
        ctx.on_progress(done, total)

    return total


def _point_id(document_id: uuid.UUID, chunk_index: int) -> int:
    """Deterministic 63-bit point id so re-ingestion overwrites same rows."""
    h = hash((str(document_id), chunk_index))
    return h & ((1 << 63) - 1)
