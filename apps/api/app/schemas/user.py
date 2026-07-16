"""User request/response schemas.

Named distinctly from app/schemas/auth.py's UserCreateRequest / UserUpdateRequest
(those use int user_id/org_id and a first_name/last_name split, predating the
UUID-based, full_name schema in 3_DATABASE_SCHEMA.md — reconciling that stub is
out of scope here; flagging so it isn't mistaken for a duplicate by accident).
"""

from datetime import datetime
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict, EmailStr, Field

from app.models.enums import UserRole


class UserCreate(BaseModel):
    """Create a user within an organization."""

    org_id: UUID
    email: EmailStr
    password: Optional[str] = Field(None, min_length=8, description="Omit for SSO-only users")
    full_name: Optional[str] = Field(None, max_length=255)
    role: UserRole = UserRole.VIEWER


class UserUpdate(BaseModel):
    """Partial update of a user."""

    full_name: Optional[str] = Field(None, max_length=255)
    role: Optional[UserRole] = None
    is_active: Optional[bool] = None


class UserRead(BaseModel):
    """User as returned by the API. Never includes password_hash."""

    model_config = ConfigDict(from_attributes=True)

    user_id: UUID
    org_id: UUID
    email: EmailStr
    full_name: Optional[str] = None
    role: UserRole
    is_active: bool
    last_login: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime
