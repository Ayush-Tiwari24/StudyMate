"""
StudyMate RAG — History Routes

GET    /api/history         — List all past chats (alias for /api/chats)
"""

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.deps import get_db, get_current_user
from app.models.user import User
from app.models.chat import Chat
from app.schemas.chat import ChatResponse, ChatListResponse

router = APIRouter(prefix="/api/history", tags=["History"])


@router.get("", response_model=ChatListResponse)
def list_history(
    search: str = "",
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """List all past chats with optional search filter."""
    query = db.query(Chat).filter(Chat.user_id == current_user.id)

    if search:
        query = query.filter(Chat.title.ilike(f"%{search}%"))

    chats = query.order_by(Chat.updated_at.desc()).all()

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
