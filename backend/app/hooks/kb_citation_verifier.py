"""Hook: verify that citations in agent output actually exist in a KB."""

from __future__ import annotations

import logging
import re
from typing import Any
from uuid import UUID

from app.hooks.protocol import AgentHook, HookContext, HookVerdict
from app.services.workflow.state import WorkflowState

_log = logging.getLogger(__name__)


class KBCitationVerifierHook:
    """Extract citation patterns from output, then search KB for each."""

    hook_type = "kb_citation_verifier"

    def __init__(
        self,
        *,
        kb_id: str,
        patterns: list[str],
        max_retries: int = 2,
        on_exhausted: str = "error",
        timeout_ms: int = 30_000,
        retry_strategy: str = "accumulate",
        fallback_message: str = "",
    ) -> None:
        self.kb_id = UUID(kb_id)
        self.patterns = [re.compile(p) for p in patterns]
        self.max_retries = max_retries
        self.on_exhausted = on_exhausted
        self.timeout_ms = timeout_ms
        self.retry_strategy = retry_strategy
        self.fallback_message = fallback_message

    async def verify(
        self,
        output: str,
        messages: list[Any],
        state: WorkflowState,
        ctx: HookContext,
    ) -> HookVerdict:
        from app.nodes.knowledge_base import search_knowledge_base
        from app.repositories.knowledge import KnowledgeRepository

        # 1. Extract citations via regex patterns
        citations: list[str] = []
        for pat in self.patterns:
            citations.extend(pat.findall(output))

        if not citations:
            return HookVerdict(passed=True, details={"citations_found": 0})

        # Deduplicate while preserving order
        seen: set[str] = set()
        unique_citations: list[str] = []
        for c in citations:
            key = c if isinstance(c, str) else str(c)
            if key not in seen:
                seen.add(key)
                unique_citations.append(key)

        # 2. Load KB metadata (includes permission check via repository)
        repo = KnowledgeRepository(ctx.session)
        kb = await repo.get_kb(self.kb_id)
        if kb is None:
            _log.warning("kb_citation_verifier: KB %s not found", self.kb_id)
            return HookVerdict(
                passed=True,
                details={"error": f"KB {self.kb_id} not found, skipping verification"},
            )

        # 3. Search KB for each citation
        not_found: list[str] = []
        for citation in unique_citations:
            hits = await search_knowledge_base(
                query=citation,
                collection_name=kb.qdrant_collection,
                embedding_provider_name=kb.embedding_provider,
                embedding_model=kb.embedding_model,
                top_k=3,
                score_threshold=0.5,
            )
            if not hits:
                not_found.append(citation)

        if not_found:
            return HookVerdict(
                passed=False,
                feedback=(
                    f"다음 인용을 지식베이스에서 확인할 수 없습니다: {', '.join(not_found)}. "
                    f"실제 존재하는 내용만 인용하세요."
                ),
                details={
                    "not_found": not_found,
                    "total_citations": len(unique_citations),
                    "verified": len(unique_citations) - len(not_found),
                },
            )

        return HookVerdict(
            passed=True,
            details={"verified": len(unique_citations)},
        )
