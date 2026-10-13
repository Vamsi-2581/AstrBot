"""Image parser that extracts text with the optional OCR engine."""

from __future__ import annotations

import mimetypes

from astrbot.core.knowledge_base.parsers.base import (
    BaseParser,
    MediaItem,
    ParseResult,
)
from astrbot.core.knowledge_base.parsers.ocr import ocr_image_bytes


class ImageOCRParser(BaseParser):
    """OCR images and scanned pages into text.

    The engine is optional; when it is unavailable ``parse`` raises
    :class:`~astrbot.core.knowledge_base.parsers.ocr.OCREngineUnavailable` so the
    upload path can report a precise error.
    """

    def __init__(self, languages: str = "eng") -> None:
        self.languages = languages or "eng"

    async def parse(self, file_content: bytes, file_name: str) -> ParseResult:
        """OCR one image into text.

        Args:
            file_content: Raw image bytes.
            file_name: Original file name, used for the media item.

        Returns:
            ParseResult with recognized text and the original image as media.
        """
        text = await ocr_image_bytes(file_content, self.languages)
        guessed, _encoding = mimetypes.guess_type(file_name)
        media = [
            MediaItem(
                media_type="image",
                file_name=file_name,
                content=file_content,
                mime_type=guessed or "application/octet-stream",
            )
        ]
        return ParseResult(text=text, media=media)
