"""
Unit tests for ReasoningFilter:
Ensures reasoning text never appears in streamed tokens for both inline tags
and separate field formats.
"""

from app.services.generation.rag_chain import ReasoningFilter


class FakeChunk:
    def __init__(self, content: str, additional_kwargs: dict = None):
        self.content = content
        self.additional_kwargs = additional_kwargs or {}


def test_reasoning_filter_inline_think_tags():
    """Verify inline <think> tags are stripped and only final answer emits."""
    rf = ReasoningFilter()
    chunks = [
        "<think>",
        "The user is asking about Dijkstra algorithm.",
        " I need to explain the priority queue.",
        "</think>",
        "Dijkstra's algorithm finds the shortest path.",
    ]
    emitted = []
    for c in chunks:
        out = rf.process_chunk(c)
        if out:
            emitted.append(out)
    tail = rf.flush()
    if tail:
        emitted.append(tail)

    full = "".join(emitted)
    assert "<think>" not in full
    assert "</think>" not in full
    assert "The user is asking" not in full
    assert full.strip() == "Dijkstra's algorithm finds the shortest path."


def test_reasoning_filter_separate_channel_chunks():
    """Verify chunks with empty content and separate reasoning field emit nothing."""
    rf = ReasoningFilter()
    # Simulated Groq reasoning channel chunk
    c1 = FakeChunk(content="", additional_kwargs={"reasoning": "Analyze the question."})
    out1 = rf.process_chunk(c1)
    assert out1 == ""

    # Simulated answer chunk
    c2 = FakeChunk(content="Here is the explanation.")
    out2 = rf.process_chunk(c2)
    assert out2 == "Here is the explanation."

    tail = rf.flush()
    assert tail == ""
