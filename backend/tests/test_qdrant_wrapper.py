from __future__ import annotations

import os
import uuid

import pytest

from app.services.knowledge.qdrant import QdrantStore


def _qdrant_url() -> str:
    return os.environ.get("AGENTBUILDER_QDRANT_URL", "http://localhost:26333")


@pytest.mark.asyncio
async def test_qdrant_roundtrip() -> None:
    url = _qdrant_url()
    try:
        store = QdrantStore(url=url)
        await store.ping()
    except Exception:
        pytest.skip("qdrant not reachable")
    name = f"kb_test_{uuid.uuid4().hex[:8]}"
    try:
        await store.create_collection(name, dimension=4)
        await store.upsert(
            name,
            points=[
                {"id": 1, "vector": [0.1, 0.2, 0.3, 0.4], "payload": {"text": "a"}},
                {"id": 2, "vector": [0.9, 0.8, 0.7, 0.6], "payload": {"text": "b"}},
            ],
        )
        hits = await store.search(name, query=[0.1, 0.2, 0.3, 0.4], top_k=1)
        assert len(hits) == 1
        assert hits[0]["payload"]["text"] == "a"
    finally:
        await store.delete_collection(name)
