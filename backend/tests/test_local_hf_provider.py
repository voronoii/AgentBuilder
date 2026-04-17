from __future__ import annotations

import os
from pathlib import Path

import pytest

MODEL_PATH = os.environ.get(
    "AGENTBUILDER_DEFAULT_EMBEDDING_MODEL_PATH",
    "/DATA3/users/mj/hf_models/snowflake-arctic-embed-l-v2.0-ko",
)
pytestmark = pytest.mark.gpu


@pytest.mark.asyncio
async def test_local_hf_provider_embeds_korean_text() -> None:
    if not Path(MODEL_PATH).exists():
        pytest.skip(f"model path missing: {MODEL_PATH}")
    from app.services.providers.embedding.local_hf import LocalHfProvider

    provider = LocalHfProvider(model_path=MODEL_PATH)
    vectors = await provider.embed_texts(["안녕하세요, 에이전트빌더입니다."])
    assert len(vectors) == 1
    assert len(vectors[0]) == provider.dimension
    assert provider.dimension == 1024
