"""WorkflowRuntime — execution orchestrator for LangGraph workflow runs.

Manages:
- Process-local state: active task handles and SSE queues per run_id
- Global semaphore for max concurrent workflow cap (N=3)
- Background task lifecycle: compile → stream → persist events → cleanup
- SSE queue subscription for the /runs/{run_id}/events endpoint
"""
from __future__ import annotations

import asyncio
import logging
from typing import Any
from uuid import UUID

from sqlalchemy.ext.asyncio import async_sessionmaker

_log = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Process-local state
# ---------------------------------------------------------------------------

# Maps run_id → (asyncio.Task | None, asyncio.Queue)
_active_runs: dict[UUID, tuple[asyncio.Task | None, asyncio.Queue]] = {}

# Global concurrency cap — max 3 simultaneous workflow executions
_semaphore = asyncio.Semaphore(3)

# Maximum execution time per workflow run (5 minutes)
MAX_RUN_TIMEOUT_SECONDS = 300

# Batch DB commits — persist events every N items instead of per-token
_EVENT_BATCH_SIZE = 20


# ---------------------------------------------------------------------------
# Public runtime class
# ---------------------------------------------------------------------------


class WorkflowRuntime:
    """Manages workflow execution lifecycle (start, subscribe, cancel, cleanup)."""

    @staticmethod
    async def start_run(
        run_id: UUID,
        workflow_id: UUID,  # noqa: ARG004 — reserved for future metrics/logging
        nodes: list[dict],
        edges: list[dict],
        user_input: str,
        session_factory: async_sessionmaker,
    ) -> None:
        """Create a background asyncio.Task for the given run and register it."""
        queue: asyncio.Queue = asyncio.Queue()
        # Register placeholder so the queue is available immediately (before
        # the task is fully scheduled) for the SSE subscriber.
        _active_runs[run_id] = (None, queue)

        task = asyncio.create_task(
            _execute_workflow(
                run_id=run_id,
                nodes=nodes,
                edges=edges,
                user_input=user_input,
                queue=queue,
                session_factory=session_factory,
            ),
            name=f"run-{run_id}",
        )
        _active_runs[run_id] = (task, queue)

    @staticmethod
    def get_queue(run_id: UUID) -> asyncio.Queue | None:
        """Return the SSE queue for a running workflow, or None if not active."""
        entry = _active_runs.get(run_id)
        return entry[1] if entry else None

    @staticmethod
    async def cancel_run(run_id: UUID) -> bool:
        """Cancel the background task for a run. Returns True if task was found."""
        entry = _active_runs.get(run_id)
        if not entry or not entry[0]:
            return False
        entry[0].cancel()
        return True

    @staticmethod
    def cleanup(run_id: UUID) -> None:
        """Remove run from process-local state (called after task completes)."""
        _active_runs.pop(run_id, None)


# ---------------------------------------------------------------------------
# Background execution task
# ---------------------------------------------------------------------------


async def _execute_workflow(
    run_id: UUID,
    nodes: list[dict],
    edges: list[dict],
    user_input: str,
    queue: asyncio.Queue,
    session_factory: async_sessionmaker,
) -> None:
    """Compile the graph, stream events, persist to DB, signal SSE stream end."""
    # Import here to avoid circular imports at module load time.
    from app.repositories.run import RunRepository  # noqa: PLC0415
    from app.services.workflow.compiler import compile_workflow  # noqa: PLC0415

    async with _semaphore, session_factory() as session:
        repo = RunRepository(session)
        try:
            # --- Compile ----------------------------------------------------
            _log.info("runtime: compiling workflow for run_id=%s", run_id)
            compiled = await compile_workflow(nodes, edges, session)

            # --- Initial state ----------------------------------------------
            initial_state: dict[str, Any] = {
                "user_input": user_input,
                "messages": [],
                "node_outputs": {},
                "final_output": "",
            }

            # --- Stream events with timeout ---------------------------------
            collected_tokens: list[str] = []
            final_output: str = ""
            pending_events: int = 0  # count uncommitted events for batching

            async def _stream() -> None:
                nonlocal final_output, pending_events
                async for raw_event in compiled.astream_events(initial_state, version="v2"):
                    mapped = _map_event(raw_event)
                    if mapped is None:
                        continue

                    # Collect LLM tokens for final output reconstruction.
                    if mapped["event_type"] == "llm_token":
                        token = mapped.get("payload", {}).get("token", "")
                        if token:
                            collected_tokens.append(token)
                        else:
                            continue

                    # Persist to DB (batched commit for performance)
                    await repo.add_event(
                        run_id=run_id,
                        event_type=mapped["event_type"],
                        node_id=mapped.get("node_id"),
                        payload=mapped.get("payload", {}),
                    )
                    pending_events += 1

                    # Batch commit: flush every N events instead of per-token
                    if pending_events >= _EVENT_BATCH_SIZE:
                        await session.commit()
                        pending_events = 0

                    # Push to SSE queue (always immediate for responsiveness)
                    await queue.put(mapped)

                # Flush remaining uncommitted events
                if pending_events > 0:
                    await session.commit()
                    pending_events = 0

            await asyncio.wait_for(_stream(), timeout=MAX_RUN_TIMEOUT_SECONDS)

            # --- Determine final output -------------------------------------
            final_output = "".join(collected_tokens) if collected_tokens else ""

            if final_output:
                end_event = {
                    "event_type": "workflow_end",
                    "node_id": None,
                    "payload": {"output": final_output},
                }
                await repo.add_event(
                    run_id=run_id,
                    event_type="workflow_end",
                    node_id=None,
                    payload={"output": final_output},
                )
                await session.commit()
                await queue.put(end_event)

            # --- Mark success -----------------------------------------------
            await repo.update_status(
                run_id,
                _run_status("success"),
                output={"result": final_output},
            )
            await session.commit()
            _log.info("runtime: run_id=%s completed successfully", run_id)

        except asyncio.TimeoutError:
            _log.warning("runtime: run_id=%s timed out after %ds", run_id, MAX_RUN_TIMEOUT_SECONDS)
            await queue.put({"event_type": "workflow_error", "payload": {"error": f"실행 시간이 {MAX_RUN_TIMEOUT_SECONDS}초를 초과했습니다."}})
            try:
                await repo.update_status(run_id, _run_status("failed"), error=f"Timeout after {MAX_RUN_TIMEOUT_SECONDS}s")
                await session.commit()
            except Exception:  # noqa: BLE001
                _log.exception("runtime: failed to persist timeout state for run_id=%s", run_id)

        except asyncio.CancelledError:
            _log.info("runtime: run_id=%s was cancelled", run_id)
            await repo.update_status(run_id, _run_status("cancelled"))
            await session.commit()

        except Exception as exc:  # noqa: BLE001
            _log.exception("runtime: workflow execution failed: run_id=%s", run_id)
            await queue.put({"event_type": "workflow_error", "payload": {"error": str(exc)}})
            try:
                await repo.add_event(
                    run_id=run_id,
                    event_type="workflow_error",
                    node_id=None,
                    payload={"error": str(exc)},
                )
                await repo.update_status(run_id, _run_status("failed"), error=str(exc))
                await session.commit()
            except Exception:  # noqa: BLE001
                _log.exception("runtime: failed to persist error state for run_id=%s", run_id)

        finally:
            await queue.put(None)
            WorkflowRuntime.cleanup(run_id)


def _run_status(value: str) -> Any:
    """Deferred import helper — avoids circular imports at module load time."""
    from app.models.run import RunStatus  # noqa: PLC0415

    return RunStatus(value)


# ---------------------------------------------------------------------------
# LangGraph event → our event schema mapping
# ---------------------------------------------------------------------------


def _map_event(raw: dict[str, Any]) -> dict[str, Any] | None:
    """Map a LangGraph astream_events v2 event to our internal event schema.

    Returns None for events we intentionally ignore.

    Our event schema:
        {
            "event_type": str,   # node_start | node_end | llm_token | tool_call |
                                 # tool_result | workflow_end
            "node_id":    str | None,
            "payload":    dict,
        }
    """
    event_name: str = raw.get("event", "")
    name: str = raw.get("name", "")
    data: dict = raw.get("data", {})
    metadata: dict = raw.get("metadata", {})

    # Derive node_id from metadata (LangGraph v2 puts it in langgraph_node)
    node_id: str | None = metadata.get("langgraph_node") or None

    if event_name == "on_chain_start" and node_id:
        return {
            "event_type": "node_start",
            "node_id": node_id,
            "payload": {"node_name": name},
        }

    if event_name == "on_chain_end" and node_id:
        output = data.get("output", {})
        # Extract final_output if present in this node's output
        final_output = ""
        if isinstance(output, dict):
            final_output = output.get("final_output", "")
        return {
            "event_type": "node_end",
            "node_id": node_id,
            "payload": {"node_name": name, "output": final_output},
        }

    if event_name == "on_chat_model_stream":
        chunk = data.get("chunk")
        token = ""
        if chunk is not None and hasattr(chunk, "content"):
            token = chunk.content or ""
        return {
            "event_type": "llm_token",
            "node_id": node_id,
            "payload": {"token": token},
        }

    if event_name == "on_tool_start":
        return {
            "event_type": "tool_call",
            "node_id": node_id,
            "payload": {"tool_name": name, "input": data.get("input", {})},
        }

    if event_name == "on_tool_end":
        output = data.get("output", "")
        return {
            "event_type": "tool_result",
            "node_id": node_id,
            "payload": {"tool_name": name, "output": str(output)},
        }

    # Detect workflow completion: on_chain_end at the graph level (name is the graph name
    # or "__end__" sentinel). LangGraph v2 emits on_chain_end for the graph itself when done.
    if event_name == "on_chain_end" and not node_id:
        output = data.get("output", {})
        final_output = ""
        if isinstance(output, dict):
            final_output = output.get("final_output", "")
        return {
            "event_type": "workflow_end",
            "node_id": None,
            "payload": {"output": final_output},
        }

    # All other events (on_chain_stream, on_llm_start, etc.) are ignored
    return None
