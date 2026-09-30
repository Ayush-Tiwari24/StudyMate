"""
StudyMate RAG — Chat Schemas

Pydantic models for chat creation, messaging, sources, and feedback.
"""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


# ── Requests ─────────────────────────────────────────────────────

class ChatCreateRequest(BaseModel):
    title: str = Field(default="New Chat", max_length=255)
    document_ids: list[int] = Field(..., min_length=1)


class ChatUpdateRequest(BaseModel):
    title: Optional[str] = None
    document_ids: Optional[list[int]] = None


class AskRequest(BaseModel):
    question: str = Field(..., min_length=1, max_length=2000)
    document_ids: Optional[list[int]] = None  # override chat's default docs
    top_k: Optional[int] = None


class FeedbackRequest(BaseModel):
    value: int = Field(..., ge=-1, le=1)  # 1 = 👍, -1 = 👎
    comment: Optional[str] = None


# ── Responses ────────────────────────────────────────────────────

from pydantic import BaseModel, Field, ConfigDict


class SourceResponse(BaseModel):
    id: int
    file: str  # filename
    document_id: Optional[int] = None
    page: Optional[int] = None
    score: Optional[float] = None
    snippet: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)


class MessageResponse(BaseModel):
    id: int
    role: str
    content: str
    model_used: Optional[str] = None
    latency_ms: Optional[int] = None
    sources: list[SourceResponse] = []
    feedback_value: Optional[int] = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class ChatResponse(BaseModel):
    id: int
    title: str
    document_ids: list[int] = []
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class ChatDetailResponse(ChatResponse):
    messages: list[MessageResponse] = []


class ChatListResponse(BaseModel):
    chats: list[ChatResponse]
    total: int


class ExportFormat(BaseModel):
    format: str = Field(default="md", pattern="^(md|pdf)$")
