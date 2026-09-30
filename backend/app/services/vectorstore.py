"""
StudyMate RAG — Vector Store (ChromaDB)

Wrapper around ChromaDB for adding, searching, and deleting vectors.
Collection: 'studymate_chunks' with persistent storage.
"""

from functools import lru_cache

import chromadb
from chromadb.config import Settings as ChromaSettings

from app.core.config import settings
from app.core.logger import logger


COLLECTION_NAME = "studymate_chunks"


@lru_cache(maxsize=1)
def get_chroma_client() -> chromadb.ClientAPI:
    """Get or create the persistent ChromaDB client."""
    logger.info(f"Initializing ChromaDB at: {settings.vector_store_dir}")
    client = chromadb.PersistentClient(
        path=settings.vector_store_dir,
        settings=ChromaSettings(anonymized_telemetry=False),
    )
    return client


def get_collection() -> chromadb.Collection:
    """Get or create the main chunks collection."""
    client = get_chroma_client()
    collection = client.get_or_create_collection(
        name=COLLECTION_NAME,
        metadata={
            "embedding_model": settings.embedding_model,
            "hnsw:space": "cosine",
        },
    )
    return collection


def add_chunks(
    ids: list[str],
    embeddings: list[list[float]],
    documents: list[str],
    metadatas: list[dict],
) -> None:
    """
    Add chunk embeddings to the vector store.

    Args:
        ids: Unique IDs for each chunk (e.g., "doc_17_chunk_0")
        embeddings: Pre-computed embedding vectors
        documents: Chunk text content
        metadatas: Metadata dicts (user_id, document_id, page, etc.)
    """
    collection = get_collection()
    # ChromaDB has a batch limit; split into batches of 500
    batch_size = 500
    for i in range(0, len(ids), batch_size):
        collection.add(
            ids=ids[i:i + batch_size],
            embeddings=embeddings[i:i + batch_size],
            documents=documents[i:i + batch_size],
            metadatas=metadatas[i:i + batch_size],
        )
    logger.info(f"Added {len(ids)} vectors to ChromaDB")


def search(
    query_embedding: list[float],
    n_results: int = 5,
    where: dict | None = None,
) -> dict:
    """
    Search for similar chunks in the vector store.

    Args:
        query_embedding: Query vector
        n_results: Number of results to return
        where: ChromaDB filter dict (e.g., {"user_id": 1, "document_id": {"$in": [17, 18]}})

    Returns:
        ChromaDB query result with ids, documents, metadatas, distances
    """
    collection = get_collection()
    kwargs = {
        "query_embeddings": [query_embedding],
        "n_results": n_results,
        "include": ["documents", "metadatas", "distances"],
    }
    if where:
        kwargs["where"] = where

    results = collection.query(**kwargs)
    return results


def delete_vectors_by_document(document_id: int) -> None:
    """Delete all vectors belonging to a specific document."""
    collection = get_collection()
    collection.delete(where={"document_id": document_id})
    logger.info(f"Deleted vectors for document_id={document_id}")
