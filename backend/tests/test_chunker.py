"""
Tests — Chunker

Tests for chunk size, overlap, and metadata preservation.
"""

import pytest
from app.services.ingestion.chunker import chunk_pages


def test_basic_chunking():
    """Chunks should be created from page text."""
    pages = [
        {"page": 1, "text": "Hello world. " * 100},  # ~1300 chars
    ]
    chunks = chunk_pages(
        pages=pages,
        document_id=1,
        filename="test.pdf",
        user_id=1,
        chunk_size=900,
        chunk_overlap=150,
    )
    assert len(chunks) >= 1
    assert all("content" in c for c in chunks)
    assert all("metadata" in c for c in chunks)


def test_metadata_preserved():
    """Each chunk should carry correct metadata."""
    pages = [{"page": 3, "text": "Some text content. " * 50}]
    chunks = chunk_pages(
        pages=pages,
        document_id=42,
        filename="notes.pdf",
        user_id=7,
    )
    for chunk in chunks:
        meta = chunk["metadata"]
        assert meta["document_id"] == 42
        assert meta["filename"] == "notes.pdf"
        assert meta["user_id"] == 7
        assert meta["page"] == 3


def test_empty_pages_skipped():
    """Empty pages should not produce chunks."""
    pages = [
        {"page": 1, "text": ""},
        {"page": 2, "text": "   "},
        {"page": 3, "text": "Actual content here."},
    ]
    chunks = chunk_pages(
        pages=pages,
        document_id=1,
        filename="test.pdf",
        user_id=1,
    )
    # Only page 3 has content
    assert all(c["metadata"]["page"] == 3 for c in chunks)


def test_short_text_single_chunk():
    """Text shorter than chunk_size should produce one chunk."""
    pages = [{"page": 1, "text": "Short text."}]
    chunks = chunk_pages(
        pages=pages,
        document_id=1,
        filename="test.pdf",
        user_id=1,
        chunk_size=900,
        chunk_overlap=150,
    )
    assert len(chunks) == 1
    assert chunks[0]["content"] == "Short text."
