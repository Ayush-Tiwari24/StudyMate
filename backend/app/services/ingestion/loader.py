"""
StudyMate RAG — PDF Loader

Extracts text from PDF files page by page using PyMuPDF (fitz).
Returns a list of {page, text} dicts.
"""

from pathlib import Path

import fitz  # PyMuPDF

from app.core.logger import logger


def load_pdf(file_path: str | Path) -> list[dict]:
    """
    Extract text from a PDF file, page by page.

    Returns:
        List of dicts: [{"page": 1, "text": "..."}, ...]
        Page numbers are 1-indexed.
    """
    file_path = Path(file_path)
    pages = []

    try:
        doc = fitz.open(str(file_path))

        for page_num in range(len(doc)):
            page = doc[page_num]
            text = page.get_text("text")

            pages.append({
                "page": page_num + 1,  # 1-indexed
                "text": text.strip(),
            })

        doc.close()
        logger.info(f"Loaded PDF: {file_path.name} — {len(pages)} pages")

    except Exception as e:
        logger.error(f"Failed to load PDF {file_path}: {e}")
        raise

    return pages


def get_page_count(file_path: str | Path) -> int:
    """Get the total number of pages in a PDF without extracting text."""
    doc = fitz.open(str(file_path))
    count = len(doc)
    doc.close()
    return count
