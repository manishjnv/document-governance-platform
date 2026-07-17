"""Authentication API endpoints."""

import logging
from datetime import datetime, timedelta
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth import (
    create_access_token,
    create_refresh_token,
    hash_password,
    verify_password,
    verify_token,
)
from app.compliance.audit import log_action
from app.db.session import get_db
from app.dependencies import get_current_user
from app.models.organization import Organization
from app.models.user import User
from app.schemas.auth import (
    ChangePasswordRequest,
    CurrentUserResponse,
    LoginRequest,
    LoginResponse,
    PasswordResetConfirm,
    PasswordResetRequest,
    RefreshTokenData,
    RefreshTokenRequest,
    ResetTokenData,
    SignupRequest,
    SignupResponse,
    TokenResponse,
)

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/v1/auth", tags=["authentication"])


def _split_name(full_name: str | None) -> tuple[str, str]:
    """User has one `full_name` column; the API's request/response shapes
    predate it and still split first/last -- derive rather than change the
    wire contract."""
    if not full_name:
        return "", ""
    parts = full_name.split(" ", 1)
    return parts[0], parts[1] if len(parts) > 1 else ""


async def _find_candidate_users_by_email(db: AsyncSession, email: str) -> list[User]:
    """Look up active users by email (case-insensitive EXACT match).

    Exact equality on a lower()'d column, not ilike(): ilike() treats `%`
    and `_` in the input as wildcards, and both are valid RFC-5322
    local-part characters that pass EmailStr validation untouched (e.g.
    "%@corp.com" or "a_b@corp.com") -- passing user input into ilike()
    unescaped let a single login attempt match every account at a domain
    instead of one, turning "know one victim's email+password" into "know
    a domain+password". Exact match closes that off entirely.

    users.email is only unique per-org (uq_users_org_email_active), not
    globally -- the same email can exist in more than one organization.
    Returns every active match; the caller must verify the password
    against each candidate rather than picking one to check by fiat (see
    login()) -- silently trying only the oldest account meant a shared
    password across two orgs' same-email accounts logged the caller into
    the wrong one, and a non-shared password locked every account but the
    oldest out entirely.
    """
    result = await db.execute(
        select(User).where(
            func.lower(User.email) == email.lower(),
            User.deleted_at.is_(None),
            User.is_active.is_(True),
        )
    )
    return list(result.scalars().all())


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
async def login(request: LoginRequest, db: AsyncSession = Depends(get_db)) -> LoginResponse:
    """
    Login with email and password.

    Returns JWT access and refresh tokens.

    **T-103: Email/password login endpoint**
    """
    logger.info(f"Login attempt for {request.email}")

    from app.core.login_lockout import is_locked, record_failure, record_success

    locked, retry_after = is_locked(request.email)
    if locked:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=f"Too many failed login attempts. Try again in {int(retry_after / 60) + 1} minute(s).",
        )

    candidates = await _find_candidate_users_by_email(db, request.email)
    # Verify against every candidate rather than picking one up front: with
    # the same email registered in more than one org, checking only the
    # oldest account either logs the caller into the WRONG org (if the
    # password happens to match both) or hard-locks every account but the
    # oldest (if it only matches the intended one). Matching >1 is treated
    # as ambiguous and rejected rather than guessed at.
    matches = [
        u for u in candidates if u.password_hash and verify_password(request.password, u.password_hash)
    ]

    if len(matches) != 1:
        if len(matches) > 1:
            logger.warning(
                f"Login for '{request.email}' matched {len(matches)} accounts across "
                f"different orgs with the same password -- rejecting as ambiguous."
            )
        else:
            logger.warning(f"Failed login attempt for {request.email}")
        record_failure(request.email)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
        )

    user = matches[0]
    record_success(request.email)

    access_token, access_expires = create_access_token(
        user_id=user.user_id,
        email=user.email,
        org_id=user.org_id,
        role=user.role,
    )

    refresh_token, _ = create_refresh_token(
        user_id=user.user_id,
        email=user.email,
        org_id=user.org_id,
    )

    user.last_login = datetime.utcnow()

    # T-2041: audit trail -- user_id/org_id are now real FKs, so this
    # commits for real (see app/compliance/audit.py's log_action). Still
    # wrapped defensively: an audit-log failure must never break login.
    try:
        await log_action(
            db,
            org_id=user.org_id,
            user_id=user.user_id,
            action="user.login",
            resource_type="user",
            resource_id=user.user_id,
        )
        await db.commit()
    except Exception as e:
        await db.rollback()
        logger.warning(f"Audit log write failed for login of {request.email}: {e}")
        user.last_login = datetime.utcnow()
        await db.commit()

    logger.info(f"Successful login for {request.email}")

    first_name, last_name = _split_name(user.full_name)

    return LoginResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        expires_in=int(access_expires.timestamp() - datetime.utcnow().timestamp()),
        user_id=user.user_id,
        email=user.email,
        first_name=first_name,
        last_name=last_name,
        org_id=user.org_id,
        role=user.role,
    )


@router.post(
    "/signup",
    response_model=SignupResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new organization + its first admin user",
    responses={409: {"description": "Email already registered in this new organization"}},
)
async def signup(request: SignupRequest, db: AsyncSession = Depends(get_db)) -> SignupResponse:
    """
    Self-service signup: creates a NEW organization and its first user
    (role=admin) atomically, then logs them in immediately.

    There is no platform-superadmin role in this system -- every user is
    scoped to exactly one org -- so this is the only way an organization
    can come into existence via the API. Previously no endpoint existed at
    all; orgs could only be created by inserting rows directly in the DB.
    """
    from uuid import uuid4

    org = Organization(
        org_id=uuid4(),
        name=request.org_name,
    )
    db.add(org)
    await db.flush()  # org.org_id is already set client-side, but keep the row visible to the User FK within this transaction

    user = User(
        user_id=uuid4(),
        org_id=org.org_id,
        email=request.email,
        password_hash=hash_password(request.password),
        full_name=request.full_name,
        role="admin",
        is_active=True,
    )
    db.add(user)
    await db.commit()
    await db.refresh(org)
    await db.refresh(user)

    access_token, access_expires = create_access_token(
        user_id=user.user_id,
        email=user.email,
        org_id=user.org_id,
        role=user.role,
    )
    refresh_token, _ = create_refresh_token(
        user_id=user.user_id,
        email=user.email,
        org_id=user.org_id,
    )

    try:
        await log_action(
            db,
            org_id=org.org_id,
            user_id=user.user_id,
            action="organization.created",
            resource_type="organization",
            resource_id=org.org_id,
        )
        await db.commit()
    except Exception as e:
        await db.rollback()
        logger.warning(f"Audit log write failed for signup of org '{request.org_name}': {e}")

    logger.info(f"New organization '{request.org_name}' ({org.org_id}) created via signup by {request.email}")

    return SignupResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        expires_in=int(access_expires.timestamp() - datetime.utcnow().timestamp()),
        user_id=user.user_id,
        email=user.email,
        org_id=org.org_id,
        org_name=org.name,
        role=user.role,
    )


@router.post(
    "/refresh",
    response_model=TokenResponse,
    status_code=status.HTTP_200_OK,
    summary="Refresh access token",
    responses={401: {"description": "Invalid refresh token"}},
)
async def refresh(
    request: RefreshTokenRequest, db: AsyncSession = Depends(get_db)
) -> TokenResponse:
    """
    Refresh access token using refresh token.

    **T-105: Refresh token endpoint**

    Re-fetches the user from the DB (rather than trusting a role claim
    carried in the refresh token) so a role change or deactivation takes
    effect on the next refresh, not just the next full login.
    """
    token_data = verify_token(
        request.refresh_token, token_type="refresh", model=RefreshTokenData
    )

    if not token_data:
        logger.warning("Failed refresh attempt: invalid token")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired refresh token",
        )

    result = await db.execute(
        select(User).where(
            User.user_id == token_data.user_id,
            User.org_id == token_data.org_id,
            User.deleted_at.is_(None),
            User.is_active.is_(True),
        )
    )
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired refresh token",
        )

    access_token, access_expires = create_access_token(
        user_id=user.user_id,
        email=user.email,
        org_id=user.org_id,
        role=user.role,
    )

    logger.info(f"Token refreshed for user {user.user_id}")

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
async def get_current_user_info(
    current_user=Depends(get_current_user), db: AsyncSession = Depends(get_db)
) -> CurrentUserResponse:
    """
    Get current authenticated user info.

    **T-106: Get current user endpoint**
    """
    result = await db.execute(
        select(User).where(
            User.user_id == current_user.user_id,
            User.org_id == current_user.org_id,
            User.deleted_at.is_(None),
        )
    )
    user = result.scalar_one_or_none()

    org_result = await db.execute(
        select(Organization).where(Organization.org_id == current_user.org_id)
    )
    org = org_result.scalar_one_or_none()

    if not user or not org:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    first_name, last_name = _split_name(user.full_name)

    return CurrentUserResponse(
        user_id=user.user_id,
        email=user.email,
        first_name=first_name,
        last_name=last_name,
        org_id=user.org_id,
        org_name=org.name,
        role=user.role,
        mfa_enabled=False,
        created_at=user.created_at,
        last_login=user.last_login,
    )


@router.post(
    "/password-reset",
    status_code=status.HTTP_200_OK,
    summary="Request password reset",
    response_model=dict,
)
async def request_password_reset(
    request: PasswordResetRequest, db: AsyncSession = Depends(get_db)
) -> dict:
    """
    Request password reset (sends email with token).

    **T-110: Password reset flow**

    Phase 1/2: no email provider is configured in this repo -- logs the
    token instead of sending it (ponytail: wire to SendGrid/SES per
    PHASE_2_PROMPT.md's T-2019 once that integration exists).
    """
    logger.info(f"Password reset requested for {request.email}")

    candidates = await _find_candidate_users_by_email(db, request.email)
    # Reset doesn't verify a password, so there's no "which one matched"
    # signal to disambiguate a same-email-different-org collision -- take
    # the oldest account, consistent with pre-login behavior for this
    # lower-stakes path (the response is identical either way, so this
    # doesn't leak which org actually got the token).
    user = min(candidates, key=lambda u: u.created_at, default=None)

    # Always return success (don't leak whether email exists)
    if not user:
        return {"message": "If email exists, password reset link sent"}

    reset_expires = datetime.utcnow() + timedelta(hours=1)

    from jose import jwt

    from app.config import settings

    # Built as a plain dict, not ResetTokenData(...).model_dump(): jose's
    # jwt.encode json-dumps the payload, and neither of model_dump()'s modes
    # fit both fields at once -- mode="python" leaves user_id as a UUID
    # object (json.dumps can't serialize that), mode="json" turns exp/iat
    # into ISO strings (jwt.encode needs datetime/int for those). Same
    # str-the-UUID-but-not-the-timestamps shape as create_access_token().
    reset_token = jwt.encode(
        {
            "user_id": str(user.user_id),
            "email": user.email,
            "exp": reset_expires,
            "iat": datetime.utcnow(),
            "type": "reset",
        },
        settings.jwt_secret_key,
        algorithm=settings.jwt_algorithm,
    )

    # ponytail: no email provider configured -- log only, see docstring.
    logger.info(f"Reset token generated: {reset_token[:20]}...")

    return {"message": "If email exists, password reset link sent"}


@router.post(
    "/password-reset/confirm",
    status_code=status.HTTP_200_OK,
    summary="Confirm password reset",
    response_model=dict,
)
async def confirm_password_reset(
    request: PasswordResetConfirm, db: AsyncSession = Depends(get_db)
) -> dict:
    """
    Confirm password reset with new password.

    **T-110: Password reset confirmation**
    """
    token_data = verify_token(request.token, token_type="reset", model=ResetTokenData)

    if not token_data:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid or expired reset token",
        )

    result = await db.execute(
        select(User).where(
            User.user_id == token_data.user_id,
            User.deleted_at.is_(None),
        )
    )
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    user.password_hash = hash_password(request.new_password)
    await db.commit()
    logger.info(f"Password reset for user {user.user_id}")

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
    db: AsyncSession = Depends(get_db),
) -> dict:
    """
    Change password for authenticated user.

    **T-110: Change password endpoint**
    """
    result = await db.execute(
        select(User).where(
            User.user_id == current_user.user_id,
            User.org_id == current_user.org_id,
            User.deleted_at.is_(None),
        )
    )
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    if not user.password_hash or not verify_password(
        request.current_password, user.password_hash
    ):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Current password is incorrect",
        )

    user.password_hash = hash_password(request.new_password)
    await db.commit()
    logger.info(f"Password changed for user {current_user.user_id}")

    return {"message": "Password successfully changed"}
