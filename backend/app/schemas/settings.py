from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel


class SettingRead(BaseModel):
    key: str
    value: str
    description: str
    category: str
    is_secret: bool
    updated_at: datetime
    model_config = {"from_attributes": True}


class SettingCreate(BaseModel):
    key: str
    value: str = ""
    description: str = ""
    category: str = "general"
    is_secret: bool = False


class SettingUpdate(BaseModel):
    value: str


class SettingBulkUpdate(BaseModel):
    settings: dict[str, str]  # key -> value
