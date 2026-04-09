from __future__ import annotations

from pathlib import Path

import pytest

from app.services.knowledge.parsers.eml import EmlParser
from app.services.knowledge.parsers.epub import EpubParser


@pytest.mark.asyncio
async def test_eml_parser(tmp_path: Path) -> None:
    from email.message import EmailMessage

    p = tmp_path / "m.eml"
    msg = EmailMessage()
    msg["Subject"] = "hi"
    msg["From"] = "a@x"
    msg["To"] = "b@x"
    msg.set_content("body contents here")
    p.write_bytes(bytes(msg))
    parsed = await EmlParser().parse(p)
    assert "body contents here" in parsed.text
    assert parsed.metadata["subject"] == "hi"


@pytest.mark.asyncio
async def test_epub_parser_reads_chapters(tmp_path: Path) -> None:
    ebooklib = pytest.importorskip("ebooklib")
    from ebooklib import epub

    book = epub.EpubBook()
    book.set_identifier("id1")
    book.set_title("t")
    book.set_language("en")
    ch = epub.EpubHtml(title="c", file_name="c.xhtml", lang="en")
    ch.content = "<html><body><p>chapter body text</p></body></html>"
    book.add_item(ch)
    book.toc = (ch,)
    book.spine = ["nav", ch]
    book.add_item(epub.EpubNav())
    book.add_item(epub.EpubNcx())
    p = tmp_path / "b.epub"
    epub.write_epub(str(p), book)
    parsed = await EpubParser().parse(p)
    assert "chapter body text" in parsed.text
