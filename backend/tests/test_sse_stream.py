"""
Tests — SSE Streaming & Reasoning Token Filter

Verifies:
1. ReasoningFilter completely strips <think>...</think> and <thought>...</thought> tags and internal thoughts.
2. ReasoningFilter handles split tags across streaming chunk boundaries.
3. clean_rewritten_query strips thought blocks, preambles, and extra lines.
4. Cited sources filtering retains only sources with inline [X] markers in the final answer.
"""

from unittest.mock import MagicMock
from app.services.generation.rag_chain import ReasoningFilter, CitationFilter, clean_rewritten_query


def test_reasoning_filter_simple_block():
    rfilter = ReasoningFilter()
    chunk1 = MagicMock(content="<think>Evaluating graph theory concepts.</think>Dijkstra algorithm finds shortest paths.")
    out1 = rfilter.process_chunk(chunk1)
    tail = rfilter.flush()
    assert out1 + tail == "Dijkstra algorithm finds shortest paths."


def test_reasoning_filter_split_across_chunks():
    rfilter = ReasoningFilter()
    # Tag split: "<thi" then "nk> thinking </thi" then "nk> Answer"
    out1 = rfilter.process_chunk(MagicMock(content="Prefix text <thi"))
    out2 = rfilter.process_chunk(MagicMock(content="nk> Internal reasoning step 1 </thi"))
    out3 = rfilter.process_chunk(MagicMock(content="nk> Final answer text."))
    tail = rfilter.flush()

    total = out1 + out2 + out3 + tail
    assert "<think>" not in total
    assert "</think>" not in total
    assert "Internal reasoning" not in total
    assert total.strip() == "Prefix text  Final answer text."


def test_clean_rewritten_query():
    raw_with_think = """<think>
The student is asking about Prim's and Kruskal's algorithms for minimum spanning trees.
</think>
Optimized Search Query: "What is the difference between Prim's and Kruskal's algorithms?"
"""
    clean = clean_rewritten_query(raw_with_think)
    assert clean == "What is the difference between Prim's and Kruskal's algorithms?"
    assert "<think>" not in clean
    assert "Optimized Search Query:" not in clean


def test_clean_rewritten_query_plain():
    clean = clean_rewritten_query("How does binary search work?")
    assert clean == "How does binary search work?"


def test_citation_filter_simple_markers():
    cfilter = CitationFilter()
    text = "The time complexity is O(V^2) [1] and space is O(V) [2, 3]."
    out = cfilter.process(text) + cfilter.flush()
    assert "[1]" not in out
    assert "[2, 3]" not in out
    assert out == "The time complexity is O(V^2)  and space is O(V) ."


def test_citation_filter_split_across_tokens():
    cfilter = CitationFilter()
    parts = ["This fact is proven in ", "[", "4", "]", " and verified."]
    result = "".join([cfilter.process(p) for p in parts]) + cfilter.flush()
    assert "[4]" not in result
    assert result == "This fact is proven in  and verified."


def test_citation_filter_multidigit_split():
    cfilter = CitationFilter()
    parts = ["Analysis shows ", "[1", ", 2", "5] holds."]
    result = "".join([cfilter.process(p) for p in parts]) + cfilter.flush()
    assert "[1, 25]" not in result
    assert result == "Analysis shows  holds."


def test_citation_filter_preserves_non_citations():
    cfilter = CitationFilter()
    parts = ["See [markdown link](https://example.com) and task [x] done."]
    result = "".join([cfilter.process(p) for p in parts]) + cfilter.flush()
    assert "[markdown link]" in result
    assert "[x]" in result
