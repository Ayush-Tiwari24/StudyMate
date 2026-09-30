"""
StudyMate RAG — OCR Fallback Service

For scanned PDFs where direct text extraction yields little or no content.
Uses RapidOCR (pure ONNX Runtime OCR, no external binaries required)
with optional fallback to ocrmypdf/tesseract.
"""

from pathlib import Path
from typing import Callable, Optional
import pymupdf as fitz

from app.core.logger import logger

# Minimum characters per page to consider text extraction successful
MIN_TEXT_LENGTH = 30

_rapid_ocr_engine = None


def _get_ocr_engine():
    """Lazy load RapidOCR engine singleton."""
    global _rapid_ocr_engine
    if _rapid_ocr_engine is None:
        try:
            from rapidocr_onnxruntime import RapidOCR
            _rapid_ocr_engine = RapidOCR()
            logger.info("RapidOCR ONNX engine initialized successfully.")
        except Exception as e:
            logger.warning(f"Could not initialize RapidOCR: {e}")
            _rapid_ocr_engine = False
    return _rapid_ocr_engine if _rapid_ocr_engine is not False else None


def needs_ocr(page_text: str) -> bool:
    """Check if a page's extracted text is too short, suggesting a scan."""
    return len(page_text.strip()) < MIN_TEXT_LENGTH


def ocr_pdf_pages(
    file_path: str | Path,
    pages_to_ocr: Optional[set[int]] = None,
    progress_callback: Optional[Callable[[int, int], None]] = None,
) -> list[dict]:
    """
    Extract text using OCR page-by-page.
    
    Args:
        file_path: Path to the PDF file.
        pages_to_ocr: Set of 1-indexed page numbers to OCR (or None to OCR all pages).
        progress_callback: Optional function (current_page, total_pages) -> None.
        
    Returns:
        List of {"page": int, "text": str} dicts.
    """
    file_path = Path(file_path)
    ocr_engine = _get_ocr_engine()

    results = []
    doc = fitz.open(str(file_path))
    total_pages = len(doc)

    for i in range(total_pages):
        page_num = i + 1  # 1-indexed
        
        # If specific pages requested, skip others
        if pages_to_ocr is not None and page_num not in pages_to_ocr:
            text = doc[i].get_text("text").strip()
            results.append({"page": page_num, "text": text})
            continue

        page_text = ""

        if ocr_engine:
            try:
                # Render page to pixmap at 100 DPI for fast and accurate OCR
                pix = doc[i].get_pixmap(dpi=100)
                img_bytes = pix.tobytes("png")
                ocr_res, _ = ocr_engine(img_bytes)
                if ocr_res:
                    # ocr_res is list of [box, text, confidence]
                    page_text = "\n".join(r[1] for r in ocr_res if r[1].strip())
            except Exception as e:
                logger.warning(f"RapidOCR failed on page {page_num} of {file_path.name}: {e}")

        # If OCR was empty or failed, fallback to native text extraction
        if not page_text:
            page_text = doc[i].get_text("text").strip()

        results.append({"page": page_num, "text": page_text})

        if progress_callback:
            try:
                progress_callback(page_num, total_pages)
            except Exception:
                pass

        if (i + 1) % 10 == 0 or (i + 1) == total_pages:
            logger.info(f"OCR progress for {file_path.name}: {i + 1}/{total_pages} pages")

    doc.close()
    return results


def ocr_pdf(file_path: str | Path) -> str | None:
    """Legacy helper for backward compatibility."""
    return None
