from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Protocol, runtime_checkable


@dataclass(frozen=True)
class ParsedDocument:
    text: str
    metadata: dict[str, Any] = field(default_factory=dict)


@runtime_checkable
class Parser(Protocol):
    async def parse(self, path: Path) -> ParsedDocument: ...
