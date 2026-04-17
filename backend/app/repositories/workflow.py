from __future__ import annotations

import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.workflow import Workflow
from app.schemas.workflow import WorkflowCreate, WorkflowUpdate


class WorkflowRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create(self, payload: WorkflowCreate) -> Workflow:
        wf = Workflow(
            name=payload.name,
            description=payload.description,
            nodes=payload.nodes,
            edges=payload.edges,
        )
        self._session.add(wf)
        await self._session.flush()
        return wf

    async def list_all(self) -> list[Workflow]:
        result = await self._session.execute(
            select(Workflow).order_by(Workflow.updated_at.desc())
        )
        return list(result.scalars().all())

    async def get(self, wf_id: uuid.UUID) -> Workflow | None:
        return await self._session.get(Workflow, wf_id)

    async def update(self, wf_id: uuid.UUID, payload: WorkflowUpdate) -> Workflow | None:
        wf = await self.get(wf_id)
        if wf is None:
            return None
        update_data = payload.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            setattr(wf, field, value)
        await self._session.flush()
        # session.refresh needed for onupdate=func.now() — M2 lesson #3
        await self._session.refresh(wf)
        return wf

    async def delete(self, wf_id: uuid.UUID) -> bool:
        wf = await self.get(wf_id)
        if wf is None:
            return False
        await self._session.delete(wf)
        await self._session.flush()
        return True
