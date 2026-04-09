from __future__ import annotations

from pathlib import Path

from app.core.errors import AppError, ErrorCode
from app.services.knowledge.parsers.base import ParsedDocument, Parser
from app.services.knowledge.parsers.csv_parser import CsvParser
from app.services.knowledge.parsers.docx import DocxParser
from app.services.knowledge.parsers.eml import EmlParser
from app.services.knowledge.parsers.epub import EpubParser
from app.services.knowledge.parsers.pdf import PdfParser
from app.services.knowledge.parsers.pptx import PptxParser
from app.services.knowledge.parsers.text import TextParser
from app.services.knowledge.parsers.xlsx import XlsxParser

_TEXT_EXTS = {"txt", "md", "mdx", "html", "htm", "xml", "vtt", "properties"}
_REGISTRY: dict[str, Parser] = {
    **{ext: TextParser() for ext in _TEXT_EXTS},
    "pdf": PdfParser(),
    "docx": DocxParser(),
    "pptx": PptxParser(),
    "xlsx": XlsxParser(),
    "csv": CsvParser(),
    "epub": EpubParser(),
    "eml": EmlParser(),
}
SUPPORTED_EXTENSIONS: frozenset[str] = frozenset(_REGISTRY.keys())


def get_parser_for(path: Path) -> Parser:
    ext = path.suffix.lstrip(".").lower()
    if ext not in _REGISTRY:
        raise AppError(
            status_code=415,
            code=ErrorCode.KNOWLEDGE_UNSUPPORTED_FILE,
            detail=f"unsupported file extension: .{ext}",
        )
    return _REGISTRY[ext]


__all__ = ["ParsedDocument", "Parser", "SUPPORTED_EXTENSIONS", "get_parser_for"]
