"""
StudyMate RAG — Auth Routes

POST /api/auth/register  — Create a new account
POST /api/auth/login     — Authenticate and get JWT tokens
GET  /api/auth/me        — Get current user profile
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.deps import get_db, get_current_user
from app.core.security import hash_password, verify_password, create_access_token, create_refresh_token
from app.models.user import User
from app.schemas.auth import (
    RegisterRequest,
    LoginRequest,
    DeleteAccountRequest,
    TokenResponse,
    UserResponse,
    RegisterResponse,
)
from app.core.logger import logger

router = APIRouter(prefix="/api/auth", tags=["Authentication"])


@router.post("/register", response_model=RegisterResponse, status_code=status.HTTP_201_CREATED)
def register(body: RegisterRequest, db: Session = Depends(get_db)):
    """Create a new user account and return JWT session."""
    # Check for duplicate email
    existing = db.query(User).filter(User.email == body.email).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="An account with this email already exists.",
        )

    user = User(
        name=body.name,
        email=body.email,
        password_hash=hash_password(body.password),
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    access_token = create_access_token(data={"sub": str(user.id)})
    refresh_token = create_refresh_token(data={"sub": str(user.id)})

    return RegisterResponse(
        id=user.id,
        name=user.name,
        email=user.email,
        preferences=user.preferences or {},
        created_at=user.created_at,
        access_token=access_token,
        refresh_token=refresh_token,
    )


@router.post("/login", response_model=TokenResponse)
def login(body: LoginRequest, db: Session = Depends(get_db)):
    """Authenticate and return JWT access + refresh tokens and user info."""
    user = db.query(User).filter(User.email == body.email).first()

    if not user or not verify_password(body.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password.",
        )

    access_token = create_access_token(data={"sub": str(user.id)})
    refresh_token = create_refresh_token(data={"sub": str(user.id)})

    return TokenResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        user=UserResponse.model_validate(user),
    )


@router.get("/me", response_model=UserResponse)
def get_me(current_user: User = Depends(get_current_user)):
    """Return the currently authenticated user's profile."""
    return current_user


@router.get("/me/export")
def export_user_data(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Export the user's complete chat history and documents metadata as JSON."""
    chats_data = []
    for chat in current_user.chats:
        msgs = []
        for m in chat.messages:
            sources = [
                {
                    "document_id": s.document_id,
                    "page": s.page,
                    "score": s.score,
                    "snippet": s.snippet,
                }
                for s in m.sources
            ]
            msgs.append({
                "id": m.id,
                "role": m.role,
                "content": m.content,
                "model_used": m.model_used,
                "latency_ms": m.latency_ms,
                "created_at": m.created_at.isoformat() if m.created_at else None,
                "sources": sources,
            })
        chats_data.append({
            "id": chat.id,
            "title": chat.title,
            "created_at": chat.created_at.isoformat() if chat.created_at else None,
            "updated_at": chat.updated_at.isoformat() if chat.updated_at else None,
            "documents": [{"id": d.id, "filename": d.filename} for d in chat.documents],
            "messages": msgs,
        })
    return {
        "user": {
            "id": current_user.id,
            "name": current_user.name,
            "email": current_user.email,
            "created_at": current_user.created_at.isoformat() if current_user.created_at else None,
        },
        "chats": chats_data,
    }


@router.delete("/me", status_code=status.HTTP_200_OK)
@router.delete("/account", status_code=status.HTTP_200_OK)
def delete_account(
    body: DeleteAccountRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Permanently delete the user's account and all associated data.
    Requires password confirmation in the request body.
    Deletes in order: SQL rows committed, vectors, stored files.
    """
    # 1. Verify password confirmation
    if not verify_password(body.password, current_user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Incorrect password.",
        )

    user_id = current_user.id
    doc_ids = [doc.id for doc in current_user.documents]

    # 2. Delete user row in SQL and commit (cascades to documents, chats, chunks, messages, feedback)
    db.delete(current_user)
    db.commit()
    logger.info(f"User records deleted from SQL: id={user_id}")

    # 3. Delete user's vectors from vector store (best-effort)
    try:
        from app.services.vectorstore import delete_vectors_by_document
        for doc_id in doc_ids:
            delete_vectors_by_document(doc_id)
    except Exception as e:
        logger.warning(f"Error removing vectors for user {user_id}: {e}")

    # 4. Delete user's stored files (best-effort)
    try:
        from app.services.storage import get_storage
        storage = get_storage()
        storage.delete_user_files(user_id)
    except Exception as e:
        logger.warning(f"Error removing files for user {user_id}: {e}")

    logger.info(f"User account permanently deleted: id={user_id}")
    return {"message": "Account and all associated study data permanently deleted."}
