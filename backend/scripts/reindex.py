"""
StudyMate RAG — Re-index Script

Rebuilds ChromaDB vectors from SQL chunks table using the current embedding model.
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
from app.db.session import SessionLocal
from app.models.document import Document, Chunk
from app.services.embeddings import embed_documents
from app.services.vectorstore import get_chroma_client, COLLECTION_NAME


def reindex() -> None:
    logger.info(f"Starting ChromaDB re-indexing with model: '{settings.embedding_model}'")
    db = SessionLocal()

    try:
        # Fetch all chunks joined with document to populate metadata
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

        client = get_chroma_client()

        # Delete existing collection if present
        try:
            client.delete_collection(name=COLLECTION_NAME)
            logger.info(f"Deleted old ChromaDB collection '{COLLECTION_NAME}'")
        except Exception:
            pass

        # Create fresh collection with current model metadata
        collection = client.create_collection(
            name=COLLECTION_NAME,
            metadata={
                "embedding_model": settings.embedding_model,
                "hnsw:space": "cosine",
            },
        )
        logger.info(f"Created fresh collection '{COLLECTION_NAME}' with embedding_model='{settings.embedding_model}'")

        # Process in batches
        batch_size = 64
        total = len(chunks)

        for i in range(0, total, batch_size):
            batch_chunks = chunks[i : i + batch_size]
            contents = [c.content for c in batch_chunks]
            embeddings = embed_documents(contents)

            ids = []
            metadatas = []

            for c in batch_chunks:
                vector_id = c.vector_id or f"doc_{c.document_id}_chunk_{c.chunk_index}"
                ids.append(vector_id)
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
            logger.info(f"Re-indexed {min(i + batch_size, total)}/{total} chunks...")

        logger.info(f"Re-indexing complete! Successfully indexed {total} chunks.")

    finally:
        db.close()


if __name__ == "__main__":
    reindex()
