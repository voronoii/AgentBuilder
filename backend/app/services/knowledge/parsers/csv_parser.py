from __future__ import annotations

import asyncio
import csv
from pathlib import Path

from app.services.knowledge.parsers.base import ParsedDocument


class CsvParser:
    async def parse(self, path: Path) -> ParsedDocument:
        loop = asyncio.get_running_loop()
        return await loop.run_in_executor(None, self._parse_sync, path)

    def _parse_sync(self, path: Path) -> ParsedDocument:
        rows: list[list[str]] = []
        with path.open("r", encoding="utf-8", newline="") as fh:
            reader = csv.reader(fh)
            header = next(reader, None)
            for row in reader:
                rows.append(row)
        lines: list[str] = []
        if header:
            lines.append(" | ".join(header))
        for r in rows:
            lines.append(" | ".join(r))
        return ParsedDocument(
            text="\n".join(lines),
            metadata={"row_count": len(rows), "filename": path.name},
        )
