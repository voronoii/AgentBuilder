from __future__ import annotations
import pytest
from app.core.errors import AppError
from app.services.providers.embedding import get_embedding_provider, register_embedding_provider

class _Dummy:
    dimension = 3
    async def embed_texts(self, texts: list[str]) -> list[list[float]]:
        return [[0.1, 0.2, 0.3] for _ in texts]

def test_register_and_get_provider() -> None:
    register_embedding_provider("dummy", lambda **kw: _Dummy())
    p = get_embedding_provider("dummy")
    assert p.dimension == 3

def test_unknown_provider_raises_app_error() -> None:
    with pytest.raises(AppError):
        get_embedding_provider("nope_does_not_exist")
