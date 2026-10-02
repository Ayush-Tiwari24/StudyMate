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
from sqlalchemy import func, text
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
    StorageUsageResponse,
)
from app.utils.file_utils import compute_sha256, safe_filename, ensure_dir

router = APIRouter(prefix="/api/documents", tags=["Documents"])


def get_database_size_bytes(db: Session) -> int:
    """Check total database size in bytes (pg_database_size on Postgres, page pragma on SQLite)."""
    try:
        if db.bind.dialect.name == "postgresql":
            res = db.execute(text("SELECT pg_database_size(current_database());")).scalar()
            return int(res or 0)
        else:
            res = db.execute(text("SELECT page_count * page_size FROM pragma_page_count(), pragma_page_size();")).scalar()
            return int(res or 0)
    except Exception as e:
        logger.warning(f"Could not inspect database size: {e}")
        return 0


@router.post("/upload", response_model=DocumentUploadResponse, status_code=status.HTTP_202_ACCEPTED)
async def upload_document(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Upload a PDF file. Validates type and size, enforces user quota & global cap,
    saves to configured storage, and enqueues background ingestion.
    """
    # Validate content type
    if file.content_type != "application/pdf":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Only PDF files are accepted.",
        )

    # Read file content
    content = await file.read()
    content_len = len(content)

    # Validate file size
    if content_len > settings.max_upload_bytes:
        raise HTTPException(
            status_code=413,
            detail=f"File exceeds maximum size of {settings.max_upload_mb} MB.",
        )

    # Check global soft cap (refuse new uploads when database exceeds global cap)
    current_db_size = get_database_size_bytes(db)
    if current_db_size + content_len > settings.global_storage_cap_bytes:
        logger.warning(
            f"Global storage cap reached: db_size={current_db_size} cap={settings.global_storage_cap_bytes}"
        )
        raise HTTPException(
            status_code=413,
            detail="Uploads are paused because storage is full.",
        )

    # Check per-user storage quota
    user_used_bytes = (
        db.query(func.coalesce(func.sum(Document.size_bytes), 0))
        .filter(Document.user_id == current_user.id)
        .scalar()
    )
    if (user_used_bytes + content_len) > settings.user_storage_quota_bytes:
        raise HTTPException(
            status_code=413,
            detail="You've used all your storage. Delete a document to add more.",
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
        size_bytes=content_len,
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


@router.get("/usage", response_model=StorageUsageResponse)
def get_storage_usage(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Return user's storage quota usage breakdown."""
    user_used_bytes = int(
        db.query(func.coalesce(func.sum(Document.size_bytes), 0))
        .filter(Document.user_id == current_user.id)
        .scalar()
        or 0
    )
    quota_bytes = settings.user_storage_quota_bytes
    quota_mb = settings.user_storage_quota_mb
    used_mb = round(user_used_bytes / (1024 * 1024), 2)
    percent_used = round((user_used_bytes / quota_bytes) * 100, 1) if quota_bytes > 0 else 0.0

    return StorageUsageResponse(
        used_bytes=user_used_bytes,
        quota_bytes=quota_bytes,
        used_mb=used_mb,
        quota_mb=quota_mb,
        percent_used=percent_used,
    )


@router.get("", response_model=DocumentListResponse)
def list_documents(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """List all documents belonging to the current user with storage usage summary."""
    docs = (
        db.query(Document)
        .filter(Document.user_id == current_user.id)
        .order_by(Document.uploaded_at.desc())
        .all()
    )
    used_bytes = sum(d.size_bytes or 0 for d in docs)
    quota_bytes = settings.user_storage_quota_bytes
    quota_mb = settings.user_storage_quota_mb
    used_mb = round(used_bytes / (1024 * 1024), 2)
    percent_used = round((used_bytes / quota_bytes) * 100, 1) if quota_bytes > 0 else 0.0

    return DocumentListResponse(
        documents=[DocumentResponse.model_validate(d) for d in docs],
        total=len(docs),
        storage_used_bytes=used_bytes,
        storage_quota_bytes=quota_bytes,
        storage_used_mb=used_mb,
        storage_quota_mb=quota_mb,
        storage_percent_used=percent_used,
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
    from fastapi.responses import StreamingResponse
    import io

    storage = get_storage()
    if not storage.exists(doc.file_path):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="File not found in storage.")

    if hasattr(storage, "open_stream"):
        stream = storage.open_stream(doc.file_path)
    else:
        stream = io.BytesIO(storage.open(doc.file_path))

    headers = {
        "Content-Type": "application/pdf",
        "Content-Disposition": f'inline; filename="{doc.filename}"',
        "Accept-Ranges": "bytes",
    }
    if doc.size_bytes and doc.size_bytes > 0:
        headers["Content-Length"] = str(doc.size_bytes)

    return StreamingResponse(
        stream,
        media_type="application/pdf",
        headers=headers,
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
