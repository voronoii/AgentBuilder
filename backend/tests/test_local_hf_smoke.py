from __future__ import annotations

import os
from pathlib import Path

import pytest


@pytest.mark.gpu
def test_local_hf_model_directory_is_mounted() -> None:
    """Model path from Settings must exist inside the container/host venv.

    Skipped when the model directory is absent (developer laptop without
    the 8GB model). CI marks `gpu` to run only on the host with the mount.
    """
    model_path = Path(
        os.environ.get(
            "AGENTBUILDER_DEFAULT_EMBEDDING_MODEL_PATH",
            "/DATA3/users/mj/hf_models/snowflake-arctic-embed-l-v2.0-ko",
        )
    )
    if not model_path.exists():
        pytest.skip(f"model path not present: {model_path}")

    assert (model_path / "config.json").is_file(), "HF config.json missing"
    assert any(model_path.glob("*.safetensors")) or any(
        model_path.glob("pytorch_model*.bin")
    ), "no model weights found"
