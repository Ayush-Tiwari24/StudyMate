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


def test_extract_keywords():
    """Keyword extractor should filter out stopwords and return meaningful tokens."""
    from app.services.retrieval.retriever import _extract_keywords

    tokens = _extract_keywords("what are certification acheived in this profile")
    assert "certification" in tokens
    assert "acheived" in tokens
    assert "profile" in tokens
    assert "what" not in tokens
    assert "are" not in tokens
    assert "this" not in tokens


def test_mmr_selection_diversifies():
    from app.services.retrieval.retriever import _calculate_mmr

    candidates = [
        {"content": "Dijkstra algorithm finds shortest paths in a weighted graph.", "score": 0.95},
        {"content": "Dijkstra algorithm finds shortest paths in a graph with weights.", "score": 0.94},
        {"content": "Bellman-Ford algorithm handles graphs with negative edge weights.", "score": 0.88},
    ]
    selected = _calculate_mmr(candidates, top_k=2, lambda_param=0.5)
    assert len(selected) == 2
    assert selected[0]["content"] == candidates[0]["content"]
    assert "Bellman-Ford" in selected[1]["content"]


