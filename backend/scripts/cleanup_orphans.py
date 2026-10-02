"""
StudyMate RAG — Orphan Cleanup Script

Scans both the file storage and vector store for records/files
with no matching document in the SQL database, and deletes them.

Supports:
- Storage: LocalStorage and S3Storage (Supabase Storage / AWS S3)
- Vectors: ChromaDB and PostgreSQL pgvector

Usage:
    python scripts/cleanup_orphans.py [--dry-run]
"""

import sys
import argparse
from pathlib import Path

# Add backend directory to sys.path
backend_dir = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(backend_dir))

from app.core.config import settings
from app.core.logger import logger
from app.db.session import SessionLocal, engine
from app.models.document import Document
from app.services.storage import get_storage


def cleanup_storage_orphans(valid_file_paths: set[str], dry_run: bool = False) -> int:
    """Scan and delete orphan files from active storage backend."""
    storage_backend = settings.storage_backend.lower().strip()
    orphan_files_count = 0

    if storage_backend == "s3":
        logger.info(f"Scanning S3 bucket '{settings.s3_bucket}' for orphan keys...")
        storage = get_storage()
        try:
            paginator = storage.s3.get_paginator("list_objects_v2")
            orphan_keys = []
            for page in paginator.paginate(Bucket=settings.s3_bucket):
                for obj in page.get("Contents", []):
                    key = obj["Key"]
                    if key not in valid_file_paths:
                        orphan_keys.append(key)
                        orphan_files_count += 1
                        logger.warning(f"Orphan S3 key found: {key}")

            if orphan_keys and not dry_run:
                delete_entries = [{"Key": k} for k in orphan_keys]
                for i in range(0, len(delete_entries), 1000):
                    batch = delete_entries[i : i + 1000]
                    storage.s3.delete_objects(
                        Bucket=settings.s3_bucket,
                        Delete={"Objects": batch},
                    )
                logger.info(f"Deleted {len(orphan_keys)} orphan files from S3.")
        except Exception as e:
            logger.error(f"Error inspecting S3 storage for orphans: {e}")
    else:
        # LocalStorage
        upload_root = settings.upload_path
        if upload_root.exists():
            resolved_valid = {Path(p).resolve() for p in valid_file_paths if p}
            for p in upload_root.rglob("*"):
                if p.is_file():
                    resolved_p = p.resolve()
                    if resolved_p not in resolved_valid:
                        orphan_files_count += 1
                        logger.warning(f"Orphan local file found: {p}")
                        if not dry_run:
                            try:
                                p.unlink()
                                logger.info(f"Deleted orphan local file: {p}")
                            except Exception as e:
                                logger.error(f"Failed to delete orphan file {p}: {e}")

            if not dry_run:
                for d in sorted(upload_root.rglob("*"), reverse=True):
                    if d.is_dir() and not any(d.iterdir()):
                        try:
                            d.rmdir()
                        except Exception:
                            pass

    return orphan_files_count


def cleanup_vector_orphans(valid_doc_ids: set[int], dry_run: bool = False) -> int:
    """Scan and delete orphan vector records from active vector backend."""
    vector_backend = settings.vector_backend.lower().strip()
    orphan_vectors_count = 0

    if vector_backend == "pgvector":
        from sqlalchemy import text
        logger.info("Scanning PostgreSQL 'chunk_vectors' table for orphan vectors...")
        try:
            with engine.connect() as conn:
                orphan_query = text("""
                    SELECT cv.id, cv.document_id
                    FROM chunk_vectors cv
                    LEFT JOIN documents d ON cv.document_id = d.id
                    WHERE d.id IS NULL;
                """)
                orphan_rows = conn.execute(orphan_query).fetchall()
                orphan_vectors_count = len(orphan_rows)

                if orphan_rows:
                    logger.warning(f"Found {orphan_vectors_count} orphan vectors in PostgreSQL chunk_vectors.")
                    if not dry_run:
                        with engine.begin() as delete_conn:
                            delete_conn.execute(text("""
                                DELETE FROM chunk_vectors
                                WHERE document_id NOT IN (SELECT id FROM documents);
                            """))
                        logger.info(f"Deleted {orphan_vectors_count} orphan vectors from pgvector.")
                else:
                    logger.info("No orphan vectors found in PostgreSQL chunk_vectors.")
        except Exception as e:
            logger.error(f"Error inspecting pgvector for orphans: {e}")

    else:
        # ChromaDB
        from app.services.vectorstore import get_collection
        logger.info("Scanning ChromaDB collection for orphan vectors...")
        try:
            collection = get_collection(validate_model=False)
            all_data = collection.get(include=["metadatas"])
            vector_ids = all_data.get("ids", [])
            metadatas = all_data.get("metadatas", [])

            orphan_vector_ids = []
            for vid, meta in zip(vector_ids, metadatas):
                doc_id = meta.get("document_id") if meta else None
                if doc_id is None or doc_id not in valid_doc_ids:
                    orphan_vector_ids.append(vid)

            orphan_vectors_count = len(orphan_vector_ids)
            if orphan_vector_ids:
                logger.warning(f"Found {orphan_vectors_count} orphan vectors in ChromaDB.")
                if not dry_run:
                    batch_size = 500
                    for i in range(0, len(orphan_vector_ids), batch_size):
                        batch = orphan_vector_ids[i : i + batch_size]
                        collection.delete(ids=batch)
                    logger.info(f"Deleted {orphan_vectors_count} orphan vectors from ChromaDB.")
            else:
                logger.info("No orphan vectors found in ChromaDB.")
        except Exception as e:
            logger.warning(f"Could not inspect/clean ChromaDB vectors: {e}")

    return orphan_vectors_count


def cleanup_orphans(dry_run: bool = False) -> None:
    logger.info(f"Starting orphan cleanup (dry_run={dry_run})...")
    db = SessionLocal()

    try:
        docs = db.query(Document).all()
        valid_doc_ids = {d.id for d in docs}
        valid_file_paths = {d.file_path for d in docs if d.file_path}

        logger.info(f"Database contains {len(valid_doc_ids)} active document records.")

        orphan_files = cleanup_storage_orphans(valid_file_paths, dry_run=dry_run)
        orphan_vectors = cleanup_vector_orphans(valid_doc_ids, dry_run=dry_run)

        logger.info(
            f"Cleanup summary: {orphan_files} orphan files, "
            f"{orphan_vectors} orphan vectors processed."
        )

    finally:
        db.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="StudyMate RAG — Orphan Cleanup")
    parser.add_argument("--dry-run", action="store_true", help="Report orphans without deleting them")
    args = parser.parse_args()
    cleanup_orphans(dry_run=args.dry_run)
