from __future__ import annotations

import uuid
from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.run import RunEvent, RunStatus, WorkflowRun


class RunRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create(self, workflow_id: uuid.UUID, input_data: dict) -> WorkflowRun:
        run = WorkflowRun(
            workflow_id=workflow_id,
            status=RunStatus.running,
            input=input_data,
        )
        self._session.add(run)
        await self._session.flush()
        await self._session.refresh(run)
        return run

    async def get(self, run_id: uuid.UUID) -> WorkflowRun | None:
        return await self._session.get(WorkflowRun, run_id)

    async def list_by_workflow(
        self, workflow_id: uuid.UUID, limit: int = 50
    ) -> list[WorkflowRun]:
        result = await self._session.execute(
            select(WorkflowRun)
            .where(WorkflowRun.workflow_id == workflow_id)
            .order_by(WorkflowRun.started_at.desc())
            .limit(limit)
        )
        return list(result.scalars().all())

    async def update_status(
        self,
        run_id: uuid.UUID,
        status: RunStatus,
        output: dict | None = None,
        error: str | None = None,
    ) -> None:
        run = await self.get(run_id)
        if run is None:
            return
        run.status = status
        run.ended_at = datetime.now(tz=UTC)
        if output is not None:
            run.output = output
        if error is not None:
            run.error = error
        await self._session.flush()

    async def add_event(
        self,
        run_id: uuid.UUID,
        event_type: str,
        node_id: str | None,
        payload: dict,
    ) -> RunEvent:
        event = RunEvent(
            run_id=run_id,
            event_type=event_type,
            node_id=node_id,
            payload=payload,
        )
        self._session.add(event)
        await self._session.flush()
        await self._session.refresh(event)
        return event

    async def get_events(self, run_id: uuid.UUID) -> list[RunEvent]:
        result = await self._session.execute(
            select(RunEvent)
            .where(RunEvent.run_id == run_id)
            .order_by(RunEvent.timestamp.asc())
        )
        return list(result.scalars().all())

    async def mark_stale_runs_failed(self) -> int:
        """Mark all runs with status=running as failed. Called on server startup."""
        result = await self._session.execute(
            select(WorkflowRun).where(WorkflowRun.status == RunStatus.running)
        )
        runs = list(result.scalars().all())
        now = datetime.now(tz=UTC)
        for run in runs:
            run.status = RunStatus.failed
            run.ended_at = now
            run.error = "interrupted by server restart"
        await self._session.flush()
        return len(runs)
