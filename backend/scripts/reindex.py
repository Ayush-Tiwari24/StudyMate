"""
StudyMate RAG — Re-index Script

Rebuilds vector store embeddings from SQL chunks table using the current embedding model.
Works with both:
- ChromaDB (local development)
- PostgreSQL + pgvector (production online stack)

Usage:
    python scripts/reindex.py
"""

import sys
from pathlib import Path

# Add backend directory to sys.path
backend_dir = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(backend_dir))

from app.core.config import settings
from app.core.logger import logger
from app.db.session import SessionLocal, engine
from app.models.document import Document, Chunk
from app.services.embeddings import embed_documents
from app.services.vectorstore import add_chunks


def reindex_pgvector(db, chunks: list[Chunk]) -> None:
    """Rebuild pgvector chunk_vectors table from SQL chunks."""
    from sqlalchemy import text

    logger.info(f"Re-indexing pgvector with embedding_model='{settings.embedding_model}'")
    with engine.begin() as conn:
        # Clear existing chunk_vectors
        conn.execute(text("TRUNCATE TABLE chunk_vectors;"))
        # Update or insert vector_meta
        conn.execute(text("""
            INSERT INTO vector_meta (key, value)
            VALUES ('embedding_model', :model), ('embedding_dim', :dim)
            ON CONFLICT (key) DO UPDATE SET value = EXCLUDED.value;
        """), {"model": settings.embedding_model, "dim": str(settings.embedding_dim or 384)})

    batch_size = 64
    total = len(chunks)

    for i in range(0, total, batch_size):
        batch = chunks[i : i + batch_size]
        contents = [c.content for c in batch]
        embeddings = embed_documents(contents)

        ids = []
        metadatas = []
        for c in batch:
            ids.append(c.vector_id or f"doc_{c.document_id}_chunk_{c.chunk_index}")
            metadatas.append({
                "document_id": c.document_id,
                "user_id": c.document.user_id,
                "filename": c.document.filename,
                "page": c.page,
                "chunk_index": c.chunk_index,
            })

        add_chunks(
            ids=ids,
            embeddings=embeddings,
            documents=contents,
            metadatas=metadatas,
        )
        logger.info(f"Re-indexed {min(i + batch_size, total)}/{total} chunks into pgvector...")

    logger.info(f"pgvector re-indexing complete! Successfully indexed {total} chunks.")


def reindex_chroma(db, chunks: list[Chunk]) -> None:
    """Rebuild ChromaDB collection from SQL chunks."""
    from app.services.vectorstore import get_chroma_client, COLLECTION_NAME

    logger.info(f"Re-indexing ChromaDB with embedding_model='{settings.embedding_model}'")
    client = get_chroma_client()

    try:
        client.delete_collection(name=COLLECTION_NAME)
        logger.info(f"Deleted old ChromaDB collection '{COLLECTION_NAME}'")
    except Exception:
        pass

    collection = client.create_collection(
        name=COLLECTION_NAME,
        metadata={
            "embedding_model": settings.embedding_model,
            "hnsw:space": "cosine",
        },
    )

    batch_size = 64
    total = len(chunks)

    for i in range(0, total, batch_size):
        batch = chunks[i : i + batch_size]
        contents = [c.content for c in batch]
        embeddings = embed_documents(contents)

        ids = []
        metadatas = []
        for c in batch:
            ids.append(c.vector_id or f"doc_{c.document_id}_chunk_{c.chunk_index}")
            metadatas.append({
                "document_id": c.document_id,
                "user_id": c.document.user_id,
                "filename": c.document.filename,
                "page": c.page,
                "chunk_index": c.chunk_index,
            })

        collection.add(
            ids=ids,
            embeddings=embeddings,
            documents=contents,
            metadatas=metadatas,
        )
        logger.info(f"Re-indexed {min(i + batch_size, total)}/{total} chunks into ChromaDB...")

    logger.info(f"ChromaDB re-indexing complete! Successfully indexed {total} chunks.")


def reindex() -> None:
    backend = settings.vector_backend.lower().strip()
    logger.info(f"Starting re-indexing for VECTOR_BACKEND='{backend}'")
    db = SessionLocal()

    try:
        chunks = (
            db.query(Chunk)
            .join(Document, Chunk.document_id == Document.id)
            .order_by(Chunk.document_id, Chunk.chunk_index)
            .all()
        )

        if not chunks:
            logger.info("No chunks found in database to re-index.")
            return

        logger.info(f"Found {len(chunks)} chunks across documents in SQL database.")

        if backend == "pgvector":
            reindex_pgvector(db, chunks)
        else:
            reindex_chroma(db, chunks)

    finally:
        db.close()


if __name__ == "__main__":
    reindex()
