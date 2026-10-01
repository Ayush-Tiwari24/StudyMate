"""
StudyMate RAG — Ingestion Pipeline

Orchestrates the full document ingestion flow:
load PDF → OCR fallback → clean → chunk → embed → store in vector DB → update status.
Runs as a background task.
"""

from pathlib import Path

from app.core.config import settings
from app.core.logger import logger
from app.db.session import SessionLocal
from app.models.document import Document, Chunk
from app.services.ingestion.loader import load_pdf
from app.services.ingestion.ocr import needs_ocr, ocr_pdf_pages
from app.services.ingestion.cleaner import clean_pages
from app.services.ingestion.chunker import chunk_pages
from app.services.embeddings import embed_documents
from app.services.vectorstore import add_chunks, delete_vectors_by_document


def run_ingestion_pipeline(document_id: int) -> None:
    """
    Full ingestion pipeline for a single document.
    Designed to run as a FastAPI BackgroundTask.
    Uses its own DB session (not the request's session).
    """
    db = SessionLocal()

    try:
        # Load document record
        doc = db.query(Document).filter(Document.id == document_id).first()
        if not doc:
            logger.error(f"Ingestion: Document {document_id} not found in DB")
            return

        # Update status to processing and initial progress
        doc.status = "processing"
        doc.progress = 5
        doc.error_message = None
        db.commit()

        logger.info(f"Ingestion started: id={doc.id} filename={doc.filename}")

        file_path = Path(doc.file_path)
        if not file_path.exists():
            _fail(db, doc, "File not found on disk.")
            return

        # ── Step 1: Load PDF ────────────────────────────────────
        pages = load_pdf(file_path)
        doc.pages = len(pages)
        doc.progress = 20
        db.commit()

        if not pages:
            _fail(db, doc, "No pages found in PDF.")
            return

        # ── Step 2: OCR fallback for scanned pages ──────────────
        pages_needing_ocr = {p["page"] for p in pages if needs_ocr(p["text"])}
        if pages_needing_ocr:
            logger.info(f"{len(pages_needing_ocr)}/{len(pages)} pages appear scanned. Running in-process OCR for {doc.filename}")
            pages = ocr_pdf_pages(file_path, pages_to_ocr=pages_needing_ocr)

        # Check if we got readable text
        total_text = sum(len(p["text"]) for p in pages)
        if total_text < 30:
            _fail(db, doc, "No readable text could be extracted from this document.")
            return

        # ── Step 3: Clean text ──────────────────────────────────
        pages = clean_pages(pages)
        doc.progress = 40
        db.commit()

        # ── Step 4: Chunk ───────────────────────────────────────
        chunks = chunk_pages(
            pages=pages,
            document_id=doc.id,
            filename=doc.filename,
            user_id=doc.user_id,
        )

        if not chunks:
            _fail(db, doc, "Text was found but could not be chunked.")
            return

        doc.progress = 60
        db.commit()

        # ── Step 5: Embed ───────────────────────────────────────
        chunk_texts = [c["content"] for c in chunks]

        # Embed in batches to manage memory
        batch_size = 32
        all_embeddings = []
        for i in range(0, len(chunk_texts), batch_size):
            batch = chunk_texts[i:i + batch_size]
            batch_embeddings = embed_documents(batch)
            all_embeddings.extend(batch_embeddings)

        doc.progress = 80
        db.commit()

        # ── Step 6: Store in vector DB (idempotent) ──────────────
        # Purge any previous vectors for this document
        try:
            delete_vectors_by_document(doc.id)
        except Exception as e:
            logger.warning(f"Could not purge existing vectors for doc {doc.id}: {e}")

        vector_ids = [f"doc_{doc.id}_chunk_{c['metadata']['chunk_index']}" for c in chunks]
        metadatas = [c["metadata"] for c in chunks]

        add_chunks(
            ids=vector_ids,
            embeddings=all_embeddings,
            documents=chunk_texts,
            metadatas=metadatas,
        )

        # ── Step 7: Save chunks to SQL DB (idempotent) ──────────
        db.query(Chunk).filter(Chunk.document_id == doc.id).delete()
        for chunk_data, vector_id in zip(chunks, vector_ids):
            chunk_record = Chunk(
                document_id=doc.id,
                page=chunk_data["metadata"]["page"],
                chunk_index=chunk_data["metadata"]["chunk_index"],
                content=chunk_data["content"],
                vector_id=vector_id,
            )
            db.add(chunk_record)

        # ── Step 8: Update document status ──────────────────────
        doc.chunk_count = len(chunks)
        doc.progress = 100
        doc.status = "ready"
        doc.error_message = None
        db.commit()

        logger.info(
            f"Ingestion complete: id={doc.id} filename={doc.filename} "
            f"pages={doc.pages} chunks={doc.chunk_count}"
        )

    except Exception as e:
        logger.error(f"Ingestion failed for document {document_id}: {e}")
        try:
            doc = db.query(Document).filter(Document.id == document_id).first()
            if doc:
                _fail(db, doc, f"Ingestion error: {str(e)[:200]}")
        except Exception:
            pass

    finally:
        db.close()


def _fail(db, doc: Document, message: str) -> None:
    """Mark a document as failed with an error message."""
    doc.status = "failed"
    doc.progress = 0
    doc.error_message = message
    db.commit()
    logger.warning(f"Document failed: id={doc.id} — {message}")
