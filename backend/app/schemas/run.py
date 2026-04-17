from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel

from app.models.run import RunStatus


class RunCreate(BaseModel):
    input: dict[str, Any] = {}


class RunRead(BaseModel):
    id: uuid.UUID
    workflow_id: uuid.UUID
    status: RunStatus
    started_at: datetime
    ended_at: datetime | None
    input: dict[str, Any]
    output: dict[str, Any] | None
    error: str | None

    model_config = {"from_attributes": True}


class RunEventRead(BaseModel):
    id: uuid.UUID
    run_id: uuid.UUID
    timestamp: datetime
    event_type: str
    node_id: str | None
    payload: dict[str, Any]

    model_config = {"from_attributes": True}


class RunSummary(BaseModel):
    id: uuid.UUID
    status: RunStatus
    started_at: datetime
    ended_at: datetime | None
    error: str | None = None

    model_config = {"from_attributes": True}
