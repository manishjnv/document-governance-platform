"""Governance API endpoints.

T-2046: document/review data retention policy
T-2047: GDPR data export
T-2048: GDPR right-to-be-forgotten

Mounted in main.py (2026-07-18 router audit confirmed this). No router-level
test exists yet -- test_gdpr.py exercises the underlying service functions
(app.compliance.gdpr / data_retention) directly, not these HTTP endpoints.
"""

import logging
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.compliance.data_retention import get_data_retention_days, set_data_retention_days
from app.compliance.gdpr import delete_user_data, export_user_data
from app.db.session import get_db
from app.dependencies import get_current_user, require_role
from app.schemas.auth import TokenData

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/v1/governance", tags=["governance"])


@router.post(
    "/users/{user_id}/export",
    status_code=status.HTTP_200_OK,
    summary="GDPR data export for a user",
    responses={403: {"description": "Not authorized"}},
)
async def export_user(
    user_id: UUID,
    current_user: TokenData = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    T-2047: Export everything the org holds about a user (documents
    uploaded, reviews triggered, comments made, findings assigned).

    Self or admin only.
    """
    if current_user.user_id != user_id and current_user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to export this user's data",
        )

    return await export_user_data(db, current_user.org_id, user_id)


@router.delete(
    "/users/{user_id}",
    status_code=status.HTTP_200_OK,
    summary="GDPR right-to-be-forgotten for a user",
    responses={
        403: {"description": "Admin access required"},
        404: {"description": "User not found"},
    },
)
async def delete_user(
    user_id: UUID,
    current_user: TokenData = Depends(require_role("admin")),
    db: AsyncSession = Depends(get_db),
):
    """
    T-2048: Anonymize a user's personal data (redact email, deactivate,
    soft-delete). Documents/reviews/comments they created are NOT deleted.

    Admin-only.
    """
    try:
        return await delete_user_data(db, current_user.org_id, user_id)
    except ValueError as e:
        logger.error(f"GDPR delete failed for user {user_id} in org {current_user.org_id}: {e}")
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))


@router.get(
    "/retention-policy",
    status_code=status.HTTP_200_OK,
    summary="Get document/review retention policy",
    responses={
        403: {"description": "Admin access required"},
        404: {"description": "Organization not found"},
    },
)
async def get_retention_policy(
    current_user: TokenData = Depends(require_role("admin")),
    db: AsyncSession = Depends(get_db),
):
    """
    T-2046: Get org's document/review retention policy (in days).

    Separate from /api/v1/compliance/retention-policy, which governs audit
    logs specifically.
    """
    try:
        days = await get_data_retention_days(db, current_user.org_id)
    except ValueError:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Organization not found")

    return {"org_id": str(current_user.org_id), "data_retention_days": days}


@router.patch(
    "/retention-policy",
    status_code=status.HTTP_200_OK,
    summary="Update document/review retention policy",
    responses={
        403: {"description": "Admin access required"},
        404: {"description": "Organization not found"},
        422: {"description": "Invalid retention days"},
    },
)
async def update_retention_policy(
    data_retention_days: int = Query(..., gt=0, description="Retention days (must be > 0)"),
    current_user: TokenData = Depends(require_role("admin")),
    db: AsyncSession = Depends(get_db),
):
    """T-2046: Update org's document/review retention policy. Admin-only."""
    try:
        await set_data_retention_days(db, current_user.org_id, data_retention_days)
    except ValueError:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Organization not found")

    return {
        "org_id": str(current_user.org_id),
        "data_retention_days": data_retention_days,
        "message": "Retention policy updated successfully",
    }
