from collections.abc import Mapping

from .base import BaseParser

IMAGE_EXTENSIONS = frozenset(
    {".png", ".jpg", ".jpeg", ".webp", ".bmp", ".tiff", ".tif", ".gif"}
)


async def select_parser(
    ext: str,
    *,
    extraction_config: Mapping | None = None,
) -> BaseParser:
    """Choose a parser for one file extension.

    When ``tika_url`` is configured the external Tika service handles every
    format. Otherwise image files use the optional OCR parser only when
    ``ocr_enable`` is set, and built-in parsers handle the rest.

    Args:
        ext: Lower-case file extension including the dot.
        extraction_config: Optional ``knowledge_base.extraction`` mapping.

    Returns:
        A parser instance for the extension.

    Raises:
        ValueError: If no parser handles the extension.
    """
    config = extraction_config or {}
    tika_url = str(config.get("tika_url") or "").strip()
    if tika_url:
        from .tika_parser import TikaParser

        return TikaParser(tika_url)

    if ext in IMAGE_EXTENSIONS and config.get("ocr_enable"):
        from .ocr_parser import ImageOCRParser

        return ImageOCRParser(languages=str(config.get("ocr_languages") or "eng"))

    if ext in {".md", ".txt", ".markdown", ".rst", ".adoc", ".xlsx", ".docx", ".xls"}:
        from .markitdown_parser import MarkitdownParser

        return MarkitdownParser()
    if ext == ".epub":
        from .epub_parser import EpubParser

        return EpubParser()
    if ext == ".pdf":
        from .pdf_parser import PDFParser

        return PDFParser()
    raise ValueError(f"暂时不支持的文件格式: {ext}")
