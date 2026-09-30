"""
StudyMate RAG — Feedback Routes

POST /api/messages/{id}/feedback  — Submit thumbs up/down for a message
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.deps import get_db, get_current_user
from app.models.user import User
from app.models.message import Message, Feedback
from app.models.chat import Chat
from app.schemas.chat import FeedbackRequest

router = APIRouter(prefix="/api/messages", tags=["Feedback"])


@router.post("/{message_id}/feedback", status_code=status.HTTP_201_CREATED)
def submit_feedback(
    message_id: int,
    body: FeedbackRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Submit thumbs up (1) or thumbs down (-1) feedback on a message."""
    # Verify message exists and belongs to user's chat
    msg = db.query(Message).filter(Message.id == message_id).first()
    if not msg:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Message not found.")

    chat = db.query(Chat).filter(Chat.id == msg.chat_id, Chat.user_id == current_user.id).first()
    if not chat:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied.")

    # Upsert feedback
    existing = db.query(Feedback).filter(Feedback.message_id == message_id).first()
    if existing:
        existing.value = body.value
        existing.comment = body.comment
    else:
        feedback = Feedback(
            message_id=message_id,
            value=body.value,
            comment=body.comment,
        )
        db.add(feedback)

    db.commit()
    return {"message": "Feedback recorded."}
