"""
StudyMate RAG — Auth Schemas

Pydantic models for authentication requests and responses.
"""

import re
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field, ConfigDict, field_validator

EMAIL_REGEX = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


class RegisterRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=100, examples=["Amit Kumar"])
    email: str = Field(..., examples=["amit@example.com"])
    password: str = Field(..., min_length=6, max_length=128)

    @field_validator("email")
    @classmethod
    def normalize_email(cls, v: str) -> str:
        v = v.strip().lower()
        if not EMAIL_REGEX.match(v):
            raise ValueError("value is not a valid email address: missing @ or domain")
        return v


class LoginRequest(BaseModel):
    email: str = Field(..., examples=["amit@example.com"])
    password: str = Field(...)

    @field_validator("email")
    @classmethod
    def normalize_email(cls, v: str) -> str:
        v = v.strip().lower()
        if not EMAIL_REGEX.match(v):
            raise ValueError("value is not a valid email address: missing @ or domain")
        return v


class DeleteAccountRequest(BaseModel):
    password: str = Field(..., min_length=1, description="Password confirmation to delete account")


class RefreshTokenRequest(BaseModel):
    refresh_token: str = Field(..., min_length=1, description="Refresh token to rotate")


class LogoutRequest(BaseModel):
    refresh_token: Optional[str] = Field(None, description="Optional refresh token to revoke on logout")


# ── Responses ────────────────────────────────────────────────────

class UserResponse(BaseModel):
    id: int
    name: str
    email: str
    preferences: dict = {}
    created_at: datetime
    storage_used_bytes: Optional[int] = 0
    storage_quota_bytes: Optional[int] = 0

    model_config = ConfigDict(from_attributes=True)


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    user: Optional[UserResponse] = None


class RegisterResponse(UserResponse):
    access_token: Optional[str] = None
    refresh_token: Optional[str] = None
    token_type: str = "bearer"


class MessageResponse(BaseModel):
    """Generic message response for simple confirmations."""
    message: str
