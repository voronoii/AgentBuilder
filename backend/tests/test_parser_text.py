from __future__ import annotations

from pathlib import Path

import pytest

from app.services.knowledge.parsers.text import TextParser

FIX = Path(__file__).parent / "fixtures"


@pytest.mark.asyncio
async def test_text_parser_reads_utf8() -> None:
    parsed = await TextParser().parse(FIX / "sample.txt")
    assert "안녕하세요" in parsed.text
    assert parsed.metadata["char_count"] > 0


@pytest.mark.asyncio
async def test_markdown_parser_strips_nothing() -> None:
    parsed = await TextParser().parse(FIX / "sample.md")
    assert "Sample" in parsed.text
