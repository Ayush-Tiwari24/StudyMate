"""
StudyMate RAG — Document Schemas

Pydantic models for document upload, listing, and status tracking.
"""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict


class DocumentResponse(BaseModel):
    id: int
    filename: str
    size_bytes: int
    pages: int
    chunk_count: int
    status: str  # uploaded | processing | ready | failed
    error_message: Optional[str] = None
    uploaded_at: datetime

    model_config = ConfigDict(from_attributes=True)


class DocumentStatusResponse(BaseModel):
    document_id: int
    status: str
    progress: Optional[int] = None  # 0–100 percentage
    pages: int = 0
    chunks: int = 0
    error_message: Optional[str] = None


class DocumentUploadResponse(BaseModel):
    document_id: int
    filename: str
    status: str = "uploaded"


class DocumentListResponse(BaseModel):
    documents: list[DocumentResponse]
    total: int
