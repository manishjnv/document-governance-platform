"""Authentication request/response schemas."""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, EmailStr, Field


class TokenData(BaseModel):
    """JWT token payload."""

    user_id: int
    email: str
    org_id: int
    role: str
    exp: datetime  # Expiration time
    iat: datetime  # Issued at
    type: str = "access"  # access | refresh


class TokenResponse(BaseModel):
    """Token response from login/refresh endpoints."""

    access_token: str = Field(..., description="JWT access token")
    refresh_token: str = Field(..., description="JWT refresh token")
    expires_in: int = Field(..., description="Access token expiry in seconds")
    token_type: str = "bearer"


class LoginRequest(BaseModel):
    """Login request body."""

    email: EmailStr = Field(..., description="User email")
    password: str = Field(..., min_length=8, description="User password")


class LoginResponse(TokenResponse):
    """Extended login response with user info."""

    user_id: int
    email: str
    first_name: str
    last_name: str
    org_id: int
    role: str


class RefreshTokenRequest(BaseModel):
    """Refresh token request."""

    refresh_token: str = Field(..., description="Current refresh token")


class PasswordResetRequest(BaseModel):
    """Password reset request."""

    email: EmailStr = Field(..., description="User email")


class PasswordResetConfirm(BaseModel):
    """Password reset confirmation with new password."""

    token: str = Field(..., description="Reset token from email")
    new_password: str = Field(..., min_length=8, description="New password")


class ChangePasswordRequest(BaseModel):
    """Change password (authenticated user)."""

    current_password: str = Field(..., description="Current password")
    new_password: str = Field(..., min_length=8, description="New password")


class CurrentUserResponse(BaseModel):
    """Current authenticated user info."""

    user_id: int
    email: str
    first_name: str
    last_name: str
    org_id: int
    org_name: str
    role: str
    mfa_enabled: bool
    created_at: datetime
    last_login: Optional[datetime] = None


class UserCreateRequest(BaseModel):
    """Admin: Create new user."""

    email: EmailStr
    first_name: str = Field(..., min_length=1, max_length=100)
    last_name: str = Field(..., min_length=1, max_length=100)
    password: str = Field(..., min_length=8)
    role: str = Field(..., pattern="^(admin|reviewer|viewer)$")


class UserUpdateRequest(BaseModel):
    """Update user info (by self or admin)."""

    first_name: Optional[str] = Field(None, min_length=1, max_length=100)
    last_name: Optional[str] = Field(None, min_length=1, max_length=100)
    role: Optional[str] = Field(None, pattern="^(admin|reviewer|viewer)$")


class MFASetupResponse(BaseModel):
    """MFA setup response with QR code."""

    secret: str
    qr_code_url: str
    backup_codes: list[str]


class MFAVerifyRequest(BaseModel):
    """MFA verification code."""

    code: str = Field(..., pattern=r"^\d{6}$")
