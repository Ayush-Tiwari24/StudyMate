"""
Unit tests for question rewrite policy:
- Rewrite skipped for self-contained questions.
- Rewrite triggered for follow-ups with pronouns/references or broad topics.
- Empty rewrite falls back gracefully without secondary calls.
- Timeout falls back to original question.
"""

import pytest
import asyncio
from app.services.generation.rag_chain import (
    should_rewrite_question,
    clean_rewritten_query,
    execute_question_rewrite,
)


HISTORY_FIXTURE = [
    {"role": "user", "content": "What is the capital of France?"},
    {"role": "assistant", "content": "The capital of France is Paris."},
]


def test_skip_rewrite_when_no_history():
    """First standalone question should never rewrite."""
    q = "What is the time complexity of merge sort?"
    assert should_rewrite_question(q, history=[], is_broad_query=False, doc_titles=[]) is False


def test_skip_rewrite_for_self_contained_question():
    """Even with previous chat history, self-contained questions must skip rewrite."""
    q = "What is the difference between TCP and UDP?"
    assert should_rewrite_question(q, history=HISTORY_FIXTURE, is_broad_query=False, doc_titles=[]) is False

    q2 = "Explain the time complexity of quicksort in the worst case."
    assert should_rewrite_question(q2, history=HISTORY_FIXTURE, is_broad_query=False, doc_titles=[]) is False


def test_trigger_rewrite_for_pronoun_reference():
    """Short questions with pronouns (it, that, this, them, etc.) must trigger rewrite."""
    q = "Can you explain it in more detail?"
    assert should_rewrite_question(q, history=HISTORY_FIXTURE, is_broad_query=False, doc_titles=[]) is True

    q2 = "What are the main prerequisites for this?"
    assert should_rewrite_question(q2, history=HISTORY_FIXTURE, is_broad_query=False, doc_titles=[]) is True

    q3 = "What about the second one?"
    assert should_rewrite_question(q3, history=HISTORY_FIXTURE, is_broad_query=False, doc_titles=[]) is True


def test_trigger_rewrite_for_broad_queries_with_docs():
    """Broad queries with document titles must trigger rewrite."""
    q = "Give me an overview of this document"
    assert should_rewrite_question(q, history=HISTORY_FIXTURE, is_broad_query=True, doc_titles=["Algorithms"]) is True


def test_clean_rewritten_query_strips_reasoning_and_labels():
    """clean_rewritten_query strips <think> tags, labels, and extracts clean text."""
    raw = "<think>The user wants to know about Dijkstra.</think>\nRewritten question: What is Dijkstra algorithm?"
    cleaned = clean_rewritten_query(raw)
    assert cleaned == "What is Dijkstra algorithm?"

    # Empty output
    empty = "<think>Just thinking with no output</think>"
    assert clean_rewritten_query(empty) == ""


def test_async_rewrite_timeout_fallback():
    """If rewrite takes longer than timeout, it returns None without crashing."""
    # Test with 0.0001s timeout on a prompt
    res = asyncio.run(execute_question_rewrite("Rewrite this prompt", "groq", "openai/gpt-oss-20b", timeout=0.0001))
    assert res is None
