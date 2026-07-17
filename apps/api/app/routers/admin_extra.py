"""Admin extra endpoints for subscription and activity monitoring.

T-2083: Subscription tier display
T-2089: User activity monitoring
"""

import logging
from datetime import datetime, timedelta
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel
from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.dependencies import get_current_user, require_role
from app.models.audit_log import AuditLog
from app.models.organization import Organization
from app.models.user import User
from app.schemas.auth import TokenData
from app.schemas.audit_log import AuditLogRead

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/v1/admin", tags=["admin-extra"])


class SubscriptionTierResponse(BaseModel):
    """Response for subscription tier endpoint."""

    subscription_tier: str
    org_id: str


class ActivityListResponse(BaseModel):
    """Response for activity list endpoint."""

    logs: list[AuditLogRead]
    count: int


@router.get(
    "/subscription",
    response_model=SubscriptionTierResponse,
    status_code=status.HTTP_200_OK,
    summary="Get organization subscription tier",
    responses={
        401: {"description": "Unauthorized"},
        403: {"description": "Insufficient permissions"},
    },
)
async def get_subscription_tier(
    current_user: TokenData = Depends(require_role("admin")),
    db: AsyncSession = Depends(get_db),
):
    """
    Get the subscription tier for the current organization.

    Requires: admin role

    Returns:
        subscription_tier: free | pro | enterprise
        org_id: Organization ID
    """
    org_id = current_user.org_id

    # Query organization by org_id
    stmt = select(Organization).where(Organization.org_id == org_id)
    result = await db.execute(stmt)
    org = result.scalar_one_or_none()

    if not org:
        logger.warning(f"Organization {org_id} not found")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Organization not found",
        )

    return SubscriptionTierResponse(
        subscription_tier=org.subscription_tier,
        org_id=str(org.org_id),
    )


@router.get(
    "/users/{user_id}/activity",
    response_model=ActivityListResponse,
    status_code=status.HTTP_200_OK,
    summary="Get user activity logs",
    responses={
        401: {"description": "Unauthorized"},
        403: {"description": "Insufficient permissions"},
        404: {"description": "User not found or not in organization"},
    },
)
async def get_user_activity(
    user_id: UUID,
    days: int = Query(30, ge=1, le=365, description="Number of days to look back"),
    current_user: TokenData = Depends(require_role("admin")),
    db: AsyncSession = Depends(get_db),
):
    """
    Get activity logs for a specific user within an organization.

    Requires: admin role

    Args:
        user_id: User ID to retrieve activity for
        days: Number of days to look back (1-365, default 30)

    Returns:
        logs: List of audit log entries (newest first)
        count: Total number of entries

    Raises:
        404: If user doesn't exist or belongs to a different organization
    """
    org_id = current_user.org_id

    # Verify user exists and belongs to current org
    stmt = select(User).where(
        and_(
            User.user_id == user_id,
            User.org_id == org_id,
        )
    )
    result = await db.execute(stmt)
    user = result.scalar_one_or_none()

    if not user:
        logger.warning(
            f"User access denied: user {user_id} "
            f"(org {org_id}) - user not found or not in org"
        )
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )

    # Calculate the cutoff date
    cutoff_date = datetime.utcnow() - timedelta(days=days)

    # Query audit logs filtered by user_id, org_id, and time window
    stmt = (
        select(AuditLog)
        .where(
            and_(
                AuditLog.user_id == user_id,
                AuditLog.org_id == org_id,
                AuditLog.created_at >= cutoff_date,
            )
        )
        .order_by(AuditLog.created_at.desc())
    )
    result = await db.execute(stmt)
    logs = result.scalars().all()

    log_responses = [AuditLogRead.model_validate(log) for log in logs]

    return ActivityListResponse(
        logs=log_responses,
        count=len(log_responses),
    )
