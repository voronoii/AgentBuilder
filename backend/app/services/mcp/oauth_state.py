"""In-memory PKCE/state store for MCP OAuth authorization flow.

State is short-lived (default 10 min). On process restart, in-flight authorization
requests must be retried — acceptable for the MVP single-process deployment.
"""

from __future__ import annotations

import asyncio
import time
import uuid
from dataclasses import dataclass


@dataclass(frozen=True)
class StateEntry:
    server_id: uuid.UUID
    code_verifier: str
    expires_at: float  # monotonic-style absolute time.time()


class _Store:
    def __init__(self) -> None:
        self._items: dict[str, StateEntry] = {}
        self._lock = asyncio.Lock()

    async def put(self, state: str, entry: StateEntry) -> None:
        async with self._lock:
            self._gc_locked()
            self._items[state] = entry

    async def pop(self, state: str) -> StateEntry | None:
        async with self._lock:
            self._gc_locked()
            return self._items.pop(state, None)

    def _gc_locked(self) -> None:
        now = time.time()
        expired = [k for k, v in self._items.items() if v.expires_at < now]
        for k in expired:
            self._items.pop(k, None)


_store = _Store()


def get_state_store() -> _Store:
    return _store
