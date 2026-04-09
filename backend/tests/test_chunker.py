from __future__ import annotations

from app.services.knowledge.chunker import Chunk, chunk_text


def test_chunk_text_respects_size_and_overlap() -> None:
    text = "가나다라마바사아자차카타파하. " * 200
    chunks = chunk_text(text, chunk_size=200, chunk_overlap=40)
    assert len(chunks) > 1
    for c in chunks:
        assert isinstance(c, Chunk)


def test_empty_text_returns_empty_list() -> None:
    assert chunk_text("", chunk_size=100, chunk_overlap=10) == []
