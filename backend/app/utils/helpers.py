"""
StudyMate RAG — General Helpers

Miscellaneous utility functions used across the application.
"""

from typing import Any


def truncate_text(text: str, max_length: int = 200) -> str:
    """Truncate text to max_length characters, adding ellipsis if truncated."""
    if len(text) <= max_length:
        return text
    return text[:max_length - 3] + "..."


def build_error_response(code: str, message: str) -> dict[str, Any]:
    """
    Build a standardized error response body.
    Matches the spec format: { "error": { "code": "...", "message": "..." } }
    """
    return {"error": {"code": code, "message": message}}
