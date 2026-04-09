from __future__ import annotations

import asyncio
from pathlib import Path

from bs4 import BeautifulSoup
from ebooklib import ITEM_DOCUMENT, epub

from app.services.knowledge.parsers.base import ParsedDocument


class EpubParser:
    async def parse(self, path: Path) -> ParsedDocument:
        loop = asyncio.get_running_loop()
        return await loop.run_in_executor(None, self._parse_sync, path)

    def _parse_sync(self, path: Path) -> ParsedDocument:
        book = epub.read_epub(str(path))
        chapters: list[str] = []
        for item in book.get_items_of_type(ITEM_DOCUMENT):
            soup = BeautifulSoup(item.get_content(), "html.parser")
            text = soup.get_text(separator="\n").strip()
            if text:
                chapters.append(text)
        return ParsedDocument(
            text="\n\n".join(chapters),
            metadata={"chapter_count": len(chapters), "filename": path.name},
        )
