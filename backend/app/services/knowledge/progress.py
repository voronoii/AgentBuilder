from __future__ import annotations

import asyncio
import uuid
from collections.abc import AsyncIterator
from dataclasses import dataclass, field


@dataclass(frozen=True)
class ProgressEvent:
    kb_id: uuid.UUID
    document_id: uuid.UUID
    status: str  # "processing" | "done" | "failed"
    chunks_done: int = 0
    chunks_total: int = 0
    error: str | None = None

    def to_dict(self) -> dict[str, object]:
        return {
            "kb_id": str(self.kb_id),
            "document_id": str(self.document_id),
            "status": self.status,
            "chunks_done": self.chunks_done,
            "chunks_total": self.chunks_total,
            "error": self.error,
        }


@dataclass
class _Bus:
    _subscribers: dict[uuid.UUID, list[asyncio.Queue[ProgressEvent]]] = field(
        default_factory=dict
    )
    _latest: dict[uuid.UUID, dict[uuid.UUID, ProgressEvent]] = field(
        default_factory=dict
    )
    _lock: asyncio.Lock = field(default_factory=asyncio.Lock)

    async def publish(self, event: ProgressEvent) -> None:
        async with self._lock:
            self._latest.setdefault(event.kb_id, {})[event.document_id] = event
            for q in self._subscribers.get(event.kb_id, []):
                await q.put(event)

    async def subscribe(self, kb_id: uuid.UUID) -> AsyncIterator[ProgressEvent]:
        queue: asyncio.Queue[ProgressEvent] = asyncio.Queue()
        async with self._lock:
            self._subscribers.setdefault(kb_id, []).append(queue)
            for evt in self._latest.get(kb_id, {}).values():
                await queue.put(evt)
        try:
            while True:
                yield await queue.get()
        finally:
            async with self._lock:
                subs = self._subscribers.get(kb_id, [])
                if queue in subs:
                    subs.remove(queue)


progress_bus = _Bus()
