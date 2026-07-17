"""Compliance and audit management API endpoints.

Implementation: T-2043 (audit retention), T-2045 (compliance export),
T-2049 (PII detection)
- Audit log retention policies (admin-only)
- Audit log export for compliance (admin-only)
- PII detection and masking utilities
"""

import logging
from datetime import datetime
from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import Response
from sqlalchemy.ext.asyncio import AsyncSession

from app.compliance.reports import export_audit_logs_csv
from app.compliance.retention import get_retention_days, set_retention_days
from app.db.session import get_db
from app.dependencies import get_current_user, require_role
from app.schemas.auth import TokenData

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/v1/compliance", tags=["compliance"])


@router.get(
    "/audit-export",
    status_code=status.HTTP_200_OK,
    summary="Export audit logs for compliance",
    responses={
        403: {"description": "Admin access required"},
        404: {"description": "Organization not found"},
    },
)
async def export_audit_logs(
    format: str = Query("csv", description="Export format (currently only 'csv')"),
    date_from: Optional[datetime] = Query(None, description="Start date (ISO 8601)"),
    date_to: Optional[datetime] = Query(None, description="End date (ISO 8601)"),
    current_user: TokenData = Depends(require_role("admin")),
    db: AsyncSession = Depends(get_db),
):
    """
    Export audit logs as CSV for compliance/audit purposes.

    **T-2045: Audit report generation**
    - Admin-only endpoint
    - Filters by organization
    - Supports date range filtering
    - Returns CSV with: log_id, created_at, user_id, action, resource_type,
      resource_id, details

    Query Parameters:
    - format: Export format (default: csv)
    - date_from: Optional start date (ISO 8601)
    - date_to: Optional end date (ISO 8601)
    """
    if format != "csv":
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Only 'csv' format is supported",
        )

    try:
        csv_content = await export_audit_logs_csv(
            db=db,
            org_id=current_user.org_id,
            date_from=date_from,
            date_to=date_to,
        )
    except ValueError as e:
        logger.error(f"Export failed for org {current_user.org_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to export audit logs",
        )

    filename = f"audit_logs_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
    return Response(
        content=csv_content,
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename={filename}"},
    )


@router.get(
    "/retention-policy",
    status_code=status.HTTP_200_OK,
    summary="Get audit retention policy",
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
    Get organization's audit log retention policy.

    **T-2043: Audit log retention policies**
    - Admin-only endpoint
    - Returns audit_retention_days (30, 90, or 365)
    """
    try:
        retention_days = await get_retention_days(db, current_user.org_id)
        return {
            "org_id": str(current_user.org_id),
            "audit_retention_days": retention_days,
        }
    except ValueError as e:
        logger.error(f"Failed to fetch retention policy for org {current_user.org_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Organization not found",
        )


@router.patch(
    "/retention-policy",
    status_code=status.HTTP_200_OK,
    summary="Update audit retention policy",
    responses={
        403: {"description": "Admin access required"},
        404: {"description": "Organization not found"},
        422: {"description": "Invalid retention days"},
    },
)
async def update_retention_policy(
    audit_retention_days: int = Query(
        ..., description="Retention days (30, 90, or 365)"
    ),
    current_user: TokenData = Depends(require_role("admin")),
    db: AsyncSession = Depends(get_db),
):
    """
    Update organization's audit log retention policy.

    **T-2043: Audit log retention policies**
    - Admin-only endpoint
    - Allowed values: 30, 90, 365 days
    - Updates audit_retention_days for org
    """
    if audit_retention_days not in (30, 90, 365):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Invalid retention days. Allowed: 30, 90, 365",
        )

    try:
        await set_retention_days(db, current_user.org_id, audit_retention_days)
        return {
            "org_id": str(current_user.org_id),
            "audit_retention_days": audit_retention_days,
            "message": "Retention policy updated successfully",
        }
    except ValueError as e:
        logger.error(f"Failed to update retention policy for org {current_user.org_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Organization not found",
        )
