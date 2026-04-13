"""Runs API — create, stream, cancel, and query workflow runs.

Route layout (mixed prefix per spec §8.7):
  POST   /workflows/{workflow_id}/runs         → create_run
  GET    /workflows/{workflow_id}/runs         → list_runs
  GET    /runs/{run_id}                        → get_run
  GET    /runs/{run_id}/events                 → stream_events  (SSE)
  GET    /runs/{run_id}/events/history         → get_run_events (persisted)
  POST   /runs/{run_id}/cancel                 → cancel_run
"""
from __future__ import annotations

import asyncio
import json
import logging
import uuid
from collections.abc import AsyncIterator
from typing import Annotated, Any

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession
from sse_starlette.sse import EventSourceResponse

from app.core.db import get_session, get_sessionmaker
from app.core.errors import AppError, ErrorCode
from app.models.run import RunStatus
from app.repositories.run import RunRepository
from app.repositories.workflow import WorkflowRepository
from app.schemas.run import RunCreate, RunEventRead, RunRead, RunSummary
from app.services.workflow.runtime import WorkflowRuntime

_log = logging.getLogger(__name__)

# Two separate routers to handle the mixed path prefixes
_workflow_router = APIRouter(prefix="/workflows", tags=["runs"])
_run_router = APIRouter(prefix="/runs", tags=["runs"])


# ---------------------------------------------------------------------------
# POST /workflows/{workflow_id}/runs
# ---------------------------------------------------------------------------


@_workflow_router.post(
    "/{workflow_id}/runs",
    response_model=RunRead,
    status_code=status.HTTP_201_CREATED,
)
async def create_run(
    workflow_id: uuid.UUID,
    body: RunCreate,
    session: Annotated[AsyncSession, Depends(get_session)],
) -> Any:
    """Create a new WorkflowRun and start execution in the background.

    Returns the run record immediately (status=running) without waiting for
    the workflow to complete.
    """
    # Verify the workflow exists
    wf = await WorkflowRepository(session).get(workflow_id)
    if wf is None:
        raise AppError(
            status_code=404,
            code=ErrorCode.WORKFLOW_NOT_FOUND,
            detail="워크플로우를 찾을 수 없습니다.",
        )

    # Determine user_input from body.input
    user_input: str = body.input.get("message", "") if body.input else ""

    # Create the WorkflowRun record (status=running)
    repo = RunRepository(session)
    run = await repo.create(workflow_id=workflow_id, input_data=body.input)
    await session.commit()
    await session.refresh(run)

    # Start background execution task (non-blocking)
    await WorkflowRuntime.start_run(
        run_id=run.id,
        workflow_id=workflow_id,
        nodes=wf.nodes or [],
        edges=wf.edges or [],
        user_input=user_input,
        session_factory=get_sessionmaker(),
    )

    _log.info("create_run: started run_id=%s for workflow_id=%s", run.id, workflow_id)
    return run


# ---------------------------------------------------------------------------
# GET /workflows/{workflow_id}/runs
# ---------------------------------------------------------------------------


@_workflow_router.get("/{workflow_id}/runs", response_model=list[RunSummary])
async def list_runs(
    workflow_id: uuid.UUID,
    session: Annotated[AsyncSession, Depends(get_session)],
) -> list[Any]:
    """List runs for a workflow (most recent first, up to 50)."""
    wf = await WorkflowRepository(session).get(workflow_id)
    if wf is None:
        raise AppError(
            status_code=404,
            code=ErrorCode.WORKFLOW_NOT_FOUND,
            detail="워크플로우를 찾을 수 없습니다.",
        )
    return await RunRepository(session).list_by_workflow(workflow_id)


# ---------------------------------------------------------------------------
# GET /runs/{run_id}
# ---------------------------------------------------------------------------


@_run_router.get("/{run_id}", response_model=RunRead)
async def get_run(
    run_id: uuid.UUID,
    session: Annotated[AsyncSession, Depends(get_session)],
) -> Any:
    """Get the current state of a run."""
    run = await RunRepository(session).get(run_id)
    if run is None:
        raise AppError(
            status_code=404,
            code=ErrorCode.RUN_NOT_FOUND,
            detail="실행 기록을 찾을 수 없습니다.",
        )
    return run


# ---------------------------------------------------------------------------
# GET /runs/{run_id}/events  (SSE)
# ---------------------------------------------------------------------------


@_run_router.get("/{run_id}/events")
async def stream_events(
    run_id: uuid.UUID,
    session: Annotated[AsyncSession, Depends(get_session)],
) -> EventSourceResponse:
    """SSE stream of run events.

    If the run is still active, subscribes to the in-memory asyncio.Queue
    and relays events as they arrive.  If the run has already completed,
    replays persisted events from the database instead.
    """
    run = await RunRepository(session).get(run_id)
    if run is None:
        raise AppError(
            status_code=404,
            code=ErrorCode.RUN_NOT_FOUND,
            detail="실행 기록을 찾을 수 없습니다.",
        )

    # Check if there is an active in-memory queue for this run
    queue = WorkflowRuntime.get_queue(run_id)

    if queue is not None:
        # Live run — stream from the queue
        return EventSourceResponse(_stream_from_queue(queue, run_id))
    else:
        # Completed run — replay persisted events from DB
        repo = RunRepository(session)
        events = await repo.get_events(run_id)
        return EventSourceResponse(_stream_from_db(events, run))


async def _stream_from_queue(
    queue: asyncio.Queue,
    run_id: uuid.UUID,
) -> AsyncIterator[dict]:
    """Yield SSE events from the live asyncio.Queue until the sentinel (None)."""
    while True:
        try:
            event = await asyncio.wait_for(queue.get(), timeout=60.0)
        except TimeoutError:
            # Send a keep-alive comment to prevent client timeout
            yield {"event": "ping", "data": ""}
            continue

        if event is None:
            # Sentinel — workflow finished (success, failed, or cancelled)
            yield {"event": "done", "data": json.dumps({"run_id": str(run_id)})}
            break

        yield {
            "event": event.get("event_type", "event"),
            "data": json.dumps(_sanitize_event(event)),
        }


async def _stream_from_db(events: list, run: Any) -> AsyncIterator[dict]:
    """Replay already-persisted events from the database."""
    for ev in events:
        yield {
            "event": ev.event_type,
            "data": json.dumps(
                {
                    "event_type": ev.event_type,
                    "node_id": ev.node_id,
                    "payload": ev.payload,
                    "timestamp": ev.timestamp.isoformat(),
                }
            ),
        }
    # Final done event
    yield {
        "event": "done",
        "data": json.dumps({"run_id": str(run.id), "status": run.status}),
    }


def _sanitize_event(event: dict) -> dict:
    """Ensure all values are JSON-serializable."""
    return {
        "event_type": event.get("event_type", ""),
        "node_id": event.get("node_id"),
        "payload": event.get("payload", {}),
    }


# ---------------------------------------------------------------------------
# GET /runs/{run_id}/events/history
# ---------------------------------------------------------------------------


@_run_router.get("/{run_id}/events/history", response_model=list[RunEventRead])
async def get_run_events(
    run_id: uuid.UUID,
    session: Annotated[AsyncSession, Depends(get_session)],
) -> list[Any]:
    """Get all persisted events for a run (for completed/failed runs)."""
    run = await RunRepository(session).get(run_id)
    if run is None:
        raise AppError(
            status_code=404,
            code=ErrorCode.RUN_NOT_FOUND,
            detail="실행 기록을 찾을 수 없습니다.",
        )
    return await RunRepository(session).get_events(run_id)


# ---------------------------------------------------------------------------
# POST /runs/{run_id}/cancel
# ---------------------------------------------------------------------------


@_run_router.post("/{run_id}/cancel")
async def cancel_run(
    run_id: uuid.UUID,
    session: Annotated[AsyncSession, Depends(get_session)],
) -> dict[str, str]:
    """Cancel a running workflow.

    Raises 409 if the run is already in a terminal state.
    Raises 500 if the cancel signal could not be delivered.
    """
    repo = RunRepository(session)
    run = await repo.get(run_id)
    if run is None:
        raise AppError(
            status_code=404,
            code=ErrorCode.RUN_NOT_FOUND,
            detail="실행 기록을 찾을 수 없습니다.",
        )

    terminal_statuses = {RunStatus.success, RunStatus.failed, RunStatus.cancelled}
    if RunStatus(run.status) in terminal_statuses:
        raise AppError(
            status_code=409,
            code=ErrorCode.RUN_ALREADY_FINISHED,
            detail=f"이미 종료된 실행입니다 (상태: {run.status}).",
        )

    cancelled = await WorkflowRuntime.cancel_run(run_id)
    if not cancelled:
        # The task may have just finished between our status check and the cancel call.
        # Treat as if already finished.
        raise AppError(
            status_code=409,
            code=ErrorCode.RUN_CANCEL_FAILED,
            detail="실행을 취소할 수 없습니다. 이미 완료되었을 수 있습니다.",
        )

    _log.info("cancel_run: cancellation signal sent for run_id=%s", run_id)
    return {"status": "cancelling", "run_id": str(run_id)}


# ---------------------------------------------------------------------------
# Expose both routers as a list for main.py to include
# ---------------------------------------------------------------------------

routers = [_workflow_router, _run_router]
