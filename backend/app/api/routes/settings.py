"""
StudyMate RAG — Settings Routes

GET /api/settings  — Read user preferences
PUT /api/settings  — Update user preferences
"""

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from typing import Optional
from sqlalchemy.orm import Session

from app.api.deps import get_db, get_current_user
from app.models.user import User

router = APIRouter(prefix="/api/settings", tags=["Settings"])


class SettingsUpdate(BaseModel):
    theme: Optional[str] = None          # "dark" | "light"
    llm_provider: Optional[str] = None   # "openai" | "ollama"
    model_name: Optional[str] = None
    temperature: Optional[float] = None
    top_k: Optional[int] = None
    show_chunks: Optional[bool] = None


@router.get("")
def get_settings(current_user: User = Depends(get_current_user)):
    """Return the current user's preferences."""
    return current_user.preferences or {}


@router.put("")
def update_settings(
    body: SettingsUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Update user preferences (partial update)."""
    prefs = current_user.preferences or {}
    update_data = body.model_dump(exclude_none=True)
    prefs.update(update_data)
    current_user.preferences = prefs

    # Force SQLAlchemy to detect JSON change
    from sqlalchemy.orm.attributes import flag_modified
    flag_modified(current_user, "preferences")

    db.commit()
    return prefs
