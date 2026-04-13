"""WorkflowCompiler — converts a React Flow UI graph JSON into a compiled
LangGraph StateGraph ready for execution.

Pipeline (spec §8.1-8.2):
  1. Validate — raise AppError(COMPILATION_FAILED) on any structural error.
  2. Build node map from the raw list.
  3. Identify the single ChatInput (→ START) and ChatOutput (→ END) nodes.
  4. Topological sort of the remaining processing nodes.
  5. Create a LangGraph node function for each processing node via the
     registry in app.nodes.registry.
  6. Wire START → first processing node → … → last processing node → END.
  7. graph.compile() and return the compiled graph.
"""
from __future__ import annotations

import logging
from collections import defaultdict, deque
from typing import Any

from langgraph.graph import END, START, StateGraph
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import AppError, ErrorCode
from app.services.workflow.state import WorkflowState
from app.services.workflow.validator import WorkflowValidator

_log = logging.getLogger(__name__)


class WorkflowCompiler:
    """Converts a React Flow graph (nodes + edges dicts) into a compiled LangGraph."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._validator = WorkflowValidator()

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    async def compile(
        self,
        nodes: list[dict],
        edges: list[dict],
    ) -> Any:
        """Validate and compile the UI graph to a LangGraph CompiledGraph.

        Args:
            nodes: List of React Flow node dicts (each has "id" and "data").
            edges: List of React Flow edge dicts (each has "source" and "target").

        Returns:
            A compiled LangGraph StateGraph ready for `graph.invoke()` /
            `graph.astream()`.

        Raises:
            AppError(COMPILATION_FAILED): On any validation or wiring error.
        """
        _log.debug("compile: validating %d nodes, %d edges", len(nodes), len(edges))

        # Step 1 — Validate ------------------------------------------------
        errors = self._validator.validate(nodes, edges)
        if errors:
            error_details = [
                {"code": e.code, "message": e.message, "node_id": e.node_id}
                for e in errors
            ]
            _log.warning("compile: validation failed with %d error(s)", len(errors))
            raise AppError(
                status_code=422,
                code=ErrorCode.COMPILATION_FAILED,
                detail=f"워크플로우 검증 실패: {errors[0].message}",
                extra={"validation_errors": error_details},
            )

        # Step 2 — Build node map ------------------------------------------
        node_map: dict[str, dict] = {n["id"]: n for n in nodes}

        # Step 3 — Identify ChatInput / ChatOutput -------------------------
        chat_input_id = next(
            n["id"]
            for n in nodes
            if self._node_type(n) == "chat_input"
        )
        chat_output_id = next(
            n["id"]
            for n in nodes
            if self._node_type(n) == "chat_output"
        )

        # Step 4 — Topological sort (excluding I/O terminal nodes) ----------
        processing_ids_ordered = self._topological_sort(
            node_map=node_map,
            edges=edges,
            exclude={chat_input_id, chat_output_id},
        )
        _log.debug(
            "compile: processing order = %s", processing_ids_ordered
        )

        # Step 5 — Create LangGraph node functions -------------------------
        # Import deferred to avoid circular imports at module load time.
        from app.nodes.registry import create_node_function  # noqa: PLC0415

        graph: StateGraph = StateGraph(WorkflowState)
        processing_set = set(processing_ids_ordered)

        # Build predecessor map: node_id -> [predecessor_ids]
        predecessor_map: dict[str, list[str]] = defaultdict(list)
        for edge in edges:
            src, tgt = edge["source"], edge["target"]
            if src == chat_input_id and tgt in processing_set:
                predecessor_map[tgt].append(src)
            elif src in processing_set and tgt in processing_set:
                predecessor_map[tgt].append(src)

        for node_id in processing_ids_ordered:
            node_data = node_map[node_id].get("data", {})
            predecessors = predecessor_map.get(node_id, [])
            node_fn = await create_node_function(
                node_id=node_id,
                node_data=node_data,
                session=self._session,
                predecessor_ids=predecessors,
            )
            graph.add_node(node_id, node_fn)
            _log.debug("compile: added node %s (type=%s, predecessors=%s)", node_id, node_data.get("type"), predecessors)

        # Step 6 — Wire edges ----------------------------------------------
        if not processing_ids_ordered:
            # Degenerate: only ChatInput → ChatOutput (passthrough)
            # This should not happen after validation, but handle gracefully.
            raise AppError(
                status_code=422,
                code=ErrorCode.COMPILATION_FAILED,
                detail="워크플로우에 처리 노드(LLM, Agent 등)가 없습니다.",
            )

        # START → first processing node
        graph.add_edge(START, processing_ids_ordered[0])

        # Wire edges between processing nodes following the original UI graph.
        for edge in edges:
            src, tgt = edge["source"], edge["target"]
            # Only wire edges between actual processing nodes (not I/O terminals).
            if src in processing_set and tgt in processing_set:
                graph.add_edge(src, tgt)

        # Sink processing nodes → END
        # Sinks = nodes that have no outgoing edges to other processing nodes.
        # ALL sinks must be connected to END (not just one).
        sink_ids = self._find_sink_nodes(
            processing_ids_ordered, edges, processing_set
        )
        for sink_id in sink_ids:
            graph.add_edge(sink_id, END)

        # Step 7 — Compile -------------------------------------------------
        compiled = graph.compile()
        _log.info(
            "compile: graph compiled successfully (%d processing nodes)",
            len(processing_ids_ordered),
        )
        return compiled

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _topological_sort(
        self,
        *,
        node_map: dict[str, dict],
        edges: list[dict],
        exclude: set[str],
    ) -> list[str]:
        """Return node IDs in topological order, skipping excluded IDs.

        Kahn's algorithm.  The validator already confirmed there are no cycles,
        so this is safe.
        """
        ids = [nid for nid in node_map if nid not in exclude]
        ids_set = set(ids)

        in_degree: dict[str, int] = {nid: 0 for nid in ids}
        adjacency: dict[str, list[str]] = defaultdict(list)

        for edge in edges:
            src, tgt = edge["source"], edge["target"]
            if src in ids_set and tgt in ids_set:
                adjacency[src].append(tgt)
                in_degree[tgt] += 1

        queue: deque[str] = deque(nid for nid, deg in in_degree.items() if deg == 0)
        ordered: list[str] = []

        while queue:
            nid = queue.popleft()
            ordered.append(nid)
            for neighbour in adjacency[nid]:
                in_degree[neighbour] -= 1
                if in_degree[neighbour] == 0:
                    queue.append(neighbour)

        return ordered

    def _find_sink_nodes(
        self,
        ordered: list[str],
        edges: list[dict],
        processing_set: set[str],
    ) -> list[str]:
        """Return IDs of all sink processing nodes (no outgoing processing edges).

        All sinks must be wired to END so LangGraph can terminate correctly,
        even when multiple parallel branches exist.
        """
        has_outgoing: set[str] = set()
        for edge in edges:
            if edge["source"] in processing_set and edge["target"] in processing_set:
                has_outgoing.add(edge["source"])

        sinks = [nid for nid in ordered if nid not in has_outgoing]
        if not sinks:
            # Fallback: use topological last
            sinks = [ordered[-1]]

        _log.debug("_find_sink_nodes: %d sink(s) found: %s", len(sinks), sinks)
        return sinks

    @staticmethod
    def _node_type(node: dict) -> str:
        data = node.get("data", {})
        return str(data.get("type") or node.get("type", ""))


# ---------------------------------------------------------------------------
# Convenience helper used by the run API
# ---------------------------------------------------------------------------


async def compile_workflow(
    nodes: list[dict[str, Any]],
    edges: list[dict[str, Any]],
    session: AsyncSession,
) -> Any:
    """Module-level shortcut: instantiate WorkflowCompiler and compile."""
    return await WorkflowCompiler(session).compile(nodes, edges)
