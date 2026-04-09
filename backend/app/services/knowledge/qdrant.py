from __future__ import annotations

import asyncio
from typing import Any

from qdrant_client import QdrantClient
from qdrant_client.http import models as qm

from app.core.errors import AppError, ErrorCode


class QdrantStore:
    def __init__(self, url: str) -> None:
        self._client = QdrantClient(url=url)

    async def _run(self, fn: Any, *args: Any, **kwargs: Any) -> Any:
        loop = asyncio.get_running_loop()
        return await loop.run_in_executor(None, lambda: fn(*args, **kwargs))

    async def ping(self) -> None:
        try:
            await self._run(self._client.get_collections)
        except Exception as exc:
            raise AppError(
                status_code=503,
                code=ErrorCode.KNOWLEDGE_QDRANT_UNAVAILABLE,
                detail=f"qdrant unavailable: {exc}",
            ) from exc

    async def create_collection(self, name: str, *, dimension: int) -> None:
        await self._run(
            self._client.recreate_collection,
            collection_name=name,
            vectors_config=qm.VectorParams(size=dimension, distance=qm.Distance.COSINE),
        )

    async def delete_collection(self, name: str) -> None:
        await self._run(self._client.delete_collection, collection_name=name)

    async def upsert(self, name: str, *, points: list[dict[str, Any]]) -> None:
        qpoints = [
            qm.PointStruct(id=p["id"], vector=p["vector"], payload=p.get("payload", {}))
            for p in points
        ]
        await self._run(self._client.upsert, collection_name=name, points=qpoints)

    async def delete_by_document(self, name: str, *, document_id: str) -> None:
        await self._run(
            self._client.delete,
            collection_name=name,
            points_selector=qm.FilterSelector(
                filter=qm.Filter(
                    must=[
                        qm.FieldCondition(key="document_id", match=qm.MatchValue(value=document_id))
                    ]
                )
            ),
        )

    async def search(
        self, name: str, *, query: list[float], top_k: int = 5, score_threshold: float | None = None
    ) -> list[dict[str, Any]]:
        hits = await self._run(
            self._client.search,
            collection_name=name,
            query_vector=query,
            limit=top_k,
            score_threshold=score_threshold,
        )
        return [{"id": h.id, "score": h.score, "payload": h.payload or {}} for h in hits]
