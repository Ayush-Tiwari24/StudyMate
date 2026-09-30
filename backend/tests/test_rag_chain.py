"""
Tests — RAG Chain

Tests for citation presence and "not found" fallback.
Note: Full RAG chain tests require LLM access.
"""

import pytest
from app.services.generation.prompts import build_answer_prompt, build_rewrite_prompt


def test_answer_prompt_has_citations():
    """Answer prompt should include numbered context."""
    chunks = [
        {"content": "Normalization reduces redundancy.", "metadata": {"filename": "dbms.pdf", "page": 14}},
        {"content": "1NF requires atomic values.", "metadata": {"filename": "dbms.pdf", "page": 15}},
    ]
    prompt = build_answer_prompt(chunks, "What is normalization?")

    assert "[1]" in prompt
    assert "[2]" in prompt
    assert "dbms.pdf" in prompt
    assert "p.14" in prompt
    assert "What is normalization?" in prompt


def test_rewrite_prompt_includes_history():
    """Rewrite prompt should include chat history."""
    history = [
        {"role": "user", "content": "What is normalization?"},
        {"role": "assistant", "content": "Normalization is..."},
    ]
    prompt = build_rewrite_prompt(history, "What about its types?")

    assert "What about its types?" in prompt
    assert "What is normalization?" in prompt


def test_rewrite_prompt_empty_history():
    """Rewrite prompt should handle empty history gracefully."""
    prompt = build_rewrite_prompt([], "What is ACID?")
    assert "no prior messages" in prompt
    assert "What is ACID?" in prompt
