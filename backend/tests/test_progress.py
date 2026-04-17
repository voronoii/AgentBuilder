from __future__ import annotations

import asyncio
import uuid

import pytest

from app.services.knowledge.progress import ProgressEvent, progress_bus


@pytest.mark.asyncio
async def test_publish_and_subscribe() -> None:
    kb_id = uuid.uuid4()
    doc_id = uuid.uuid4()
    received: list[ProgressEvent] = []

    async def consume() -> None:
        async for evt in progress_bus.subscribe(kb_id):
            received.append(evt)
            if evt.status == "done":
                break

    consumer = asyncio.create_task(consume())
    await asyncio.sleep(0)

    await progress_bus.publish(
        ProgressEvent(
            kb_id=kb_id,
            document_id=doc_id,
            status="processing",
            chunks_done=5,
            chunks_total=10,
        )
    )
    await progress_bus.publish(
        ProgressEvent(
            kb_id=kb_id,
            document_id=doc_id,
            status="done",
            chunks_done=10,
            chunks_total=10,
        )
    )

    await asyncio.wait_for(consumer, timeout=2.0)
    assert [e.status for e in received] == ["processing", "done"]
