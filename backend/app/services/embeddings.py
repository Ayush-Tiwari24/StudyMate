"""
StudyMate RAG — Embedding Service

Loads the embedding model once and provides methods to embed
documents (chunks) and queries.
Uses sentence-transformers for local, lightweight embeddings.
"""

from functools import lru_cache

try:
    from langchain_huggingface import HuggingFaceEmbeddings
except ImportError:
    from langchain_community.embeddings import HuggingFaceEmbeddings

from app.core.config import settings
from app.core.logger import logger


import os
os.environ.setdefault("HF_HUB_OFFLINE", "1")


@lru_cache(maxsize=1)
def get_embedding_model() -> HuggingFaceEmbeddings:
    """
    Load and cache the embedding model singleton.
    Uses all-MiniLM-L6-v2 by default (384 dimensions, fast, light).
    Loads from local cache directly to avoid online HF Hub rate limits/hangs.
    """
    logger.info(f"Loading embedding model: {settings.embedding_model}")

    try:
        model = HuggingFaceEmbeddings(
            model_name=settings.embedding_model,
            model_kwargs={"device": "cpu", "local_files_only": True},
            encode_kwargs={
                "normalize_embeddings": True,
                "batch_size": 32,
            },
        )
    except Exception:
        # Fallback if local files not found yet
        os.environ.pop("HF_HUB_OFFLINE", None)
        model = HuggingFaceEmbeddings(
            model_name=settings.embedding_model,
            model_kwargs={"device": "cpu"},
            encode_kwargs={
                "normalize_embeddings": True,
                "batch_size": 32,
            },
        )

    logger.info("Embedding model loaded successfully.")
    return model


def embed_documents(texts: list[str]) -> list[list[float]]:
    """Embed a batch of document chunks. Returns list of vectors."""
    model = get_embedding_model()
    return model.embed_documents(texts)


def embed_query(query: str) -> list[float]:
    """Embed a single query string. Returns a vector."""
    model = get_embedding_model()
    return model.embed_query(query)
