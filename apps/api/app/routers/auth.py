"""Authentication API endpoints."""

import logging
from datetime import datetime, timedelta
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status

from app.auth import create_access_token, create_refresh_token, hash_password, verify_password, verify_token
from app.dependencies import get_current_user
from app.schemas.auth import (
    ChangePasswordRequest,
    CurrentUserResponse,
    LoginRequest,
    LoginResponse,
    PasswordResetConfirm,
    PasswordResetRequest,
    RefreshTokenRequest,
    TokenResponse,
)

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/v1/auth", tags=["authentication"])

# In-memory user store (Phase 1 MVP - replace with database in T-201+)
# Initialized lazily to avoid hashing at module import time
USERS_DB = {}
ORGANIZATIONS_DB = {}


def _init_test_data():
    """Initialize test data on first use."""
    global USERS_DB, ORGANIZATIONS_DB
    if not ORGANIZATIONS_DB:
        ORGANIZATIONS_DB[1] = {
            "org_id": 1,
            "name": "Default Organization",
            "subscription_tier": "enterprise",
        }
    if not USERS_DB:
        USERS_DB[1] = {
            "user_id": 1,
            "email": "admin@example.com",
            "password_hash": hash_password("password123"),
            "first_name": "Admin",
            "last_name": "User",
            "org_id": 1,
            "role": "admin",
            "mfa_enabled": False,
            "created_at": datetime.utcnow(),
            "last_login": None,
        }


@router.post(
    "/login",
    response_model=LoginResponse,
    status_code=status.HTTP_200_OK,
    summary="User login",
    responses={
        401: {"description": "Invalid credentials"},
        429: {"description": "Too many failed login attempts"},
    },
)
async def login(request: LoginRequest) -> LoginResponse:
    """
    Login with email and password.

    Returns JWT access and refresh tokens.

    **Implementation notes:**
    - T-103: Email/password login endpoint
    - T-108: Rate limiting on failed attempts (5 per 15 min)
    - Later: Azure AD/Entra ID oauth flow (T-109)
    """
    _init_test_data()
    logger.info(f"Login attempt for {request.email}")

    # Find user by email (simplified - will use DB in T-201+)
    user = None
    for u in USERS_DB.values():
        if u["email"].lower() == request.email.lower():
            user = u
            break

    if not user or not verify_password(request.password, user["password_hash"]):
        logger.warning(f"Failed login attempt for {request.email}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
        )

    # Create tokens
    access_token, access_expires = create_access_token(
        user_id=user["user_id"],
        email=user["email"],
        org_id=user["org_id"],
        role=user["role"],
    )

    refresh_token, _ = create_refresh_token(
        user_id=user["user_id"],
        email=user["email"],
        org_id=user["org_id"],
    )

    # Update last login (will persist to DB in T-201+)
    user["last_login"] = datetime.utcnow()

    logger.info(f"Successful login for {request.email}")

    return LoginResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        expires_in=int(access_expires.timestamp() - datetime.utcnow().timestamp()),
        user_id=user["user_id"],
        email=user["email"],
        first_name=user["first_name"],
        last_name=user["last_name"],
        org_id=user["org_id"],
        role=user["role"],
    )


@router.post(
    "/refresh",
    response_model=TokenResponse,
    status_code=status.HTTP_200_OK,
    summary="Refresh access token",
    responses={401: {"description": "Invalid refresh token"}},
)
async def refresh(request: RefreshTokenRequest) -> TokenResponse:
    """
    Refresh access token using refresh token.

    **T-105: Refresh token endpoint**
    """
    token_data = verify_token(request.refresh_token, token_type="refresh")

    if not token_data:
        logger.warning(f"Failed refresh attempt: invalid token")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired refresh token",
        )

    # Create new access token
    access_token, access_expires = create_access_token(
        user_id=token_data.user_id,
        email=token_data.email,
        org_id=token_data.org_id,
        role=token_data.role,
    )

    logger.info(f"Token refreshed for user {token_data.user_id}")

    return TokenResponse(
        access_token=access_token,
        refresh_token=request.refresh_token,
        expires_in=int(access_expires.timestamp() - datetime.utcnow().timestamp()),
    )


@router.post(
    "/logout",
    status_code=status.HTTP_200_OK,
    summary="User logout",
    response_model=dict,
)
async def logout(current_user=Depends(get_current_user)) -> dict:
    """
    Logout (invalidate tokens).

    **T-104: Logout endpoint**

    Note: In stateless JWT auth, tokens are valid until expiry.
    For true logout, consider:
    - Token blacklist (Redis)
    - Short access token lifetime
    - Refresh token rotation
    """
    logger.info(f"Logout for user {current_user.user_id}")
    return {"message": "Successfully logged out"}


@router.get(
    "/me",
    response_model=CurrentUserResponse,
    status_code=status.HTTP_200_OK,
    summary="Get current user",
)
async def get_current_user_info(current_user=Depends(get_current_user)) -> CurrentUserResponse:
    """
    Get current authenticated user info.

    **T-106: Get current user endpoint**
    """
    _init_test_data()
    user = USERS_DB.get(current_user.user_id)
    org = ORGANIZATIONS_DB.get(current_user.org_id)

    if not user or not org:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    return CurrentUserResponse(
        user_id=user["user_id"],
        email=user["email"],
        first_name=user["first_name"],
        last_name=user["last_name"],
        org_id=user["org_id"],
        org_name=org["name"],
        role=user["role"],
        mfa_enabled=user["mfa_enabled"],
        created_at=user["created_at"],
        last_login=user["last_login"],
    )


@router.post(
    "/password-reset",
    status_code=status.HTTP_200_OK,
    summary="Request password reset",
    response_model=dict,
)
async def request_password_reset(request: PasswordResetRequest) -> dict:
    """
    Request password reset (sends email with token).

    **T-110: Password reset flow**

    Phase 1: Simplified (no actual email sending, just returns token)
    Future: Integrate with email service
    """
    _init_test_data()
    logger.info(f"Password reset requested for {request.email}")

    # Find user
    user = None
    for u in USERS_DB.values():
        if u["email"].lower() == request.email.lower():
            user = u
            break

    # Always return success (don't leak whether email exists)
    if not user:
        return {"message": "If email exists, password reset link sent"}

    # Create reset token (valid for 1 hour)
    reset_expires = datetime.utcnow() + timedelta(hours=1)
    reset_payload = {
        "user_id": user["user_id"],
        "email": user["email"],
        "type": "reset",
        "exp": reset_expires,
        "iat": datetime.utcnow(),
    }

    from jose import jwt
    from app.config import settings

    reset_token = jwt.encode(
        reset_payload,
        settings.jwt_secret_key,
        algorithm=settings.jwt_algorithm,
    )

    # TODO: Send email with reset link containing token
    # For now, just log it
    logger.info(f"Reset token generated: {reset_token[:20]}...")

    return {"message": "If email exists, password reset link sent"}


@router.post(
    "/password-reset/confirm",
    status_code=status.HTTP_200_OK,
    summary="Confirm password reset",
    response_model=dict,
)
async def confirm_password_reset(request: PasswordResetConfirm) -> dict:
    """
    Confirm password reset with new password.

    **T-110: Password reset confirmation**
    """
    token_data = verify_token(request.token, token_type="reset")

    if not token_data:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid or expired reset token",
        )

    user = USERS_DB.get(token_data.user_id)
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    # Update password
    user["password_hash"] = hash_password(request.new_password)
    logger.info(f"Password reset for user {token_data.user_id}")

    return {"message": "Password successfully reset"}


@router.post(
    "/change-password",
    status_code=status.HTTP_200_OK,
    summary="Change password (authenticated user)",
    response_model=dict,
)
async def change_password(
    request: ChangePasswordRequest,
    current_user=Depends(get_current_user),
) -> dict:
    """
    Change password for authenticated user.

    **T-110: Change password endpoint**
    """
    _init_test_data()
    user = USERS_DB.get(current_user.user_id)
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    # Verify current password
    if not verify_password(request.current_password, user["password_hash"]):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Current password is incorrect",
        )

    # Update password
    user["password_hash"] = hash_password(request.new_password)
    logger.info(f"Password changed for user {current_user.user_id}")

    return {"message": "Password successfully changed"}
