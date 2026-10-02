"""
StudyMate RAG — Retriever

Searches the vector store for relevant chunks matching a query.
Supports top-k similarity search with user and document filters,
plus an optional MMR (Maximal Marginal Relevance) mode for diversity.
"""

import re
from app.core.config import settings
from app.core.logger import logger
from app.services.embeddings import embed_query
from app.services.vectorstore import search


STOPWORDS = {
    "what", "is", "are", "the", "a", "an", "in", "of", "to", "for", "on", "at",
    "by", "with", "about", "from", "and", "or", "tell", "me", "show", "give",
    "this", "that", "these", "those", "my", "his", "her", "their", "its", "who",
    "which", "when", "where", "why", "how", "all", "any", "both", "each", "few",
    "more", "most", "other", "some", "such", "than", "too", "very", "can", "will",
    "just", "should", "now", "does", "did", "have", "has", "had", "been", "were", "was"
}


def _extract_keywords(text: str) -> list[str]:
    """Extract informative lowercase keywords from query, excluding stopwords."""
    words = re.findall(r"[a-zA-Z0-9]+", text.lower())
    return [w for w in words if len(w) > 2 and w not in STOPWORDS]


def retrieve_chunks(
    question: str,
    user_id: int,
    document_ids: list[int],
    top_k: int | None = None,
) -> list[dict]:
    """
    Retrieve the most relevant chunks for a question.

    Args:
        question: The user's question (or rewritten standalone question)
        user_id: Current user's ID (for data isolation)
        document_ids: List of document IDs to search within
        top_k: Number of results to return (default from settings)

    Returns:
        List of dicts with keys: content, metadata, score
        Sorted by relevance score (highest first).
    """
    top_k = top_k or settings.top_k
    fetch_k = settings.fetch_k  # Fetch more candidates for MMR/reranking

    # Embed the question
    query_vector = embed_query(question)

    # Build ChromaDB filter
    conditions = [{"user_id": user_id}]
    if len(document_ids) == 1:
        conditions.append({"document_id": document_ids[0]})
    elif len(document_ids) > 1:
        conditions.append({"document_id": {"$in": document_ids}})

    where_filter = {"$and": conditions} if len(conditions) > 1 else conditions[0]

    # Search vector store
    results = search(
        query_embedding=query_vector,
        n_results=fetch_k,
        where=where_filter,
    )

    if not results or not results.get("ids") or not results["ids"][0]:
        logger.info("No chunks found for query")
        return []

    # Parse results into a clean format
    chunks = []
    ids = results["ids"][0]
    documents = results["documents"][0]
    metadatas = results["metadatas"][0]
    distances = results["distances"][0]

    query_keywords = _extract_keywords(question)

    for i in range(len(ids)):
        # ChromaDB returns cosine distance; convert to similarity score
        # cosine distance = 1 - cosine similarity
        raw_score = 1.0 - distances[i]

        # Calculate lexical overlap boost for exact token or prefix matches
        content_lower = documents[i].lower()
        matched_kws = 0
        for kw in query_keywords:
            if kw in content_lower or (len(kw) >= 4 and kw[:4] in content_lower):
                matched_kws += 1

        # Add modest lexical boost (up to 0.15) to help direct keyword matches surface
        lexical_boost = min(matched_kws * 0.05, 0.15)
        score = raw_score + lexical_boost

        chunks.append({
            "content": documents[i],
            "metadata": metadatas[i],
            "score": round(score, 4),
            "raw_score": round(raw_score, 4),
            "vector_id": ids[i],
        })

    # Sort by score descending
    chunks.sort(key=lambda x: x["score"], reverse=True)

    # Apply score threshold — filter out low-relevance chunks
    threshold = settings.score_threshold
    filtered = [c for c in chunks if c["score"] >= threshold]

    # Adaptive fallback: if all chunks scored below threshold, but positive matches exist,
    # fall back to top candidates instead of dropping everything and returning a false "not found"
    if not filtered and chunks and chunks[0]["score"] > 0.0:
        logger.info(
            f"All chunks below threshold ({threshold}), falling back to top candidates "
            f"(best score: {chunks[0]['score']}, raw: {chunks[0].get('raw_score')})"
        )
        filtered = chunks[:top_k]
    elif not filtered:
        logger.info(f"All chunks below threshold ({threshold}). Best score: {chunks[0]['score'] if chunks else 'N/A'}")
        return []

    # Apply MMR if enabled to balance relevance and diversity, otherwise take top-k
    if settings.use_mmr and len(filtered) > top_k:
        result = _calculate_mmr(filtered, top_k=top_k)
    else:
        result = filtered[:top_k]

    logger.info(
        f"Retrieved {len(result)} chunks (from {len(chunks)} candidates, MMR={settings.use_mmr}). "
        f"Scores: {[c['score'] for c in result]}"
    )

    return result


def _calculate_mmr(
    candidates: list[dict],
    top_k: int,
    lambda_param: float = 0.7,
) -> list[dict]:
    """
    Maximal Marginal Relevance (MMR) selection to balance relevance and diversity.
    Penalizes candidates that have high word overlap with already selected chunks.
    """
    if len(candidates) <= top_k:
        return candidates

    selected = [candidates[0]]
    remaining = candidates[1:]

    def get_words(text: str) -> set[str]:
        return set(re.findall(r"[a-z0-9]{3,}", text.lower()))

    selected_words = [get_words(selected[0]["content"])]
    remaining_words = [get_words(c["content"]) for c in remaining]

    while len(selected) < top_k and remaining:
        best_idx = -1
        best_mmr_score = float("-inf")

        for idx, (cand, cand_words) in enumerate(zip(remaining, remaining_words)):
            max_sim = 0.0
            if cand_words:
                for sel_w in selected_words:
                    if sel_w:
                        sim = len(cand_words & sel_w) / len(cand_words | sel_w)
                        if sim > max_sim:
                            max_sim = sim

            mmr_score = (lambda_param * cand["score"]) - ((1.0 - lambda_param) * max_sim)

            if mmr_score > best_mmr_score:
                best_mmr_score = mmr_score
                best_idx = idx

        if best_idx != -1:
            chosen = remaining.pop(best_idx)
            chosen_w = remaining_words.pop(best_idx)
            selected.append(chosen)
            selected_words.append(chosen_w)
        else:
            break

    return selected
