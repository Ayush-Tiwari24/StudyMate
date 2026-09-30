"""
StudyMate RAG — Utility Functions: File Handling

Hashing, safe filenames, and file I/O helpers.
"""

import hashlib
import re
import uuid
from pathlib import Path


def compute_sha256(file_bytes: bytes) -> str:
    """Compute SHA-256 hash of file content for deduplication."""
    return hashlib.sha256(file_bytes).hexdigest()


def safe_filename(filename: str) -> str:
    """
    Sanitize a filename: keep only alphanumerics, dots, hyphens, underscores.
    Prepend a short UUID to avoid collisions.
    """
    # Strip path components
    name = Path(filename).name
    # Remove unsafe characters
    name = re.sub(r"[^\w.\-]", "_", name)
    # Prepend short UUID
    prefix = uuid.uuid4().hex[:8]
    return f"{prefix}_{name}"


def ensure_dir(path: Path) -> Path:
    """Create directory (and parents) if it doesn't exist. Returns the path."""
    path.mkdir(parents=True, exist_ok=True)
    return path
