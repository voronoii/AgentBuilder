from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class ReactFlowNode(BaseModel):
    id: str
    type: str
    position: dict[str, Any]
    data: dict[str, Any]
    model_config = ConfigDict(extra="allow")


class ReactFlowEdge(BaseModel):
    id: str | None = None
    source: str
    target: str
    sourceHandle: str | None = None
    targetHandle: str | None = None
    model_config = ConfigDict(extra="allow")


class WorkflowCreate(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    description: str = ""
    nodes: list[ReactFlowNode] = Field(default_factory=list)
    edges: list[ReactFlowEdge] = Field(default_factory=list)


class WorkflowUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=200)
    description: str | None = None
    nodes: list[ReactFlowNode] | None = None
    edges: list[ReactFlowEdge] | None = None


class WorkflowRead(BaseModel):
    id: uuid.UUID
    name: str
    description: str
    nodes: list[dict[str, Any]]
    edges: list[dict[str, Any]]
    created_at: datetime
    updated_at: datetime
    model_config = ConfigDict(from_attributes=True)


class WorkflowValidationWarning(BaseModel):
    code: str
    message: str


class WorkflowValidationResult(BaseModel):
    valid: bool
    warnings: list[WorkflowValidationWarning]
