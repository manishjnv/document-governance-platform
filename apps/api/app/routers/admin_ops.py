"""Admin operations: usage metrics, user suspension, bulk import.

T-2084: Organization usage metrics
T-2085: Organization member management (endpoints)
T-2088: User suspension/deactivation
T-2090: Bulk user import via CSV
T-2099: Usage analytics (same data as T-2084)
"""

import logging
from uuid import UUID

from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile, status
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.admin.usage import get_org_usage_metrics
from app.admin.user_lifecycle import (
    LastActiveAdminError,
    bulk_import_users,
    reactivate_user,
    suspend_user,
)
from app.db.session import get_db
from app.dependencies import require_role
from app.schemas.auth import TokenData

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/v1/admin", tags=["admin-ops"])


class UsageMetricsResponse(BaseModel):
    """Usage metrics response."""

    documents_uploaded: int
    reviews_run: int
    findings_by_severity: dict[str, int]
    total_storage_bytes: int
    window_start: str
    window_end: str


class BulkImportResponse(BaseModel):
    """Bulk import response."""

    created: int
    skipped: list[dict]
    errors: list[dict]


@router.get(
    "/usage",
    response_model=UsageMetricsResponse,
    summary="Get organization usage metrics",
    status_code=status.HTTP_200_OK,
)
async def get_usage_metrics(
    months: int = Query(1, ge=1, le=12, description="Reporting window in months"),
    current_user: TokenData = Depends(require_role("admin")),
    db: AsyncSession = Depends(get_db),
):
    """T-2084/T-2099: Get org usage metrics for the past N months.

    Includes:
    - Documents uploaded
    - Reviews run
    - Findings by severity
    - Total storage used

    Requires: admin role
    """
    metrics = await get_org_usage_metrics(db, current_user.org_id, months=months)
    return metrics


@router.patch(
    "/users/{user_id}/suspend",
    summary="Suspend a user",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def suspend_user_endpoint(
    user_id: UUID,
    current_user: TokenData = Depends(require_role("admin")),
    db: AsyncSession = Depends(get_db),
):
    """T-2088: Suspend a user (set is_active = False).

    Refuses to suspend the last active admin.

    Requires: admin role
    """
    try:
        await suspend_user(db, current_user.org_id, user_id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )
    except LastActiveAdminError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )


@router.patch(
    "/users/{user_id}/reactivate",
    summary="Reactivate a user",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def reactivate_user_endpoint(
    user_id: UUID,
    current_user: TokenData = Depends(require_role("admin")),
    db: AsyncSession = Depends(get_db),
):
    """T-2088: Reactivate a user (set is_active = True).

    Requires: admin role
    """
    try:
        await reactivate_user(db, current_user.org_id, user_id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )


@router.post(
    "/users/bulk-import",
    response_model=BulkImportResponse,
    summary="Bulk import users from CSV",
    status_code=status.HTTP_200_OK,
)
async def bulk_import_users_endpoint(
    file: UploadFile = File(...),
    current_user: TokenData = Depends(require_role("admin")),
    db: AsyncSession = Depends(get_db),
):
    """T-2090: Bulk import users from CSV file.

    CSV format (with header):
        email,full_name,role

    Behavior:
    - Skips rows where email already exists in org (case-insensitive)
    - Creates users with random temporary password
    - Validates role is admin/reviewer/viewer
    - Returns summary of created, skipped, and errored rows

    Note: No email configured for temp password delivery; caller must communicate separately.

    Requires: admin role
    """
    try:
        csv_content = (await file.read()).decode("utf-8")
    except UnicodeDecodeError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="File must be valid UTF-8",
        )

    result = await bulk_import_users(db, current_user.org_id, csv_content)
    return result
