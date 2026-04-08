from __future__ import annotations

import os
from collections.abc import Iterator

import pytest


@pytest.fixture(autouse=True)
def isolate_env(monkeypatch: pytest.MonkeyPatch) -> Iterator[None]:
    """Strip AGENTBUILDER_* env vars before each test for deterministic Settings."""
    for key in list(os.environ):
        if key.startswith("AGENTBUILDER_"):
            monkeypatch.delenv(key, raising=False)
    yield
