from __future__ import annotations

import pytest
from httpx import ASGITransport, AsyncClient

from app.main import create_app
from app.services.knowledge.bootstrap import get_orchestrator


async def _setup_app():
    app = create_app()
    from app.core.db import get_engine
    from app.models.base import Base

    async with get_engine().begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    return app


@pytest.mark.asyncio
async def test_upload_creates_pending_doc_and_schedules_ingestion(
    tmp_path, monkeypatch
) -> None:
    monkeypatch.setenv("AGENTBUILDER_UPLOADS_DIR", str(tmp_path))
    app = await _setup_app()

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://t"
    ) as c:
        r = await c.post(
            "/knowledge",
            json={
                "name": "up1",
                "embedding_provider": "fastembed",
                "embedding_model": "BAAI/bge-small-en-v1.5",
                "embedding_dim": 384,
            },
        )
        kb_id = r.json()["id"]

        files = {"file": ("hi.txt", b"hello world " * 40, "text/plain")}
        r = await c.post(f"/knowledge/{kb_id}/documents", files=files)
        assert r.status_code == 202, r.text
        doc = r.json()
        assert doc["filename"] == "hi.txt"
        assert doc["status"] == "pending"

        await get_orchestrator().wait_idle()

        r = await c.get(f"/knowledge/{kb_id}/documents")
        docs = r.json()
        assert len(docs) == 1
        assert docs[0]["status"] in {"done", "failed"}
