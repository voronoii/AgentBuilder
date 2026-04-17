from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class AppCreate(BaseModel):
    workflow_id: uuid.UUID
    name: str = Field(min_length=1, max_length=200)
    description: str = ""
    icon_url: str | None = None
    welcome_message: str = "안녕하세요! 무엇을 도와드릴까요?"
    placeholder_text: str = "메시지를 입력하세요..."


class AppUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=200)
    description: str | None = None
    icon_url: str | None = None
    welcome_message: str | None = None
    placeholder_text: str | None = None


class AppRead(BaseModel):
    id: uuid.UUID
    workflow_id: uuid.UUID
    name: str
    description: str
    icon_url: str | None
    welcome_message: str
    placeholder_text: str
    api_key: str
    is_active: bool
    created_at: datetime
    updated_at: datetime
    model_config = ConfigDict(from_attributes=True)


class AppConfig(BaseModel):
    id: uuid.UUID
    name: str
    description: str
    icon_url: str | None
    welcome_message: str
    placeholder_text: str
    model_config = ConfigDict(from_attributes=True)
