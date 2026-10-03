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

from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session, selectinload

from app.api.deps import get_db, get_current_user
from app.core.config import settings
from app.models.user import User
from app.models.chat import Chat
from app.models.document import Document
from app.models.message import Message
from app.schemas.chat import (
    ChatCreateRequest,
    ChatUpdateRequest,
    AskRequest,
    ChatResponse,
    ChatDetailResponse,
    ChatListResponse,
    MessageResponse,
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
        .options(selectinload(Chat.documents))
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
    """Get a chat with all its messages."""
    chat = (
        db.query(Chat)
        .options(
            selectinload(Chat.documents),
            selectinload(Chat.messages).selectinload(Message.feedback),
        )
        .filter(Chat.id == chat_id, Chat.user_id == current_user.id)
        .first()
    )
    if not chat:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Chat not found.")

    messages = [
        MessageResponse(
            id=msg.id,
            role=msg.role,
            content=msg.content,
            model_used=msg.model_used,
            latency_ms=msg.latency_ms,
            feedback_value=msg.feedback.value if msg.feedback else None,
            created_at=msg.created_at,
        )
        for msg in chat.messages
    ]

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
    request: Request,
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

    from app.utils.timing import AskTimer
    from app.models.document import Document
    from app.db.session import SessionLocal

    timer = AskTimer()

    # 1. Short initial transaction: save user message, pre-fetch history & doc titles
    with timer.measure("init_db"):
        user_msg = Message(chat_id=chat.id, role="user", content=body.question)
        db.add(user_msg)
        db.commit()

        # Pre-fetch recent messages for conversation history
        recent_msgs = (
            db.query(Message)
            .filter(Message.chat_id == chat.id)
            .order_by(Message.created_at.desc())
            .limit(settings.history_window * 2)
            .all()
        )
        recent_msgs.reverse()
        prefetched_history = [{"role": m.role, "content": m.content} for m in recent_msgs]

        # Pre-fetch document titles
        docs = db.query(Document).filter(Document.id.in_(doc_ids)).all()
        prefetched_doc_titles = [d.filename.replace('.pdf', '').strip() for d in docs]

        # Pre-fetch user preferences and id before releasing db connection
        current_user_id = current_user.id
        user_prefs = dict(current_user.preferences or {})

    # Release initial DB connection back to the connection pool immediately!
    db.close()

    # Stream the response via SSE (zero DB connections held during streaming)
    async def event_stream() -> AsyncGenerator[str, None]:
        full_answer = ""

        # Send initial keep-alive comment so proxy buffers are flushed immediately
        yield ": ready\n\n"

        try:
            from app.services.generation.rag_chain import rag_query
            last_ping_time = time.time()

            async for event in rag_query(
                question=body.question,
                chat_id=chat_id,
                user_id=current_user_id,
                document_ids=doc_ids,
                top_k=body.top_k or user_prefs.get("top_k"),
                db=None,
                user_preferences=user_prefs,
                timer=timer,
                prefetched_history=prefetched_history,
                prefetched_doc_titles=prefetched_doc_titles,
            ):
                if await request.is_disconnected():
                    logger.info(f"Client disconnected from SSE stream for chat {chat_id}")
                    return

                now = time.time()
                if now - last_ping_time > 15.0:
                    yield ": ping\n\n"
                    last_ping_time = now

                if event["type"] == "token":
                    full_answer += event["text"]
                    yield f"event: token\ndata: {json.dumps({'text': event['text']})}\n\n"
                    last_ping_time = now

        except Exception as e:
            logger.error(f"RAG query error: {e}")
            yield f"event: error\ndata: {json.dumps({'message': str(e)})}\n\n"
            return

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

        # 2. Short final transaction: save assistant message
        with timer.measure("save"):
            save_db = SessionLocal()
            try:
                assistant_msg = Message(
                    chat_id=chat_id,
                    role="assistant",
                    content=full_answer,
                    model_used=model_name,
                    latency_ms=int(timer.timings.get("total_ms", 0)),
                )
                save_db.add(assistant_msg)
                save_db.commit()
                saved_msg_id = assistant_msg.id
            finally:
                save_db.close()

        timings = timer.finish()
        latency_ms = int(timings.get("total_ms", 0))

        # Log structured timing line without secrets or document texts
        logger.info(timer.format_log(chat_id=chat_id, user_id=current_user_id, model=model_name))

        yield f"event: done\ndata: {json.dumps({'message_id': saved_msg_id, 'latency_ms': latency_ms, 'timings': timings})}\n\n"

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
    """Export a chat conversation as plain markdown."""
    chat = (
        db.query(Chat)
        .options(
            selectinload(Chat.messages),
        )
        .filter(Chat.id == chat_id, Chat.user_id == current_user.id)
        .first()
    )
    if not chat:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Chat not found.")

    # Build markdown export with plain questions and answers only
    lines = [f"# {chat.title}\n"]
    for msg in chat.messages:
        role_label = "**You:**" if msg.role == "user" else "**Assistant:**"
        lines.append(f"\n{role_label}\n{msg.content}\n")

    content = "\n".join(lines)

    return StreamingResponse(
        iter([content]),
        media_type="text/markdown",
        headers={"Content-Disposition": f'attachment; filename="{chat.title}.md"'},
    )

