"""
StudyMate RAG — Text Cleaner

Cleans extracted PDF text: removes repeated headers/footers,
page numbers, fixes broken hyphenation, and normalizes whitespace.
"""

import re
from collections import Counter

from app.core.logger import logger


def clean_pages(pages: list[dict]) -> list[dict]:
    """
    Clean extracted text across all pages.

    Steps:
    1. Remove repeated headers/footers (lines appearing on >50% of pages)
    2. Remove standalone page numbers
    3. Fix broken hyphenation (word- \\n continuation)
    4. Normalize whitespace

    Args:
        pages: List of {"page": int, "text": str}

    Returns:
        Same structure with cleaned text.
    """
    if not pages:
        return pages

    # Step 1: Identify repeated headers/footers
    repeated_lines = _find_repeated_lines(pages)

    cleaned = []
    for page_data in pages:
        text = page_data["text"]

        # Remove repeated header/footer lines
        text = _remove_repeated_lines(text, repeated_lines)

        # Remove standalone page numbers (e.g., "  42  " on its own line)
        text = re.sub(r"^\s*\d{1,4}\s*$", "", text, flags=re.MULTILINE)

        # Fix broken hyphenation: "exam-\nple" → "example"
        text = re.sub(r"(\w)-\s*\n\s*(\w)", r"\1\2", text)

        # Normalize multiple blank lines to single
        text = re.sub(r"\n{3,}", "\n\n", text)

        # Normalize spaces (but preserve newlines)
        text = re.sub(r"[^\S\n]+", " ", text)

        text = text.strip()

        cleaned.append({
            "page": page_data["page"],
            "text": text,
        })

    logger.info(f"Cleaned {len(cleaned)} pages")
    return cleaned


def _find_repeated_lines(pages: list[dict], threshold: float = 0.5) -> set[str]:
    """
    Find lines that appear on more than `threshold` fraction of pages.
    These are likely headers or footers.
    """
    line_counter: Counter = Counter()
    total_pages = len(pages)

    for page_data in pages:
        # Get unique lines per page (so a repeated line within one page counts once)
        lines = set()
        for line in page_data["text"].split("\n"):
            stripped = line.strip()
            if stripped and len(stripped) > 3:  # Ignore very short lines
                lines.add(stripped)
        for line in lines:
            line_counter[line] += 1

    # Lines appearing on more than threshold of pages
    repeated = {
        line
        for line, count in line_counter.items()
        if count / total_pages > threshold and total_pages > 2
    }

    if repeated:
        logger.info(f"Found {len(repeated)} repeated header/footer lines")

    return repeated


def _remove_repeated_lines(text: str, repeated: set[str]) -> str:
    """Remove lines identified as repeated headers/footers."""
    if not repeated:
        return text

    lines = text.split("\n")
    filtered = [line for line in lines if line.strip() not in repeated]
    return "\n".join(filtered)
