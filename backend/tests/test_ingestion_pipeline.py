from __future__ import annotations

import uuid
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import pytest

from app.services.knowledge.ingestion import IngestionContext, run_ingestion
from app.services.knowledge.parsers.base import ParsedDocument


class _FakeEmbedder:
    dimension = 3

    async def embed_texts(self, texts: list[str]) -> list[list[float]]:
        return [[float(len(t)), 0.0, 1.0] for t in texts]


@dataclass
class _Recorded:
    collection: str
    point_count: int


class _FakeStore:
    def __init__(self) -> None:
        self.calls: list[_Recorded] = []

    async def upsert(self, name: str, *, points: list[dict[str, Any]]) -> None:
        self.calls.append(_Recorded(collection=name, point_count=len(points)))

    async def delete_by_document(self, name: str, *, document_id: str) -> None:
        pass


class _FakeParser:
    async def parse(self, path: Path) -> ParsedDocument:
        return ParsedDocument(
            text="hello world " * 50, metadata={"filename": path.name}
        )


@pytest.mark.asyncio
async def test_run_ingestion_chunks_embeds_and_upserts(tmp_path: Path) -> None:
    file = tmp_path / "doc.txt"
    file.write_text("placeholder")

    store = _FakeStore()
    events: list[tuple[str, int, int]] = []

    ctx = IngestionContext(
        kb_id=uuid.uuid4(),
        document_id=uuid.uuid4(),
        collection_name="kb_t",
        file_path=file,
        chunk_size=80,
        chunk_overlap=20,
        parser=_FakeParser(),
        embedder=_FakeEmbedder(),
        store=store,
        on_progress=lambda done, total: events.append(("p", done, total)),
    )

    chunks = await run_ingestion(ctx)
    assert chunks > 0
    assert len(store.calls) >= 1
    assert store.calls[0].collection == "kb_t"
    assert events[-1][1] == events[-1][2]  # final done==total
