from __future__ import annotations

import pytest
from httpx import ASGITransport, AsyncClient

from app.main import create_app


async def _setup_app():
    """Create app and ensure schema exists (since startup events don't fire with ASGITransport)."""
    app = create_app()
    from app.core.db import get_engine
    from app.models.base import Base

    async with get_engine().begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    return app


@pytest.mark.asyncio
async def test_create_list_get_delete_kb() -> None:
    app = await _setup_app()
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://t") as c:
        r = await c.post(
            "/knowledge",
            json={
                "name": "docs1",
                "description": "",
                "embedding_provider": "fastembed",
                "embedding_model": "BAAI/bge-small-en-v1.5",
                "embedding_dim": 384,
            },
        )
        assert r.status_code == 201, r.text
        kb_id = r.json()["id"]

        r = await c.get("/knowledge")
        assert r.status_code == 200
        assert any(item["id"] == kb_id for item in r.json())

        r = await c.get(f"/knowledge/{kb_id}")
        assert r.status_code == 200

        r = await c.delete(f"/knowledge/{kb_id}")
        assert r.status_code == 204

        r = await c.get(f"/knowledge/{kb_id}")
        assert r.status_code == 404
        assert r.json()["code"] == "KNOWLEDGE_NOT_FOUND"
