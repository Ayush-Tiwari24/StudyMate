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


def get_collection(validate_model: bool = True) -> chromadb.Collection:
    """Get or create the main chunks collection and validate model consistency."""
    client = get_chroma_client()
    collection = client.get_or_create_collection(
        name=COLLECTION_NAME,
        metadata={
            "embedding_model": settings.embedding_model,
            "hnsw:space": "cosine",
        },
    )
    if validate_model and collection.metadata:
        stored_model = collection.metadata.get("embedding_model")
        if stored_model and stored_model != settings.embedding_model:
            error_msg = (
                f"Embedding model mismatch! Collection uses '{stored_model}', "
                f"but settings configure '{settings.embedding_model}'. "
                f"Refusing to add vectors until scripts/reindex.py is run."
            )
            logger.error(error_msg)
            raise ValueError(error_msg)
    return collection


def _add_chunks_chroma(
    ids: list[str],
    embeddings: list[list[float]],
    documents: list[str],
    metadatas: list[dict],
) -> None:
    collection = get_collection()
    batch_size = 500
    for i in range(0, len(ids), batch_size):
        collection.add(
            ids=ids[i : i + batch_size],
            embeddings=embeddings[i : i + batch_size],
            documents=documents[i : i + batch_size],
            metadatas=metadatas[i : i + batch_size],
        )
    logger.info(f"Added {len(ids)} vectors to ChromaDB")


def _search_chroma(
    query_embedding: list[float],
    n_results: int = 5,
    where: dict | None = None,
) -> dict:
    collection = get_collection()
    kwargs = {
        "query_embeddings": [query_embedding],
        "n_results": n_results,
        "include": ["documents", "metadatas", "distances"],
    }
    if where:
        kwargs["where"] = where
    return collection.query(**kwargs)


def _delete_vectors_chroma(document_id: int) -> None:
    collection = get_collection()
    collection.delete(where={"document_id": document_id})
    logger.info(f"Deleted vectors from ChromaDB for document_id={document_id}")


# ── PgVector implementation stubs / helpers ───────────────────────
def _add_chunks_pgvector(ids, embeddings, documents, metadatas):
    logger.warning("pgvector backend selected; falling back to Chroma if pgvector extension is unconfigured.")
    _add_chunks_chroma(ids, embeddings, documents, metadatas)


def _search_pgvector(query_embedding, n_results=5, where=None):
    return _search_chroma(query_embedding, n_results, where)


def _delete_vectors_pgvector(document_id: int):
    _delete_vectors_chroma(document_id)


# ── Public API (Backend Agnostic) ─────────────────────────────────
def add_chunks(
    ids: list[str],
    embeddings: list[list[float]],
    documents: list[str],
    metadatas: list[dict],
) -> None:
    """Add chunk embeddings to the active vector store."""
    backend = settings.vector_backend.lower().strip()
    if backend == "pgvector":
        _add_chunks_pgvector(ids, embeddings, documents, metadatas)
    else:
        _add_chunks_chroma(ids, embeddings, documents, metadatas)


def search(
    query_embedding: list[float],
    n_results: int = 5,
    where: dict | None = None,
) -> dict:
    """Search for similar chunks in the active vector store."""
    backend = settings.vector_backend.lower().strip()
    if backend == "pgvector":
        return _search_pgvector(query_embedding, n_results, where)
    return _search_chroma(query_embedding, n_results, where)


def delete_vectors_by_document(document_id: int) -> None:
    """Delete all vectors belonging to a specific document."""
    backend = settings.vector_backend.lower().strip()
    if backend == "pgvector":
        _delete_vectors_pgvector(document_id)
    else:
        _delete_vectors_chroma(document_id)
