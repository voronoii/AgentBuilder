from __future__ import annotations

from fastapi.testclient import TestClient

from app.main import create_app


def test_request_id_generated_when_missing() -> None:
    client = TestClient(create_app())
    resp = client.get("/health")
    assert "x-request-id" in resp.headers
    assert len(resp.headers["x-request-id"]) >= 32


def test_request_id_preserved_when_supplied() -> None:
    client = TestClient(create_app())
    resp = client.get("/health", headers={"X-Request-ID": "caller-supplied-123"})
    assert resp.headers["x-request-id"] == "caller-supplied-123"
