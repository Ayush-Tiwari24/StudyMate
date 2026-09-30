"""
StudyMate RAG — Retriever

Searches the vector store for relevant chunks matching a query.
Supports top-k similarity search with user and document filters,
plus an optional MMR (Maximal Marginal Relevance) mode for diversity.
"""

from app.core.config import settings
from app.core.logger import logger
from app.services.embeddings import embed_query
from app.services.vectorstore import search


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

    for i in range(len(ids)):
        # ChromaDB returns cosine distance; convert to similarity score
        # cosine distance = 1 - cosine similarity
        score = 1.0 - distances[i]

        chunks.append({
            "content": documents[i],
            "metadata": metadatas[i],
            "score": round(score, 4),
            "vector_id": ids[i],
        })

    # Sort by score descending
    chunks.sort(key=lambda x: x["score"], reverse=True)

    # Apply score threshold — filter out low-relevance chunks
    threshold = settings.score_threshold
    filtered = [c for c in chunks if c["score"] >= threshold]

    if not filtered:
        logger.info(f"All chunks below threshold ({threshold}). Best score: {chunks[0]['score'] if chunks else 'N/A'}")
        return []

    # Return top-k results
    result = filtered[:top_k]

    logger.info(
        f"Retrieved {len(result)} chunks (from {len(chunks)} candidates). "
        f"Scores: {[c['score'] for c in result]}"
    )

    return result
