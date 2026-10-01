"""
StudyMate RAG — Settings Routes

GET /api/settings  — Read user preferences merged with defaults
PUT /api/settings  — Update user preferences with strict validation
"""

from typing import Optional, Literal
from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field, ConfigDict
from sqlalchemy.orm import Session
from sqlalchemy.orm.attributes import flag_modified

from app.api.deps import get_db, get_current_user
from app.core.config import settings
from app.models.user import User

router = APIRouter(prefix="/api/settings", tags=["Settings"])


class SettingsUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    theme: Optional[Literal["light", "night", "dark", "system"]] = None
    llm_provider: Optional[Literal["groq", "openai", "ollama"]] = None
    model_name: Optional[str] = Field(None, max_length=100)
    temperature: Optional[float] = Field(None, ge=0.0, le=1.0)
    top_k: Optional[int] = Field(None, ge=1, le=10)
    font_scale: Optional[Literal["small", "medium", "large"]] = None
    text_size: Optional[Literal["small", "medium", "large"]] = None
    show_chunks: Optional[bool] = None


def get_default_settings() -> dict:
    """Return default settings dictionary derived from core configuration."""
    provider = settings.llm_provider
    if provider == "groq":
        default_model = settings.groq_model
    elif provider == "openai":
        default_model = settings.openai_model
    else:
        default_model = settings.ollama_model

    return {
        "theme": "light",
        "llm_provider": provider,
        "model_name": default_model,
        "temperature": settings.llm_temperature,
        "top_k": settings.top_k,
        "font_scale": "medium",
        "show_chunks": False,
    }


@router.get("")
def get_settings(current_user: User = Depends(get_current_user)):
    """Return the current user's preferences merged with system defaults."""
    merged = get_default_settings()
    if current_user.preferences:
        merged.update(current_user.preferences)
    return merged


@router.put("")
def update_settings(
    body: SettingsUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Update user preferences (partial update with strict validation)."""
    prefs = dict(current_user.preferences or {})
    update_data = body.model_dump(exclude_none=True)

    # Normalize text_size to font_scale
    if "text_size" in update_data:
        update_data["font_scale"] = update_data.pop("text_size")

    prefs.update(update_data)
    current_user.preferences = prefs

    # Force SQLAlchemy to detect JSON change
    flag_modified(current_user, "preferences")
    db.commit()

    merged = get_default_settings()
    merged.update(prefs)
    return merged

