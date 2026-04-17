from __future__ import annotations

import uuid
from typing import Annotated, Any

from fastapi import APIRouter, Depends, status
from fastapi.responses import Response
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_session
from app.core.errors import AppError, ErrorCode
from app.models.workflow import Workflow
from app.repositories.workflow import WorkflowRepository
from app.schemas.workflow import (
    WorkflowCreate,
    WorkflowRead,
    WorkflowUpdate,
    WorkflowValidationResult,
    WorkflowValidationWarning,
)
from app.seed.demo_workflows import ALL_DEMOS

router = APIRouter(prefix="/workflows", tags=["workflows"])


def _validate_workflow(
    nodes: list[dict[str, Any]],
    edges: list[dict[str, Any]],  # noqa: ARG001
) -> WorkflowValidationResult:
    """Warning-level validation: check ChatInput/ChatOutput presence."""
    warnings: list[WorkflowValidationWarning] = []
    node_types = [n.get("data", {}).get("type") or n.get("type", "") for n in nodes]

    if "chat_input" not in node_types:
        warnings.append(
            WorkflowValidationWarning(
                code="MISSING_CHAT_INPUT",
                message="워크플로우에 ChatInput 노드가 없습니다.",
            )
        )
    if "chat_output" not in node_types:
        warnings.append(
            WorkflowValidationWarning(
                code="MISSING_CHAT_OUTPUT",
                message="워크플로우에 ChatOutput 노드가 없습니다.",
            )
        )

    return WorkflowValidationResult(valid=len(warnings) == 0, warnings=warnings)


# ---------- CRUD ----------


@router.post("", response_model=WorkflowRead, status_code=status.HTTP_201_CREATED)
async def create_workflow(
    payload: WorkflowCreate,
    session: Annotated[AsyncSession, Depends(get_session)],
) -> Workflow:
    repo = WorkflowRepository(session)
    try:
        wf = await repo.create(payload)
        await session.commit()
    except IntegrityError as exc:
        raise AppError(
            status_code=409,
            code=ErrorCode.WORKFLOW_DUPLICATE_NAME,
            detail=f"'{payload.name}' 이름의 워크플로우가 이미 존재합니다.",
        ) from exc
    return wf


@router.get("", response_model=list[WorkflowRead])
async def list_workflows(
    session: Annotated[AsyncSession, Depends(get_session)],
) -> list[Workflow]:
    return await WorkflowRepository(session).list_all()


@router.get("/{wf_id}", response_model=WorkflowRead)
async def get_workflow(
    wf_id: uuid.UUID,
    session: Annotated[AsyncSession, Depends(get_session)],
) -> Workflow:
    wf = await WorkflowRepository(session).get(wf_id)
    if wf is None:
        raise AppError(
            status_code=404,
            code=ErrorCode.WORKFLOW_NOT_FOUND,
            detail="워크플로우를 찾을 수 없습니다.",
        )
    return wf


@router.put("/{wf_id}", response_model=WorkflowRead)
async def update_workflow(
    wf_id: uuid.UUID,
    payload: WorkflowUpdate,
    session: Annotated[AsyncSession, Depends(get_session)],
) -> Workflow:
    repo = WorkflowRepository(session)
    try:
        wf = await repo.update(wf_id, payload)
    except IntegrityError as exc:
        raise AppError(
            status_code=409,
            code=ErrorCode.WORKFLOW_DUPLICATE_NAME,
            detail=f"'{payload.name}' 이름의 워크플로우가 이미 존재합니다.",
        ) from exc
    if wf is None:
        raise AppError(
            status_code=404,
            code=ErrorCode.WORKFLOW_NOT_FOUND,
            detail="워크플로우를 찾을 수 없습니다.",
        )
    await session.commit()
    return wf


@router.delete("/{wf_id}", status_code=status.HTTP_204_NO_CONTENT, response_class=Response)
async def delete_workflow(
    wf_id: uuid.UUID,
    session: Annotated[AsyncSession, Depends(get_session)],
) -> Response:
    deleted = await WorkflowRepository(session).delete(wf_id)
    if not deleted:
        raise AppError(
            status_code=404,
            code=ErrorCode.WORKFLOW_NOT_FOUND,
            detail="워크플로우를 찾을 수 없습니다.",
        )
    await session.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)


# ---------- Validation ----------


@router.post("/{wf_id}/validate", response_model=WorkflowValidationResult)
async def validate_workflow(
    wf_id: uuid.UUID,
    session: Annotated[AsyncSession, Depends(get_session)],
) -> WorkflowValidationResult:
    wf = await WorkflowRepository(session).get(wf_id)
    if wf is None:
        raise AppError(
            status_code=404,
            code=ErrorCode.WORKFLOW_NOT_FOUND,
            detail="워크플로우를 찾을 수 없습니다.",
        )
    return _validate_workflow(wf.nodes, wf.edges)


# ---------- Seed ----------


@router.post("/seed", status_code=status.HTTP_201_CREATED)
async def seed_demo_workflows(
    session: Annotated[AsyncSession, Depends(get_session)],
) -> dict[str, list[str]]:
    """Insert demo workflows if they don't already exist (idempotent by name).

    Returns a dict with two keys:
    - ``created``: names of workflows inserted in this call.
    - ``skipped``: names that already existed and were left untouched.
    """
    repo = WorkflowRepository(session)
    created: list[str] = []
    skipped: list[str] = []

    for demo in ALL_DEMOS:
        name: str = demo["name"]

        # Check existence by name (name has a UNIQUE constraint in the DB)
        existing = await session.execute(
            select(Workflow).where(Workflow.name == name).limit(1)
        )
        if existing.scalar_one_or_none() is not None:
            skipped.append(name)
            continue

        payload = WorkflowCreate(**demo)
        await repo.create(payload)
        created.append(name)

    await session.commit()
    return {"created": created, "skipped": skipped}
