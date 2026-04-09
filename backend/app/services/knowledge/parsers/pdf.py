from __future__ import annotations

import asyncio
from pathlib import Path

from pypdf import PdfReader

from app.services.knowledge.parsers.base import ParsedDocument


class PdfParser:
    async def parse(self, path: Path) -> ParsedDocument:
        loop = asyncio.get_running_loop()
        return await loop.run_in_executor(None, self._parse_sync, path)

    def _parse_sync(self, path: Path) -> ParsedDocument:
        reader = PdfReader(str(path))
        pages: list[str] = []
        for page in reader.pages:
            try:
                pages.append(page.extract_text() or "")
            except Exception:
                pages.append("")
        text = "\n\n".join(p for p in pages if p.strip())
        return ParsedDocument(
            text=text,
            metadata={"page_count": len(reader.pages), "filename": path.name},
        )
