"""
StudyMate RAG — Reranker (Optional)

Uses a cross-encoder model to re-score retrieved chunks for better precision.
Can be enabled/disabled via settings.rerank_enabled.
"""

from app.core.config import settings
from app.core.logger import logger


_reranker = None


def get_reranker():
    """Lazy-load the cross-encoder reranker model."""
    global _reranker
    if _reranker is None:
        from sentence_transformers import CrossEncoder
        logger.info(f"Loading reranker model: {settings.rerank_model}")
        _reranker = CrossEncoder(settings.rerank_model, max_length=512)
        logger.info("Reranker model loaded.")
    return _reranker


def rerank_chunks(
    question: str,
    chunks: list[dict],
    top_n: int = 5,
) -> list[dict]:
    """
    Re-score chunks using a cross-encoder and return the top N.

    Args:
        question: The user's question
        chunks: List of chunk dicts (must have "content" key)
        top_n: Number of top results to keep after reranking

    Returns:
        Reranked and trimmed list of chunk dicts (with updated scores).
    """
    if not settings.rerank_enabled:
        return chunks[:top_n]

    if not chunks:
        return []

    reranker = get_reranker()

    # Prepare pairs for cross-encoder: (question, chunk_text)
    pairs = [(question, chunk["content"]) for chunk in chunks]

    # Score all pairs
    scores = reranker.predict(pairs)

    # Attach rerank scores
    for chunk, score in zip(chunks, scores):
        chunk["rerank_score"] = float(score)

    # Sort by rerank score descending
    chunks.sort(key=lambda x: x["rerank_score"], reverse=True)

    result = chunks[:top_n]

    logger.info(
        f"Reranked {len(chunks)} chunks → top {len(result)}. "
        f"Scores: {[round(c['rerank_score'], 3) for c in result]}"
    )

    return result
