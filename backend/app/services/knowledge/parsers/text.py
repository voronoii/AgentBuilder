from __future__ import annotations

from pathlib import Path

from app.services.knowledge.parsers.base import ParsedDocument


def _read_with_fallback(path: Path) -> str:
    for encoding in ("utf-8", "utf-8-sig", "cp949", "latin-1"):
        try:
            return path.read_text(encoding=encoding)
        except UnicodeDecodeError:
            continue
    return path.read_bytes().decode("utf-8", errors="replace")


class TextParser:
    async def parse(self, path: Path) -> ParsedDocument:
        text = _read_with_fallback(path)
        return ParsedDocument(text=text, metadata={"char_count": len(text), "filename": path.name})
