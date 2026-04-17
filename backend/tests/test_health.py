from __future__ import annotations

import pytest
from httpx import ASGITransport, AsyncClient

from app.main import create_app


@pytest.fixture
async def client():
    app = create_app()
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


async def test_health_returns_ok(client: AsyncClient):
    resp = await client.get("/health")
    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "ok"
    assert body["app"] == "AgentBuilder"
    assert "version" in body
    # Version should come from package metadata, not a hardcoded string
    assert body["version"] != ""


async def test_api_v1_prefix_not_mounted(client: AsyncClient):
    """API versioning is intentionally deferred — see spec §11.1."""
    resp = await client.get("/api/v1/health")
    assert resp.status_code == 404
