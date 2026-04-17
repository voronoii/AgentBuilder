from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field

from app.models.mcp import MCPTransport


class ToolMetadata(BaseModel):
    name: str
    description: str = ""
    input_schema: dict[str, Any] = Field(default_factory=dict)


class MCPServerCreate(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    description: str = ""
    transport: MCPTransport
    config: dict[str, Any] = Field(default_factory=dict)
    env_vars: dict[str, str] = Field(default_factory=dict)


class MCPServerUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=200)
    description: str | None = None
    config: dict[str, Any] | None = None
    env_vars: dict[str, str] | None = None
    enabled: bool | None = None


class MCPServerRead(BaseModel):
    id: uuid.UUID
    name: str
    description: str
    transport: MCPTransport
    config: dict[str, Any]
    env_vars: dict[str, str]
    enabled: bool
    discovered_tools: list[ToolMetadata]
    last_discovered_at: datetime | None
    created_at: datetime
    updated_at: datetime
    model_config = {"from_attributes": True}
