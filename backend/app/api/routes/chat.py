"""
StudyMate RAG — Chat Routes

POST /api/chats           — Create a new chat
GET  /api/chats           — List user's chats
GET  /api/chats/{id}      — Get chat with all messages
POST /api/chats/{id}/ask  — Ask a question (SSE stream)
PATCH /api/chats/{id}     — Rename / update documents
DELETE /api/chats/{id}    — Delete a chat
GET  /api/chats/{id}/export — Export conversation as markdown or PDF
"""

import json
import time
from typing import AsyncGenerator

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from app.api.deps import get_db, get_current_user
from app.models.user import User
from app.models.chat import Chat
from app.models.document import Document
from app.models.message import Message, MessageSource
from app.schemas.chat import (
    ChatCreateRequest,
    ChatUpdateRequest,
    AskRequest,
    ChatResponse,
    ChatDetailResponse,
    ChatListResponse,
    MessageResponse,
    SourceResponse,
)
from app.core.logger import logger

router = APIRouter(prefix="/api/chats", tags=["Chat"])


@router.post("", response_model=ChatResponse, status_code=status.HTTP_201_CREATED)
def create_chat(
    body: ChatCreateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Create a new chat session with selected documents."""
    # Validate document IDs belong to current user and are ready
    docs = (
        db.query(Document)
        .filter(
            Document.id.in_(body.document_ids),
            Document.user_id == current_user.id,
        )
        .all()
    )

    if len(docs) != len(body.document_ids):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="One or more document IDs are invalid.",
        )

    not_ready = [d for d in docs if d.status != "ready"]
    if not_ready:
        names = ", ".join(d.filename for d in not_ready)
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Documents not ready: {names}",
        )

    chat = Chat(
        user_id=current_user.id,
        title=body.title,
    )
    chat.documents = docs
    db.add(chat)
    db.commit()
    db.refresh(chat)

    return ChatResponse(
        id=chat.id,
        title=chat.title,
        document_ids=[d.id for d in chat.documents],
        created_at=chat.created_at,
        updated_at=chat.updated_at,
    )


@router.get("", response_model=ChatListResponse)
def list_chats(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """List all chats for the current user, most recent first."""
    chats = (
        db.query(Chat)
        .filter(Chat.user_id == current_user.id)
        .order_by(Chat.updated_at.desc())
        .all()
    )
    return ChatListResponse(
        chats=[
            ChatResponse(
                id=c.id,
                title=c.title,
                document_ids=[d.id for d in c.documents],
                created_at=c.created_at,
                updated_at=c.updated_at,
            )
            for c in chats
        ],
        total=len(chats),
    )


@router.get("/{chat_id}", response_model=ChatDetailResponse)
def get_chat(
    chat_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get a chat with all its messages and sources."""
    chat = (
        db.query(Chat)
        .filter(Chat.id == chat_id, Chat.user_id == current_user.id)
        .first()
    )
    if not chat:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Chat not found.")

    messages = []
    for msg in chat.messages:
        sources = [
            SourceResponse(
                id=s.id,
                file=_get_doc_filename(db, s.document_id),
                document_id=s.document_id,
                page=s.page,
                score=s.score,
                snippet=s.snippet,
            )
            for s in msg.sources
        ]
        messages.append(
            MessageResponse(
                id=msg.id,
                role=msg.role,
                content=msg.content,
                model_used=msg.model_used,
                latency_ms=msg.latency_ms,
                sources=sources,
                feedback_value=msg.feedback.value if msg.feedback else None,
                created_at=msg.created_at,
            )
        )

    return ChatDetailResponse(
        id=chat.id,
        title=chat.title,
        document_ids=[d.id for d in chat.documents],
        created_at=chat.created_at,
        updated_at=chat.updated_at,
        messages=messages,
    )


@router.post("/{chat_id}/ask")
async def ask_question(
    chat_id: int,
    body: AskRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Ask a question in a chat. Returns an SSE stream with:
    - `token` events (streaming answer text)
    - `sources` event (citation metadata)
    - `done` event (message ID + latency)
    """
    chat = (
        db.query(Chat)
        .filter(Chat.id == chat_id, Chat.user_id == current_user.id)
        .first()
    )
    if not chat:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Chat not found.")

    # Determine which documents to search
    doc_ids = body.document_ids or [d.id for d in chat.documents]
    if not doc_ids:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No documents selected for this chat.",
        )

    # Save user message
    user_msg = Message(chat_id=chat.id, role="user", content=body.question)
    db.add(user_msg)
    db.commit()

    # Stream the response via SSE
    async def event_stream() -> AsyncGenerator[str, None]:
        start_time = time.time()
        full_answer = ""
        sources_data = []
        user_prefs = current_user.preferences or {}

        try:
            from app.services.generation.rag_chain import rag_query

            async for event in rag_query(
                question=body.question,
                chat_id=chat.id,
                user_id=current_user.id,
                document_ids=doc_ids,
                top_k=body.top_k or user_prefs.get("top_k"),
                db=db,
                user_preferences=user_prefs,
            ):
                if event["type"] == "token":
                    full_answer += event["text"]
                    yield f"event: token\ndata: {json.dumps({'text': event['text']})}\n\n"
                elif event["type"] == "sources":
                    sources_data = event["sources"]
                    yield f"event: sources\ndata: {json.dumps({'sources': sources_data})}\n\n"

        except Exception as e:
            logger.error(f"RAG query error: {e}")
            yield f"event: error\ndata: {json.dumps({'message': str(e)})}\n\n"
            return

        # Calculate latency
        latency_ms = int((time.time() - start_time) * 1000)

        # Determine model name used for message audit record
        from app.core.config import settings as app_settings
        active_provider = user_prefs.get("llm_provider") or app_settings.llm_provider
        pref_model = user_prefs.get("model_name")
        if pref_model:
            model_name = pref_model
        elif active_provider == "groq":
            model_name = app_settings.groq_model
        elif active_provider == "openai":
            model_name = app_settings.openai_model
        else:
            model_name = app_settings.ollama_model

        assistant_msg = Message(
            chat_id=chat.id,
            role="assistant",
            content=full_answer,
            model_used=model_name,
            latency_ms=latency_ms,
        )
        db.add(assistant_msg)
        db.commit()
        db.refresh(assistant_msg)

        # Save sources
        for src in sources_data:
            source = MessageSource(
                message_id=assistant_msg.id,
                document_id=src.get("document_id"),
                page=src.get("page"),
                score=src.get("score"),
                snippet=src.get("snippet"),
            )
            db.add(source)
        db.commit()

        yield f"event: done\ndata: {json.dumps({'message_id': assistant_msg.id, 'latency_ms': latency_ms})}\n\n"

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


@router.patch("/{chat_id}", response_model=ChatResponse)
def update_chat(
    chat_id: int,
    body: ChatUpdateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Rename a chat or update its associated documents."""
    chat = (
        db.query(Chat)
        .filter(Chat.id == chat_id, Chat.user_id == current_user.id)
        .first()
    )
    if not chat:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Chat not found.")

    if body.title is not None:
        chat.title = body.title

    if body.document_ids is not None:
        docs = (
            db.query(Document)
            .filter(
                Document.id.in_(body.document_ids),
                Document.user_id == current_user.id,
            )
            .all()
        )
        chat.documents = docs

    db.commit()
    db.refresh(chat)

    return ChatResponse(
        id=chat.id,
        title=chat.title,
        document_ids=[d.id for d in chat.documents],
        created_at=chat.created_at,
        updated_at=chat.updated_at,
    )


@router.delete("/{chat_id}", status_code=status.HTTP_200_OK)
def delete_chat(
    chat_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Delete a chat and all its messages."""
    chat = (
        db.query(Chat)
        .filter(Chat.id == chat_id, Chat.user_id == current_user.id)
        .first()
    )
    if not chat:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Chat not found.")

    db.delete(chat)
    db.commit()
    return {"message": "Chat deleted successfully."}


@router.get("/{chat_id}/export")
def export_chat(
    chat_id: int,
    format: str = "md",
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Export a chat conversation as markdown."""
    chat = (
        db.query(Chat)
        .filter(Chat.id == chat_id, Chat.user_id == current_user.id)
        .first()
    )
    if not chat:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Chat not found.")

    # Build markdown export
    lines = [f"# {chat.title}\n"]
    for msg in chat.messages:
        role_label = "**You:**" if msg.role == "user" else "**Assistant:**"
        lines.append(f"\n{role_label}\n{msg.content}\n")
        if msg.sources:
            lines.append("\n*Sources:*")
            for s in msg.sources:
                fname = _get_doc_filename(db, s.document_id)
                lines.append(f"- {fname}, p.{s.page}: {s.snippet[:100] if s.snippet else ''}...")

    content = "\n".join(lines)

    return StreamingResponse(
        iter([content]),
        media_type="text/markdown",
        headers={"Content-Disposition": f'attachment; filename="{chat.title}.md"'},
    )


def _get_doc_filename(db: Session, document_id: int | None) -> str:
    """Helper to get a document's filename or 'source removed'."""
    if document_id is None:
        return "source removed"
    doc = db.query(Document).filter(Document.id == document_id).first()
    return doc.filename if doc else "source removed"
