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
        messages: list[dict] | None = None,
        conversation_id: str | None = None,
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
                messages=messages,
                conversation_id=conversation_id,
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
    messages: list[dict] | None = None,
    conversation_id: str | None = None,
) -> None:
    """Compile the graph, stream events, persist to DB, signal SSE stream end."""
    # Import here to avoid circular imports at module load time.
    from app.repositories.run import RunRepository  # noqa: PLC0415
    from app.services.workflow.compiler import compile_workflow  # noqa: PLC0415

    import time as _time
    _t_exec_start = _time.perf_counter()
    print(f"[runtime] EXECUTE_START run_id={run_id}", flush=True)

    async with _semaphore, session_factory() as session:
        _t_session_ready = _time.perf_counter()
        print(f"[runtime] TIMING semaphore+session={(_t_session_ready - _t_exec_start)*1000:.0f}ms", flush=True)
        repo = RunRepository(session)
        try:
            # --- Compile ----------------------------------------------------
            _log.info(
                "runtime: compiling workflow for run_id=%s conversation_id=%s",
                run_id, conversation_id,
            )

            # Multi-turn: resolve checkpointer when a conversation_id is provided.
            # When absent we fall back to single-shot execution (no memory).
            checkpointer = None
            if conversation_id:
                try:
                    from app.services.workflow.checkpointer import (  # noqa: PLC0415
                        get_checkpointer,
                    )

                    checkpointer = await get_checkpointer()
                except Exception:  # noqa: BLE001
                    _log.warning(
                        "runtime: checkpointer unavailable; running stateless",
                        exc_info=True,
                    )

            _t_compile_start = _time.perf_counter()
            compiled = await compile_workflow(nodes, edges, session, checkpointer=checkpointer)
            _t_compile_end = _time.perf_counter()
            print(f"[runtime] TIMING compile_workflow={(_t_compile_end - _t_compile_start)*1000:.0f}ms", flush=True)

            # Identify guardrail node IDs — their internal LLM judge
            # tokens must be excluded from collected_tokens and SSE stream.
            _guardrail_node_ids: set[str] = {
                n["id"] for n in nodes
                if n.get("data", {}).get("type") == "input_guardrail"
            }

            # Outer graph 노드 ID 집합 — _map_event가 sub-graph 내부의
            # node_start/node_end (예: ReAct sub-graph의 'agent', 'tools',
            # 'call_model' 등)를 필터링할 때 사용.
            _outer_node_ids: set[str] = {n["id"] for n in nodes}

            # --- Initial state ----------------------------------------------
            # Always seed messages with the current user turn. The
            # ``add_messages`` reducer + checkpointer hydrates prior turns and
            # appends this one — that is the canonical LangGraph chat pattern.
            # Callers may also pre-populate ``messages`` (e.g. tests) which
            # will then be appended after the seeded user turn.
            seeded_user = (
                [{"role": "user", "content": user_input}] if user_input else []
            )
            initial_state: dict[str, Any] = {
                "user_input": user_input,
                "messages": seeded_user + (messages or []),
                "node_outputs": {},
                "final_output": "",
                "guardrail_blocked": False,
            }

            # --- Stream events with timeout ---------------------------------
            collected_tokens: list[str] = []
            final_output: str = ""
            state_final_output: str = ""  # from graph state (guardrail block, etc.)
            pending_events: int = 0  # count uncommitted events for batching

            # When a checkpointer is in use we must pass thread_id via config so
            # LangGraph can hydrate prior turns and persist this turn's deltas.
            stream_config: dict[str, Any] = {}
            if checkpointer is not None and conversation_id:
                stream_config["configurable"] = {"thread_id": conversation_id}

            # 한 LLM call 내에서 흐른 token들을 buffer. on_chat_model_end 시점에
                # tool_calls 유무 보고 답변 본문으로 emit 또는 폐기 결정.
            _pending_llm_tokens: list[dict[str, Any]] = []

            async def _stream() -> None:
                nonlocal final_output, pending_events, state_final_output
                _t_stream_start = _time.perf_counter()
                _first_event_logged = False
                async for raw_event in compiled.astream_events(
                    initial_state,
                    version="v2",
                    config=stream_config or None,
                ):
                    _ev_ms = (_time.perf_counter() - _t_stream_start) * 1000
                    _ev_name = raw_event.get("event", "?")
                    _ev_node = raw_event.get("metadata", {}).get("langgraph_node")
                    if not _first_event_logged:
                        print(f"[runtime] TIMING first_astream_event={_ev_ms:.0f}ms event={_ev_name}", flush=True)
                        _first_event_logged = True
                    # outer graph 노드 이벤트만 timestamp 기록 (sub-graph noise 제외)
                    if _ev_node and _outer_node_ids and _ev_node in _outer_node_ids:
                        print(f"[runtime] OUTER ev_t={_ev_ms:.0f}ms event={_ev_name} node={_ev_node}", flush=True)
                    mapped = _map_event(raw_event, outer_node_ids=_outer_node_ids)
                    if mapped is None:
                        continue

                    # ── llm_token 분기 처리 ────────────────────────────────
                    # ReAct 에이전트는 LLM 호출이 도구 호출 결정용(thought)일 때도
                    # content 토큰을 streaming 한다. 이걸 그대로 답변 본문에 흘려
                    # 보내면 reasoning 텍스트가 답변에 섞인다. 한 LLM call 내의
                    # 토큰을 buffer 했다가, on_chat_model_end 시점에 tool_calls
                    # 유무로 분기한다.
                    #   - tool_calls 있음 (thought call) → buffer 폐기 (대신
                    #     agent_thought 이벤트로 별도 발행됨)
                    #   - tool_calls 없음 (final 답변 call) → buffer 토큰들을
                    #     llm_token 이벤트로 일괄 emit → frontend 답변 본문에 누적
                    if mapped["event_type"] == "llm_token":
                        if mapped.get("node_id") in _guardrail_node_ids:
                            continue
                        token = mapped.get("payload", {}).get("token", "")
                        if not token:
                            continue
                        # 답변/thought 분기 전이라 즉시 발행 안 함. buffer 만 한다.
                        _pending_llm_tokens.append(mapped)
                        continue

                    # Track final_output from non-LLM paths (guardrail block, etc.)
                    # node_end and workflow_end events carry final_output in payload.
                    if mapped["event_type"] in ("node_end", "workflow_end"):
                        output = mapped.get("payload", {}).get("output", "")
                        if output:
                            state_final_output = output

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

                    # llm_end 시점에 도구 호출 결정 + reasoning content가 있으면
                    # 별도 agent_thought 이벤트를 추가 발행한다. ReAct 에이전트의
                    # "이 도구를 왜 부르는지" 사고 과정을 사용자에게 노출.
                    if mapped["event_type"] == "llm_end":
                        # buffer 된 token 들을 어디로 보낼지 결정
                        thought_event = _maybe_emit_agent_thought(raw_event, mapped)
                        if thought_event is not None:
                            # thought call 이었음 — buffer 토큰은 답변에 안 넣고 폐기
                            _pending_llm_tokens.clear()
                            await repo.add_event(
                                run_id=run_id,
                                event_type=thought_event["event_type"],
                                node_id=thought_event.get("node_id"),
                                payload=thought_event.get("payload", {}),
                            )
                            pending_events += 1
                            await queue.put(thought_event)
                        else:
                            # 답변 call — buffer 된 token 들을 한꺼번에 emit.
                            # streaming 효과는 다소 손실되지만 답변과 thought 분리.
                            for tok_event in _pending_llm_tokens:
                                tok = tok_event.get("payload", {}).get("token", "")
                                if tok:
                                    collected_tokens.append(tok)
                                await repo.add_event(
                                    run_id=run_id,
                                    event_type="llm_token",
                                    node_id=tok_event.get("node_id"),
                                    payload=tok_event.get("payload", {}),
                                )
                                pending_events += 1
                                await queue.put(tok_event)
                            _pending_llm_tokens.clear()

                # Flush remaining uncommitted events
                if pending_events > 0:
                    await session.commit()
                    pending_events = 0

            await asyncio.wait_for(_stream(), timeout=MAX_RUN_TIMEOUT_SECONDS)

            # --- Determine final output -------------------------------------
            # Prefer state-based final_output (explicitly set by agent/LLM
            # nodes); fall back to collected tokens for backwards compat.
            final_output = (
                state_final_output if state_final_output
                else "".join(collected_tokens)
            )

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


def _maybe_emit_agent_thought(
    raw: dict[str, Any],
    mapped: dict[str, Any],
) -> dict[str, Any] | None:
    """Inspect an on_chat_model_end event and emit an agent_thought event if the
    LLM produced both reasoning content and tool_calls.

    ReAct 에이전트는 "도구를 부르기 직전 짧은 reasoning"을 message.content에
    담아 보낼 수 있다 (모델에 따라 빈 경우도 많음). 답변 생성용 final LLM
    호출은 tool_calls 없이 content만 가진다 — 이 경우는 thought가 아니므로
    skip. tool_calls가 있고 content가 비어있지 않을 때만 thought로 본다.
    """
    data = raw.get("data", {})
    output = data.get("output")
    if output is None:
        return None

    # langchain AIMessage / AIMessageChunk 모두 content + tool_calls 속성을 가짐
    tool_calls = getattr(output, "tool_calls", None)
    if not tool_calls:
        return None

    content = getattr(output, "content", "")
    if isinstance(content, list):
        # multi-modal content — 텍스트 부분만 합침
        parts: list[str] = []
        for item in content:
            if isinstance(item, dict) and item.get("type") == "text":
                parts.append(item.get("text", ""))
            elif isinstance(item, str):
                parts.append(item)
        content = "".join(parts)
    if not isinstance(content, str):
        content = str(content) if content else ""
    content = content.strip()
    if not content:
        return None

    # tool_calls metadata 요약 — 사용자에게 어떤 도구를 부르려 하는지 미리보기
    tool_summaries: list[dict[str, Any]] = []
    for tc in tool_calls:
        if isinstance(tc, dict):
            tool_summaries.append({
                "name": tc.get("name") or tc.get("tool"),
                "args": tc.get("args") or tc.get("arguments") or {},
            })
        else:
            tool_summaries.append({
                "name": getattr(tc, "name", None) or getattr(tc, "tool", None),
                "args": getattr(tc, "args", None) or getattr(tc, "arguments", {}),
            })

    return {
        "event_type": "agent_thought",
        "node_id": mapped.get("node_id"),
        "payload": {
            "label": "thought",
            "status": "success",
            "content": content,
            "tool_calls": tool_summaries,
        },
    }


def _map_event(
    raw: dict[str, Any],
    outer_node_ids: set[str] | None = None,
) -> dict[str, Any] | None:
    """Map a LangGraph astream_events v2 event to our internal event schema.

    Returns None for events we intentionally ignore.

    ``outer_node_ids``: workflow의 outer graph 노드 ID 집합. node_start/node_end는
    이 집합에 속한 ID에 한해 통과시켜 ReAct sub-graph 내부의 노이즈 이벤트
    ('agent', 'tools', 'call_model', 'should_continue', 'RunnableSequence' 등)를
    제거한다. 다른 이벤트(llm_*, tool_*)는 sub-graph에서 발화되더라도 사용자
    UX에 의미가 있으므로 그대로 전달한다.

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
        # outer graph 노드만 통과 — sub-graph 내부 이벤트는 noise
        if outer_node_ids is not None and node_id not in outer_node_ids:
            return None
        return {
            "event_type": "node_start",
            "node_id": node_id,
            "payload": {"node_name": name},
        }

    if event_name == "on_chain_end" and node_id:
        if outer_node_ids is not None and node_id not in outer_node_ids:
            return None
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

    if event_name == "on_chat_model_start":
        # ReAct agent의 매 LLM 호출 시작 — 사용자에게 추론 진행 단계를
        # 풍부하게 보여주기 위해 프론트에 노출.
        return {
            "event_type": "llm_start",
            "node_id": node_id,
            "payload": {"name": name},
        }

    if event_name == "on_chat_model_end":
        return {
            "event_type": "llm_end",
            "node_id": node_id,
            "payload": {"name": name},
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

    # Hook events — dispatched via stream_writer in agent_node hook loop.
    # LangGraph on_custom_event carries these when using dispatch_custom_event.
    if event_name == "on_custom_event":
        custom_name = raw.get("name", "")
        if custom_name in ("hook_start", "hook_result"):
            return {
                "event_type": custom_name,
                "node_id": data.get("node_id"),
                "payload": data,
            }

    # All other events (on_chain_stream, on_llm_start, etc.) are ignored
    return None
