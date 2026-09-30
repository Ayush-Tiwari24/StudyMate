"""
Tests — Retriever

Tests for chunk retrieval, filtering, and user isolation.
Note: These tests require the embedding model and ChromaDB to be available.
"""

import pytest


def test_retrieve_returns_list():
    """Retriever should return a list (even if empty)."""
    # This is a placeholder — full integration test requires
    # embedding model + seeded vector store
    from app.services.retrieval.retriever import retrieve_chunks

    # With no documents ingested, should return empty list
    result = retrieve_chunks(
        question="test question",
        user_id=999,
        document_ids=[999],
    )
    assert isinstance(result, list)


def test_reranker_disabled_passthrough():
    """When reranking is disabled, rerank_chunks should return input unchanged."""
    from app.services.retrieval.reranker import rerank_chunks

    chunks = [
        {"content": "chunk 1", "score": 0.9, "metadata": {}},
        {"content": "chunk 2", "score": 0.8, "metadata": {}},
    ]
    result = rerank_chunks("test", chunks, top_n=5)
    assert len(result) == 2
