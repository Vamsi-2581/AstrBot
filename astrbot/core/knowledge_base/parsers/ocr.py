"""Optional OCR helper backed by Tesseract via ``pytesseract``.

The engine is imported lazily so the base install stays lean. Operators enable
OCR explicitly and install ``pytesseract`` plus the Tesseract binary; when the
engine is missing the caller receives a clear, user-facing error.
"""

from __future__ import annotations

import asyncio
import io


class OCREngineUnavailable(RuntimeError):
    """Raised when OCR is requested but the optional engine is not installed."""


def _run_ocr(content: bytes, languages: str) -> str:
    try:
        import pytesseract
        from PIL import Image
    except Exception as exc:  # pragma: no cover - import guard
        raise OCREngineUnavailable(
            "OCR is enabled but pytesseract/Pillow is not installed"
        ) from exc

    with Image.open(io.BytesIO(content)) as image:
        try:
            return pytesseract.image_to_string(image, lang=languages or "eng")
        except Exception as exc:
            raise OCREngineUnavailable(f"OCR engine failed: {exc}") from exc


async def ocr_image_bytes(content: bytes, languages: str = "eng") -> str:
    """Run OCR on one image off the event loop.

    Args:
        content: Raw image bytes.
        languages: Tesseract language specification, for example ``eng``.

    Returns:
        Recognized text, possibly empty.

    Raises:
        OCREngineUnavailable: If the optional OCR engine is missing or fails.
    """
    return await asyncio.to_thread(_run_ocr, content, languages)
