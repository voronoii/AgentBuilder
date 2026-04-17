from __future__ import annotations

from fastapi.testclient import TestClient

from app.core.errors import AppError, ErrorCode
from app.main import create_app


def test_app_error_is_serialized_as_envelope() -> None:
    app = create_app()

    @app.get("/__boom")
    async def boom() -> None:
        raise AppError(
            status_code=404,
            code=ErrorCode.KNOWLEDGE_NOT_FOUND,
            detail="knowledge base missing",
        )

    client = TestClient(app)
    resp = client.get("/__boom")
    assert resp.status_code == 404
    body = resp.json()
    assert body["detail"] == "knowledge base missing"
    assert body["code"] == "KNOWLEDGE_NOT_FOUND"
    assert "request_id" in body and len(body["request_id"]) > 0
    assert resp.headers["x-request-id"] == body["request_id"]


def test_validation_error_is_repackaged() -> None:
    from pydantic import BaseModel

    app = create_app()

    class Body(BaseModel):
        name: str

    @app.post("/__validate")
    async def v(body: Body) -> dict[str, str]:
        return {"name": body.name}

    client = TestClient(app)
    resp = client.post("/__validate", json={})
    assert resp.status_code == 422
    body = resp.json()
    assert body["code"] == "VALIDATION_FAILED"
    assert "request_id" in body
