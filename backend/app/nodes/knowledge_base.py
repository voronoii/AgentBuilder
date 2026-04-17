"""KnowledgeBase node — retrieves relevant context from a Qdrant collection.

Embeds the current input, searches the configured knowledge base, and
prepends the retrieved chunks to the state so downstream LLM/Agent nodes
can use them as context.
"""
from __future__ import annotations

import logging
import uuid
from collections.abc import Callable

from sqlalchemy.ext.asyncio import AsyncSession

from app.nodes.utils import get_input_text
from app.services.workflow.state import WorkflowState

_log = logging.getLogger(__name__)


async def search_knowledge_base(
    query: str,
    collection_name: str,
    embedding_provider_name: str,
    embedding_model: str,
    top_k: int = 5,
    score_threshold: float | None = None,
) -> list[str]:
    """Search a Qdrant collection and return matching text chunks.

    This is the shared search logic used by both the standalone KB node
    and the KB-as-tool integration in the Agent node.

    Args:
        query: The text to search for.
        collection_name: Qdrant collection to search.
        embedding_provider_name: Provider name (e.g. "local_hf", "openai").
        embedding_model: Model name or path for embedding.
        top_k: Number of chunks to retrieve.
        score_threshold: Minimum similarity score (None = no filtering).

    Returns:
        List of retrieved text chunks.
    """
    from app.services.knowledge.bootstrap import get_store  # noqa: PLC0415
    from app.services.providers.embedding import get_embedding_provider  # noqa: PLC0415

    if embedding_provider_name == "local_hf":
        embedder = get_embedding_provider("local_hf", model_path=embedding_model)
    else:
        embedder = get_embedding_provider(embedding_provider_name, model_name=embedding_model)

    query_vectors = await embedder.embed_texts([query])
    query_vector: list[float] = query_vectors[0]

    store = get_store()
    hits = await store.search(
        collection_name,
        query=query_vector,
        top_k=top_k,
        score_threshold=score_threshold,
    )

    chunks: list[str] = []
    for hit in hits:
        payload = hit.get("payload", {})
        text = payload.get("text") or payload.get("content") or ""
        if text:
            chunks.append(text)

    return chunks


async def make_knowledge_base_node(
    node_id: str,
    node_data: dict,
    session: AsyncSession,
    predecessor_ids: list[str] | None = None,
) -> Callable[[WorkflowState], dict]:
    """Factory that creates a KnowledgeBase node callable.

    Loads the KnowledgeBase record from the DB at compile time to resolve the
    embedding provider and Qdrant collection name.  The actual embedding and
    search happens at run time inside the returned coroutine.

    Args:
        node_id: Unique identifier of this node in the workflow graph.
        node_data: Frontend node configuration:
            - knowledgeBaseId (str): UUID of the KnowledgeBase row.
            - topK (int): Number of chunks to retrieve (default 5).
            - scoreThreshold (float): Minimum similarity score (default 0.0).
        session: Active async DB session.

    Returns:
        Async callable compatible with LangGraph's StateGraph.add_node().

    Raises:
        AppError(KNOWLEDGE_NOT_FOUND): If the KB UUID does not exist in the DB.
    """
    from app.core.errors import AppError, ErrorCode  # noqa: PLC0415
    from app.repositories.knowledge import KnowledgeRepository  # noqa: PLC0415

    kb_id_str: str = node_data.get("knowledgeBaseId", "")
    top_k: int = int(node_data.get("topK", 5))
    score_threshold: float = float(node_data.get("scoreThreshold", 0.0))

    # Resolve KB at compile time so we fail fast on bad configuration.
    try:
        kb_uuid = uuid.UUID(kb_id_str)
    except (ValueError, AttributeError) as exc:
        raise AppError(
            status_code=422,
            code=ErrorCode.COMPILATION_FAILED,
            detail=f"노드 '{node_id}': knowledgeBaseId '{kb_id_str}'가 유효한 UUID가 아닙니다.",
        ) from exc

    kb = await KnowledgeRepository(session).get_kb(kb_uuid)
    if kb is None:
        raise AppError(
            status_code=404,
            code=ErrorCode.KNOWLEDGE_NOT_FOUND,
            detail=f"노드 '{node_id}': KnowledgeBase '{kb_id_str}'를 찾을 수 없습니다.",
        )

    collection_name: str = kb.qdrant_collection
    embedding_provider_name: str = kb.embedding_provider
    embedding_model: str = kb.embedding_model
    effective_threshold: float | None = score_threshold if score_threshold > 0.0 else None
    _predecessors = predecessor_ids

    async def knowledge_base_node(state: WorkflowState) -> dict:
        input_text = get_input_text(state, node_id, predecessor_ids=_predecessors)
        _log.debug(
            "knowledge_base [%s]: kb=%s top_k=%d input_len=%d",
            node_id, kb_id_str, top_k, len(input_text),
        )

        chunks = await search_knowledge_base(
            query=input_text,
            collection_name=collection_name,
            embedding_provider_name=embedding_provider_name,
            embedding_model=embedding_model,
            top_k=top_k,
            score_threshold=effective_threshold,
        )

        context_text: str = "\n\n".join(chunks) if chunks else ""
        _log.debug(
            "knowledge_base [%s]: retrieved %d chunks (%d chars)",
            node_id, len(chunks), len(context_text),
        )

        enriched_output = (
            f"[Retrieved Context]\n{context_text}\n\n[User Input]\n{input_text}"
            if context_text
            else input_text
        )

        return {
            "node_outputs": {node_id: enriched_output},
        }

    knowledge_base_node.__name__ = f"knowledge_base_{node_id}"
    return knowledge_base_node
