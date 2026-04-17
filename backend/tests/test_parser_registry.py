from __future__ import annotations

from pathlib import Path

import pytest

from app.core.errors import AppError
from app.services.knowledge.parsers import SUPPORTED_EXTENSIONS, get_parser_for


def test_registry_dispatches_known_extensions() -> None:
    from app.services.knowledge.parsers.text import TextParser

    parser = get_parser_for(Path("a.txt"))
    assert isinstance(parser, TextParser)


def test_registry_raises_for_unknown_extension() -> None:
    with pytest.raises(AppError):
        get_parser_for(Path("a.xyz"))


def test_supported_extensions_includes_required_formats() -> None:
    required = {
        "txt",
        "md",
        "html",
        "xml",
        "vtt",
        "pdf",
        "docx",
        "pptx",
        "xlsx",
        "csv",
        "epub",
        "eml",
    }
    assert required.issubset(SUPPORTED_EXTENSIONS)
