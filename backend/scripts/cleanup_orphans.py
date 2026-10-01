"""
StudyMate RAG — Orphan Cleanup Script

Scans both the file storage and Chroma vector store for records/files
with no matching document in the SQL database, and deletes them.

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
from app.db.session import SessionLocal
from app.models.document import Document
from app.services.vectorstore import get_collection


def cleanup_orphans(dry_run: bool = False) -> None:
    logger.info(f"Starting orphan cleanup (dry_run={dry_run})...")
    db = SessionLocal()

    try:
        docs = db.query(Document).all()
        valid_doc_ids = {d.id for d in docs}
        valid_file_paths = {Path(d.file_path).resolve() for d in docs if d.file_path}

        logger.info(f"Database contains {len(valid_doc_ids)} active document records.")

        # ── 1. Clean up orphan disk files ─────────────────────────
        upload_root = settings.upload_path
        orphan_files_count = 0

        if upload_root.exists():
            for p in upload_root.rglob("*"):
                if p.is_file():
                    resolved_p = p.resolve()
                    if resolved_p not in valid_file_paths:
                        orphan_files_count += 1
                        logger.warning(f"Orphan file found: {p}")
                        if not dry_run:
                            try:
                                p.unlink()
                                logger.info(f"Deleted orphan file: {p}")
                            except Exception as e:
                                logger.error(f"Failed to delete orphan file {p}: {e}")

            # Remove empty directories
            if not dry_run:
                for d in sorted(upload_root.rglob("*"), reverse=True):
                    if d.is_dir() and not any(d.iterdir()):
                        try:
                            d.rmdir()
                        except Exception:
                            pass

        # ── 2. Clean up orphan Chroma vectors ──────────────────────
        orphan_vectors_count = 0
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
                    # Chroma batch delete
                    batch_size = 500
                    for i in range(0, len(orphan_vector_ids), batch_size):
                        batch = orphan_vector_ids[i : i + batch_size]
                        collection.delete(ids=batch)
                    logger.info(f"Deleted {orphan_vectors_count} orphan vectors from ChromaDB.")
            else:
                logger.info("No orphan vectors found in ChromaDB.")

        except Exception as e:
            logger.warning(f"Could not inspect/clean ChromaDB vectors: {e}")

        logger.info(
            f"Cleanup summary: {orphan_files_count} orphan files, "
            f"{orphan_vectors_count} orphan vectors detected."
        )

    finally:
        db.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Clean up orphan files and vectors.")
    parser.add_argument("--dry-run", action="store_true", help="Report orphans without deleting.")
    args = parser.parse_args()
    cleanup_orphans(dry_run=args.dry_run)
