from __future__ import annotations

import asyncio
from email import policy
from email.parser import BytesParser
from pathlib import Path

from app.services.knowledge.parsers.base import ParsedDocument


class EmlParser:
    async def parse(self, path: Path) -> ParsedDocument:
        loop = asyncio.get_running_loop()
        return await loop.run_in_executor(None, self._parse_sync, path)

    def _parse_sync(self, path: Path) -> ParsedDocument:
        with path.open("rb") as fh:
            msg = BytesParser(policy=policy.default).parse(fh)
        body_part = msg.get_body(preferencelist=("plain", "html"))
        body = body_part.get_content() if body_part is not None else ""
        meta = {
            "subject": msg.get("subject", ""),
            "from": msg.get("from", ""),
            "to": msg.get("to", ""),
            "filename": path.name,
        }
        text = f"Subject: {meta['subject']}\nFrom: {meta['from']}\nTo: {meta['to']}\n\n{body}"
        return ParsedDocument(text=text, metadata=meta)
