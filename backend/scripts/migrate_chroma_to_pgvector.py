"""
StudyMate RAG — Migrate ChromaDB Vectors to PostgreSQL pgvector

Reads all vector records from the local ChromaDB collection (ids, documents,
metadatas, embeddings) and batch-inserts them into PostgreSQL's chunk_vectors table.
Verifies the counts per document to guarantee lossless migration.

Usage:
    python scripts/migrate_chroma_to_pgvector.py [--dry-run]

Note:
    An alternative to vector migration is re-indexing directly from stored
    PDF documents using: python scripts/reindex.py (with VECTOR_BACKEND=pgvector).
"""

import sys
import argparse
from pathlib import Path
from collections import defaultdict

# Add backend directory to sys.path
backend_dir = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(backend_dir))

from app.core.config import settings
from app.core.logger import logger
from app.db.session import engine
from app.services.vectorstore import get_chroma_client, COLLECTION_NAME


def migrate_chroma_to_pgvector(dry_run: bool = False) -> None:
    logger.info(f"Starting Chroma to pgvector migration (dry_run={dry_run})...")

    # 1. Verify target database dialect is PostgreSQL
    if engine.dialect.name != "postgresql":
        logger.error(
            f"Target database dialect is '{engine.dialect.name}', not PostgreSQL. "
            "Set DATABASE_URL to your PostgreSQL connection string before running this script."
        )
        sys.exit(1)

    # 2. Connect to Chroma and fetch all records
    client = get_chroma_client()
    try:
        collection = client.get_collection(name=COLLECTION_NAME)
    except Exception as e:
        logger.error(f"Could not load Chroma collection '{COLLECTION_NAME}': {e}")
        sys.exit(1)

    count = collection.count()
    logger.info(f"Chroma collection '{COLLECTION_NAME}' has {count} total vectors.")
    if count == 0:
        logger.info("Nothing to migrate. Exiting.")
        return

    # Chroma .get() with embeddings included
    logger.info("Fetching all records with embeddings from ChromaDB...")
    data = collection.get(include=["documents", "metadatas", "embeddings"])

    ids = data.get("ids", [])
    documents = data.get("documents", [])
    metadatas = data.get("metadatas", [])
    embeddings = data.get("embeddings", [])

    logger.info(f"Fetched {len(ids)} records from Chroma.")

    # Group counts per document for verification
    doc_counts_chroma = defaultdict(int)
    for meta in metadatas:
        doc_id = meta.get("document_id") if meta else None
        if doc_id is not None:
            doc_counts_chroma[doc_id] += 1

    logger.info(f"Vector counts across {len(doc_counts_chroma)} documents in Chroma:")
    for doc_id, c in doc_counts_chroma.items():
        logger.info(f"  - Document ID {doc_id}: {c} vectors")

    if dry_run:
        logger.info("Dry run requested. No changes written to PostgreSQL.")
        return

    # 3. Batch insert into PostgreSQL chunk_vectors table
    from sqlalchemy import text

    batch_size = 500
    total = len(ids)

    insert_sql = text("""
        INSERT INTO chunk_vectors (id, user_id, document_id, filename, page, chunk_index, content, embedding)
        VALUES (:id, :user_id, :document_id, :filename, :page, :chunk_index, :content, :embedding)
        ON CONFLICT (id) DO UPDATE SET
            user_id = EXCLUDED.user_id,
            document_id = EXCLUDED.document_id,
            filename = EXCLUDED.filename,
            page = EXCLUDED.page,
            chunk_index = EXCLUDED.chunk_index,
            content = EXCLUDED.content,
            embedding = EXCLUDED.embedding;
    """)

    with engine.begin() as conn:
        for i in range(0, total, batch_size):
            batch_params = []
            for j in range(i, min(i + batch_size, total)):
                meta = metadatas[j]
                emb = str(embeddings[j])
                batch_params.append({
                    "id": ids[j],
                    "user_id": int(meta.get("user_id")),
                    "document_id": int(meta.get("document_id")),
                    "filename": meta.get("filename"),
                    "page": meta.get("page"),
                    "chunk_index": meta.get("chunk_index"),
                    "content": documents[j],
                    "embedding": emb,
                })
            conn.execute(insert_sql, batch_params)
            logger.info(f"Inserted {min(i + batch_size, total)}/{total} vectors into PostgreSQL...")

        # Record embedding model in vector_meta
        conn.execute(text("""
            INSERT INTO vector_meta (key, value)
            VALUES ('embedding_model', :model), ('embedding_dim', :dim)
            ON CONFLICT (key) DO UPDATE SET value = EXCLUDED.value;
        """), {"model": settings.embedding_model, "dim": str(settings.embedding_dim or 384)})

    # 4. Verify counts in PostgreSQL
    with engine.connect() as conn:
        verify_rows = conn.execute(text("""
            SELECT document_id, count(*) AS count
            FROM chunk_vectors
            GROUP BY document_id;
        """)).fetchall()

    doc_counts_pg = {row.document_id: row.count for row in verify_rows}

    logger.info("Verification of vector counts in PostgreSQL:")
    mismatch = False
    for doc_id, expected in doc_counts_chroma.items():
        actual = doc_counts_pg.get(doc_id, 0)
        if actual != expected:
            logger.error(f"Mismatch for Document ID {doc_id}: Chroma={expected}, Postgres={actual}")
            mismatch = True
        else:
            logger.info(f"  - Document ID {doc_id}: {actual} vectors (Verified Match)")

    if mismatch:
        logger.error("Migration finished with count mismatches! Check logs above.")
        sys.exit(1)
    else:
        logger.info(f"Migration successful! All {total} vectors migrated and verified in PostgreSQL.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="StudyMate RAG — Migrate Chroma to pgvector")
    parser.add_argument("--dry-run", action="store_true", help="Inspect Chroma records without writing to Postgres")
    args = parser.parse_args()
    migrate_chroma_to_pgvector(dry_run=args.dry_run)
