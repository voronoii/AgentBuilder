from __future__ import annotations

import pytest

from app.services.providers.embedding.fastembed_provider import FastembedProvider


@pytest.mark.asyncio
async def test_fastembed_embeds_and_reports_dim() -> None:
    provider = FastembedProvider(model_name="BAAI/bge-small-en-v1.5")
    vectors = await provider.embed_texts(["hello", "world"])
    assert len(vectors) == 2
    assert len(vectors[0]) == provider.dimension
    assert provider.dimension > 0
