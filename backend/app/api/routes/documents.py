"""
StudyMate RAG — Document Routes

POST   /api/documents/upload       — Upload a PDF
GET    /api/documents              — List user's documents
GET    /api/documents/{id}/status  — Processing status
GET    /api/documents/{id}/file    — Download original PDF
DELETE /api/documents/{id}         — Delete PDF + vectors + chunks
"""

from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, BackgroundTasks, status
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from app.api.deps import get_db, get_current_user
from app.core.config import settings
from app.core.logger import logger
from app.models.user import User
from app.models.document import Document
from app.schemas.document import (
    DocumentUploadResponse,
    DocumentResponse,
    DocumentStatusResponse,
    DocumentListResponse,
)
from app.utils.file_utils import compute_sha256, safe_filename, ensure_dir

router = APIRouter(prefix="/api/documents", tags=["Documents"])


@router.post("/upload", response_model=DocumentUploadResponse, status_code=status.HTTP_202_ACCEPTED)
async def upload_document(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Upload a PDF file. Validates type and size, saves to disk,
    and enqueues background ingestion.
    """
    # Validate content type
    if file.content_type != "application/pdf":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Only PDF files are accepted.",
        )

    # Read file content
    content = await file.read()

    # Validate file size
    if len(content) > settings.max_upload_bytes:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"File exceeds maximum size of {settings.max_upload_mb} MB.",
        )

    # Check for duplicates via SHA-256 hash
    file_hash = compute_sha256(content)
    existing = (
        db.query(Document)
        .filter(Document.user_id == current_user.id, Document.file_hash == file_hash)
        .first()
    )
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"This file has already been uploaded as '{existing.filename}'.",
        )

    # Save file via storage backend (stores relative storage key)
    from app.services.storage import get_storage
    storage = get_storage()
    storage_key = storage.save(current_user.id, file.filename or "document.pdf", content)

    # Create database record
    document = Document(
        user_id=current_user.id,
        filename=file.filename or "document.pdf",
        file_path=storage_key,
        file_hash=file_hash,
        size_bytes=len(content),
        status="uploaded",
    )
    db.add(document)
    db.commit()
    db.refresh(document)

    logger.info(f"Document uploaded: id={document.id} filename={document.filename}")

    # Enqueue ingestion pipeline as background task
    from app.services.ingestion.pipeline import run_ingestion_pipeline
    background_tasks.add_task(run_ingestion_pipeline, document.id)

    return DocumentUploadResponse(
        document_id=document.id,
        filename=document.filename,
        status="uploaded",
    )


@router.get("", response_model=DocumentListResponse)
def list_documents(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """List all documents belonging to the current user."""
    docs = (
        db.query(Document)
        .filter(Document.user_id == current_user.id)
        .order_by(Document.uploaded_at.desc())
        .all()
    )
    return DocumentListResponse(
        documents=[DocumentResponse.model_validate(d) for d in docs],
        total=len(docs),
    )


@router.get("/{document_id}/status", response_model=DocumentStatusResponse)
def get_document_status(
    document_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get the processing status of a document (used for polling)."""
    doc = (
        db.query(Document)
        .filter(Document.id == document_id, Document.user_id == current_user.id)
        .first()
    )
    if not doc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Document not found.")

    return DocumentStatusResponse(
        document_id=doc.id,
        status=doc.status,
        progress=doc.progress,
        pages=doc.pages,
        chunks=doc.chunk_count,
        error_message=doc.error_message,
    )


@router.get("/{document_id}/file")
def download_document(
    document_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Download / view the original PDF file."""
    doc = (
        db.query(Document)
        .filter(Document.id == document_id, Document.user_id == current_user.id)
        .first()
    )
    if not doc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Document not found.")

    from app.services.storage import get_storage
    from fastapi.responses import Response
    storage = get_storage()
    if not storage.exists(doc.file_path):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="File not found in storage.")

    content = storage.open(doc.file_path)
    return Response(
        content=content,
        media_type="application/pdf",
        headers={"Content-Disposition": f'inline; filename="{doc.filename}"'},
    )


@router.delete("/{document_id}", status_code=status.HTTP_200_OK)
def delete_document(
    document_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Delete a document: remove file from disk, vectors from ChromaDB,
    and all related DB records (chunks, etc.).
    """
    doc = (
        db.query(Document)
        .filter(Document.id == document_id, Document.user_id == current_user.id)
        .first()
    )
    if not doc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Document not found.")

    doc_id = doc.id
    file_path_str = doc.file_path

    # 1. Delete from database and commit first (cascades to chunks and chat_documents)
    db.delete(doc)
    db.commit()
    logger.info(f"Document record deleted from SQL: id={doc_id}")

    # 2. Delete vectors from ChromaDB (best-effort)
    try:
        from app.services.vectorstore import delete_vectors_by_document
        delete_vectors_by_document(doc_id)
    except Exception as e:
        logger.warning(f"Failed to delete vectors for doc {doc_id}: {e}")

    # 3. Delete file from storage (best-effort)
    try:
        from app.services.storage import get_storage
        storage = get_storage()
        storage.delete(file_path_str)
    except Exception as e:
        logger.warning(f"Failed to delete file {file_path_str}: {e}")

    return {"message": "Document deleted successfully."}


@router.post("/{document_id}/retry", response_model=DocumentStatusResponse)
def retry_document(
    document_id: int,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Re-run the ingestion pipeline for a failed or stuck document."""
    doc = (
        db.query(Document)
        .filter(Document.id == document_id, Document.user_id == current_user.id)
        .first()
    )
    if not doc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Document not found.")

    doc.status = "uploaded"
    doc.progress = 0
    doc.error_message = None
    db.commit()

    from app.services.ingestion.pipeline import run_ingestion_pipeline
    background_tasks.add_task(run_ingestion_pipeline, doc.id)

    return DocumentStatusResponse(
        document_id=doc.id,
        status="uploaded",
        progress=0,
        pages=doc.pages,
        chunks=doc.chunk_count,
        error_message=None,
    )
