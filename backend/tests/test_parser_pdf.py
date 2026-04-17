from __future__ import annotations

from pathlib import Path

import pytest

from app.services.knowledge.parsers.pdf import PdfParser


@pytest.fixture
def sample_pdf(tmp_path: Path) -> Path:
    pytest.importorskip("reportlab")
    from reportlab.pdfgen import canvas

    p = tmp_path / "sample.pdf"
    c = canvas.Canvas(str(p))
    c.drawString(100, 750, "Hello PDF world")
    c.drawString(100, 730, "Second line here")
    c.save()
    return p


@pytest.mark.asyncio
async def test_pdf_parser_extracts_text(sample_pdf: Path) -> None:
    parsed = await PdfParser().parse(sample_pdf)
    assert "Hello PDF world" in parsed.text
    assert parsed.metadata["page_count"] == 1
