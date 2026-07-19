"""Authentication request/response schemas."""

import uuid
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, EmailStr, Field


class TokenData(BaseModel):
    """JWT token payload."""

    user_id: uuid.UUID
    email: str
    org_id: uuid.UUID
    role: str
    exp: datetime  # Expiration time
    iat: datetime  # Issued at
    type: str = "access"  # access | refresh


class RefreshTokenData(BaseModel):
    """Refresh-token JWT payload. Deliberately excludes `role`: refresh
    re-fetches the user from the DB to mint a fresh access token, so a
    stale/changed role never rides along in a long-lived refresh token."""

    user_id: uuid.UUID
    email: str
    org_id: uuid.UUID
    exp: datetime
    iat: datetime
    type: str = "refresh"


class ResetTokenData(BaseModel):
    """Password-reset JWT payload -- deliberately lighter than TokenData: a
    reset token proves "this email requested a reset", not org/role
    authority, so it doesn't carry org_id/role claims."""

    user_id: uuid.UUID
    email: str
    exp: datetime
    iat: datetime
    type: str = "reset"


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

    user_id: uuid.UUID
    email: str
    first_name: str
    last_name: str
    org_id: uuid.UUID
    role: str


class SignupRequest(BaseModel):
    """Self-service signup: creates a NEW organization and its first user
    (role=admin) together. There's no platform-superadmin role in this
    system -- every user is scoped to exactly one org -- so this is the
    only way an organization comes into existence via the API (previously
    orgs could only be seeded directly in the DB, no endpoint existed)."""

    org_name: str = Field(..., min_length=1, max_length=255, description="New organization name")
    email: EmailStr = Field(..., description="Admin user's email")
    password: str = Field(..., min_length=8, description="Admin user's password")
    full_name: Optional[str] = Field(None, max_length=255)


class SignupResponse(TokenResponse):
    """Signup response: same shape as login, the caller is immediately
    authenticated as the new org's first admin."""

    user_id: uuid.UUID
    email: str
    org_id: uuid.UUID
    org_name: str
    role: str


class RefreshTokenRequest(BaseModel):
    """Refresh token request."""

    refresh_token: str = Field(..., description="Current refresh token")


class OtpRequestRequest(BaseModel):
    """Request an email login code."""

    email: EmailStr = Field(..., description="User email")


class OtpVerifyRequest(BaseModel):
    """Verify an email login code -- same response shape as password login."""

    email: EmailStr = Field(..., description="User email")
    code: str = Field(..., pattern=r"^\d{6}$", description="6-digit code from email")


class GoogleLoginRequest(BaseModel):
    """Google Sign-In: the ID token credential returned by Google Identity
    Services on the frontend, verified server-side against Google's public
    keys and GOOGLE_CLIENT_ID."""

    id_token: str = Field(..., description="Google-issued ID token (JWT)")


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

    user_id: uuid.UUID
    email: str
    first_name: str
    last_name: str
    org_id: uuid.UUID
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
