"""
StudyMate RAG — CLI Bulk Ingestion Script

Usage:
    python -m scripts.ingest_folder --folder /path/to/pdfs --user-id 1

Ingests all PDF files in a folder for a given user.
"""

import argparse
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.db.session import SessionLocal
from app.db.base import Base
from app.db.session import engine
from app.models.document import Document
from app.utils.file_utils import compute_sha256, safe_filename, ensure_dir
from app.services.ingestion.pipeline import run_ingestion_pipeline
from app.core.config import settings


def main():
    parser = argparse.ArgumentParser(description="Bulk ingest PDFs into StudyMate RAG")
    parser.add_argument("--folder", required=True, help="Path to folder containing PDFs")
    parser.add_argument("--user-id", type=int, required=True, help="User ID to assign documents to")
    args = parser.parse_args()

    folder = Path(args.folder)
    if not folder.is_dir():
        print(f"Error: {folder} is not a valid directory")
        sys.exit(1)

    # Create tables if needed
    Base.metadata.create_all(bind=engine)

    pdf_files = list(folder.glob("*.pdf"))
    if not pdf_files:
        print(f"No PDF files found in {folder}")
        sys.exit(0)

    print(f"Found {len(pdf_files)} PDF files. Starting ingestion...")

    db = SessionLocal()
    try:
        for pdf_path in pdf_files:
            print(f"\n📄 Processing: {pdf_path.name}")

            # Read and hash
            content = pdf_path.read_bytes()
            file_hash = compute_sha256(content)

            # Check for duplicates
            existing = db.query(Document).filter(
                Document.user_id == args.user_id,
                Document.file_hash == file_hash,
            ).first()
            if existing:
                print(f"  ⏩ Skipping (duplicate of '{existing.filename}')")
                continue

            # Copy file to upload directory
            user_dir = ensure_dir(settings.upload_path / str(args.user_id))
            stored_name = safe_filename(pdf_path.name)
            dest = user_dir / stored_name
            dest.write_bytes(content)

            # Create DB record
            doc = Document(
                user_id=args.user_id,
                filename=pdf_path.name,
                file_path=str(dest),
                file_hash=file_hash,
                size_bytes=len(content),
                status="uploaded",
            )
            db.add(doc)
            db.commit()
            db.refresh(doc)

            # Run ingestion
            print(f"  ⚙️ Ingesting (doc_id={doc.id})...")
            run_ingestion_pipeline(doc.id)

            # Refresh to get updated status
            db.refresh(doc)
            if doc.status == "ready":
                print(f"  ✅ Ready — {doc.pages} pages, {doc.chunk_count} chunks")
            else:
                print(f"  ❌ Failed — {doc.error_message}")

    finally:
        db.close()

    print("\n🎉 Bulk ingestion complete!")


if __name__ == "__main__":
    main()
