"""WorkflowValidator — structural validation of a React Flow UI graph.

Checks performed (all must pass for compilation to proceed):
  1. Exactly one chat_input node and exactly one chat_output node.
  2. No isolated nodes (every node has at least one edge).
  3. No cycles (DAG check via Kahn's algorithm).
  4. Required fields are set on each node type.
  5. Every edge references valid node IDs.
"""
from __future__ import annotations

import logging
from collections import defaultdict, deque
from dataclasses import dataclass

_log = logging.getLogger(__name__)

# ── Node types that require specific fields ─────────────────────────────────
_REQUIRED_FIELDS: dict[str, list[str]] = {
    "llm": ["provider", "model"],
    "agent": ["provider", "model"],
    "knowledge_base": ["knowledgeBaseId"],
    "prompt_template": ["template"],
    "input_guardrail": ["provider", "model"],
}

_VALID_NODE_TYPES = {
    "chat_input",
    "chat_output",
    "llm",
    "agent",
    "knowledge_base",
    "prompt_template",
    "input_guardrail",
}


@dataclass(frozen=True)
class ValidationError:
    code: str
    message: str
    node_id: str | None = None


class WorkflowValidator:
    """Validate nodes and edges from a React Flow graph representation.

    Each node dict is expected to have the shape::

        {
            "id": "<node_id>",
            "data": {
                "type": "<NodeType>",
                ...fields...
            }
        }

    Each edge dict::

        {"source": "<node_id>", "target": "<node_id>", ...}
    """

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def validate(
        self,
        nodes: list[dict],
        edges: list[dict],
    ) -> list[ValidationError]:
        """Return a list of ValidationError objects. Empty list means valid."""
        errors: list[ValidationError] = []
        errors.extend(self._check_io_nodes(nodes))
        errors.extend(self._check_isolated_nodes(nodes, edges))
        errors.extend(self._check_cycles(nodes, edges))
        errors.extend(self._check_required_fields(nodes))
        errors.extend(self._check_edge_validity(nodes, edges))
        errors.extend(self._check_input_output_path(nodes, edges))
        return errors

    # ------------------------------------------------------------------
    # Individual checks
    # ------------------------------------------------------------------

    def _check_io_nodes(self, nodes: list[dict]) -> list[ValidationError]:
        """Exactly 1 chat_input and exactly 1 chat_output required."""
        errors: list[ValidationError] = []
        input_ids = [n["id"] for n in nodes if self._node_type(n) == "chat_input"]
        output_ids = [n["id"] for n in nodes if self._node_type(n) == "chat_output"]

        if len(input_ids) == 0:
            errors.append(
                ValidationError(
                    code="MISSING_CHAT_INPUT",
                    message="워크플로우에 ChatInput 노드가 정확히 하나 있어야 합니다 (현재 0개).",
                )
            )
        elif len(input_ids) > 1:
            errors.append(
                ValidationError(
                    code="MULTIPLE_CHAT_INPUT",
                    message=f"ChatInput 노드는 하나만 허용됩니다 (현재 {len(input_ids)}개).",
                )
            )

        if len(output_ids) == 0:
            errors.append(
                ValidationError(
                    code="MISSING_CHAT_OUTPUT",
                    message="워크플로우에 ChatOutput 노드가 정확히 하나 있어야 합니다 (현재 0개).",
                )
            )
        elif len(output_ids) > 1:
            errors.append(
                ValidationError(
                    code="MULTIPLE_CHAT_OUTPUT",
                    message=f"ChatOutput 노드는 하나만 허용됩니다 (현재 {len(output_ids)}개).",
                )
            )

        return errors

    def _check_isolated_nodes(
        self, nodes: list[dict], edges: list[dict]
    ) -> list[ValidationError]:
        """Every node must participate in at least one edge."""
        errors: list[ValidationError] = []
        connected: set[str] = set()
        for edge in edges:
            connected.add(edge["source"])
            connected.add(edge["target"])

        for node in nodes:
            node_id = node["id"]
            if node_id not in connected:
                errors.append(
                    ValidationError(
                        code="ISOLATED_NODE",
                        message=f"노드 '{node_id}'가 다른 노드와 연결되어 있지 않습니다.",
                        node_id=node_id,
                    )
                )
        return errors

    def _check_cycles(
        self, nodes: list[dict], edges: list[dict]
    ) -> list[ValidationError]:
        """DAG check via Kahn's algorithm (topological sort). Cycle → error."""
        # Build adjacency + in-degree
        node_ids = {n["id"] for n in nodes}
        in_degree: dict[str, int] = {nid: 0 for nid in node_ids}
        adjacency: dict[str, list[str]] = defaultdict(list)

        for edge in edges:
            src, tgt = edge["source"], edge["target"]
            if src in node_ids and tgt in node_ids:
                adjacency[src].append(tgt)
                in_degree[tgt] += 1

        queue: deque[str] = deque(nid for nid, deg in in_degree.items() if deg == 0)
        visited = 0

        while queue:
            nid = queue.popleft()
            visited += 1
            for neighbour in adjacency[nid]:
                in_degree[neighbour] -= 1
                if in_degree[neighbour] == 0:
                    queue.append(neighbour)

        if visited != len(node_ids):
            return [
                ValidationError(
                    code="CYCLE_DETECTED",
                    message="워크플로우에 순환(사이클)이 감지되었습니다. DAG 구조여야 합니다.",
                )
            ]
        return []

    def _check_required_fields(self, nodes: list[dict]) -> list[ValidationError]:
        """Validate that each node type has its mandatory data fields set."""
        errors: list[ValidationError] = []
        for node in nodes:
            node_id = node["id"]
            node_type = self._node_type(node)

            if node_type not in _VALID_NODE_TYPES:
                errors.append(
                    ValidationError(
                        code="UNKNOWN_NODE_TYPE",
                        message=f"알 수 없는 노드 타입: '{node_type}'.",
                        node_id=node_id,
                    )
                )
                continue

            required = _REQUIRED_FIELDS.get(node_type, [])
            data = node.get("data", {})
            for field in required:
                value = data.get(field)
                if not value:
                    errors.append(
                        ValidationError(
                            code="MISSING_REQUIRED_FIELD",
                            message=f"노드 '{node_id}' ({node_type})에 필수 필드 '{field}'가 누락되었습니다.",
                            node_id=node_id,
                        )
                    )
        return errors

    def _check_edge_validity(
        self, nodes: list[dict], edges: list[dict]
    ) -> list[ValidationError]:
        """All edge source/target IDs must reference existing nodes."""
        errors: list[ValidationError] = []
        node_ids = {n["id"] for n in nodes}

        for edge in edges:
            src = edge.get("source", "")
            tgt = edge.get("target", "")
            if src not in node_ids:
                errors.append(
                    ValidationError(
                        code="INVALID_EDGE_SOURCE",
                        message=f"엣지의 source '{src}'가 존재하지 않는 노드를 참조합니다.",
                    )
                )
            if tgt not in node_ids:
                errors.append(
                    ValidationError(
                        code="INVALID_EDGE_TARGET",
                        message=f"엣지의 target '{tgt}'가 존재하지 않는 노드를 참조합니다.",
                    )
                )
        return errors

    def _check_input_output_path(
        self, nodes: list[dict], edges: list[dict]
    ) -> list[ValidationError]:
        """BFS from chat_input to verify at least one path reaches chat_output."""
        input_ids = [n["id"] for n in nodes if self._node_type(n) == "chat_input"]
        output_ids = {n["id"] for n in nodes if self._node_type(n) == "chat_output"}

        # Skip this check if io nodes are missing (already reported by _check_io_nodes)
        if not input_ids or not output_ids:
            return []

        adjacency: dict[str, list[str]] = defaultdict(list)
        for edge in edges:
            src = edge.get("source", "")
            tgt = edge.get("target", "")
            if src and tgt:
                adjacency[src].append(tgt)

        # BFS from the single chat_input node
        start = input_ids[0]
        visited: set[str] = set()
        queue: deque[str] = deque([start])
        visited.add(start)

        while queue:
            current = queue.popleft()
            if current in output_ids:
                return []
            for neighbour in adjacency[current]:
                if neighbour not in visited:
                    visited.add(neighbour)
                    queue.append(neighbour)

        return [
            ValidationError(
                code="NO_INPUT_OUTPUT_PATH",
                message="ChatInput에서 ChatOutput까지 연결된 경로가 없습니다.",
            )
        ]

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _node_type(node: dict) -> str:
        """Extract node type from either node.data.type or node.type."""
        data = node.get("data", {})
        return str(data.get("type") or node.get("type", ""))
