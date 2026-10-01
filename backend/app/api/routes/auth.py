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
    TokenResponse,
    UserResponse,
    RegisterResponse,
)

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


@router.delete("/me", status_code=status.HTTP_200_OK)
@router.delete("/account", status_code=status.HTTP_200_OK)
def delete_account(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Permanently delete the user's account and all associated data:
    - ChromaDB vector embeddings
    - Uploaded files on disk
    - Database records (documents, chunks, chats, messages, feedback)
    """
    user_id = current_user.id

    # 1. Delete all vectors from ChromaDB for all user documents
    try:
        from app.services.vectorstore import delete_vectors_by_document
        for doc in current_user.documents:
            delete_vectors_by_document(doc.id)
    except Exception as e:
        from app.core.logger import logger
        logger.warning(f"Error removing vectors for user {user_id}: {e}")

    # 2. Delete user's physical files directory
    try:
        import shutil
        from app.core.config import settings
        user_dir = settings.upload_path / str(user_id)
        if user_dir.exists():
            shutil.rmtree(user_dir, ignore_errors=True)
    except Exception as e:
        from app.core.logger import logger
        logger.warning(f"Error removing files for user {user_id}: {e}")

    # 3. Delete user from database (cascades to all user records)
    db.delete(current_user)
    db.commit()

    from app.core.logger import logger
    logger.info(f"User account permanently deleted: id={user_id}")
    return {"message": "Account and all associated study data permanently deleted."}
