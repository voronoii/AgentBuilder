from __future__ import annotations

import enum
import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, String, Text, func
from sqlalchemy import Enum as SaEnum
from sqlalchemy.dialects.postgresql import JSON
from sqlalchemy.dialects.postgresql import UUID as PgUUID  # noqa: N811
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class MCPTransport(enum.StrEnum):
    STDIO = "stdio"
    HTTP_SSE = "http_sse"
    STREAMABLE_HTTP = "streamable_http"


class MCPServer(Base):
    __tablename__ = "mcp_servers"

    id: Mapped[uuid.UUID] = mapped_column(
        PgUUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    name: Mapped[str] = mapped_column(String(200), nullable=False, unique=True)
    description: Mapped[str] = mapped_column(Text, default="", nullable=False)

    transport: Mapped[MCPTransport] = mapped_column(
        SaEnum(
            MCPTransport,
            name="mcp_transport",
            values_callable=lambda e: [x.value for x in e],
            create_constraint=True,
        ),
        nullable=False,
    )

    # Transport-specific config:
    # STDIO: {"command": "npx", "args": [...]}
    # HTTP_SSE: {"url": "https://...", "headers": {...}}
    config: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)

    # Environment variables passed to the MCP process/request
    env_vars: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)

    enabled: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    # Cached tool list from last successful discovery
    # Each entry: {"name": str, "description": str, "input_schema": dict}
    discovered_tools: Mapped[list] = mapped_column(JSON, nullable=False, default=list)

    last_discovered_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )
