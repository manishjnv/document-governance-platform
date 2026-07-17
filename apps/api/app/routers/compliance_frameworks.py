"""Compliance framework tracking API endpoints.

T-2051 (SOC2), T-2052 (ISO27001), T-2053 (GDPR), T-2054 (HIPAA),
T-2055 (compliance report generation)

DISCLAIMER: This module provides endpoints to track self-reported implementation
status of starter compliance-control checklists. It is NOT a certification, audit,
or legal guarantee of compliance. Use it for internal self-assessment only.
Admin-only endpoints.
"""

import logging
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import Response
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.compliance.frameworks import (
    generate_compliance_report,
    get_framework_status,
    list_controls,
    seed_framework_controls,
    update_control_status,
)
from app.db.session import get_db
from app.dependencies import get_current_user, require_role
from app.schemas.auth import TokenData

logger = logging.getLogger(__name__)
router = APIRouter(
    prefix="/api/v1/compliance/frameworks", tags=["compliance-frameworks"]
)


class UpdateControlRequest(BaseModel):
    """Request to update a control's status and evidence."""

    status: str = Field(
        ...,
        description="Status: not_started, in_progress, implemented, or verified",
    )
    evidence_notes: str | None = Field(
        None, description="Optional evidence or implementation notes"
    )


@router.post(
    "/{framework}/seed",
    status_code=status.HTTP_200_OK,
    summary="Seed starter compliance checklist",
)
async def seed_framework(
    framework: str,
    current_user: TokenData = Depends(require_role("admin")),
    db: AsyncSession = Depends(get_db),
):
    """
    Seed starter compliance checklist for a framework.

    Idempotent: calling twice doesn't duplicate controls.

    **Admin-only endpoint**

    Path Parameters:
    - framework: SOC2, ISO27001, GDPR, or HIPAA

    Returns:
        {count: int} — number of controls inserted (0 if already seeded)
    """
    if framework not in ("SOC2", "ISO27001", "GDPR", "HIPAA"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Framework must be SOC2, ISO27001, GDPR, or HIPAA",
        )

    try:
        count = await seed_framework_controls(db, current_user.org_id, framework)
        await db.commit()
        return {"count": count}
    except Exception as e:
        logger.error(f"Seed failed for org {current_user.org_id}, {framework}: {e}")
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to seed framework",
        )


@router.get(
    "/{framework}/status",
    status_code=status.HTTP_200_OK,
    summary="Get framework implementation status",
)
async def get_status(
    framework: str,
    current_user: TokenData = Depends(require_role("admin")),
    db: AsyncSession = Depends(get_db),
):
    """
    Get implementation status summary for a framework.

    **Admin-only endpoint**

    Path Parameters:
    - framework: SOC2, ISO27001, GDPR, or HIPAA

    Returns:
        {framework, total_controls, by_status, percent_implemented}
    """
    if framework not in ("SOC2", "ISO27001", "GDPR", "HIPAA"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Framework must be SOC2, ISO27001, GDPR, or HIPAA",
        )

    try:
        status_data = await get_framework_status(db, current_user.org_id, framework)
        return status_data
    except Exception as e:
        logger.error(
            f"Status fetch failed for org {current_user.org_id}, {framework}: {e}"
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to fetch framework status",
        )


@router.get(
    "/{framework}/controls",
    status_code=status.HTTP_200_OK,
    summary="List framework controls",
)
async def list_framework_controls(
    framework: str,
    current_user: TokenData = Depends(require_role("admin")),
    db: AsyncSession = Depends(get_db),
):
    """
    List all controls for a framework in the organization.

    **Admin-only endpoint**

    Path Parameters:
    - framework: SOC2, ISO27001, GDPR, or HIPAA

    Returns:
        List of controls with control_id, control_code, description, status,
        evidence_notes, last_reviewed_at
    """
    if framework not in ("SOC2", "ISO27001", "GDPR", "HIPAA"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Framework must be SOC2, ISO27001, GDPR, or HIPAA",
        )

    try:
        controls = await list_controls(db, current_user.org_id, framework)
        return {"controls": controls}
    except Exception as e:
        logger.error(
            f"List controls failed for org {current_user.org_id}, {framework}: {e}"
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to list controls",
        )


@router.patch(
    "/controls/{control_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Update control status",
)
async def update_control(
    control_id: UUID,
    body: UpdateControlRequest,
    current_user: TokenData = Depends(require_role("admin")),
    db: AsyncSession = Depends(get_db),
):
    """
    Update a control's implementation status and optional evidence notes.

    Sets last_reviewed_at to current time.

    **Admin-only endpoint**

    Path Parameters:
    - control_id: Control UUID

    Request Body:
    - status: not_started, in_progress, implemented, or verified
    - evidence_notes: Optional evidence or implementation notes
    """
    if body.status not in ("not_started", "in_progress", "implemented", "verified"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Status must be not_started, in_progress, implemented, or verified",
        )

    try:
        await update_control_status(
            db, current_user.org_id, control_id, body.status, body.evidence_notes
        )
        await db.commit()
        return None
    except ValueError as e:
        logger.warning(f"Control update failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        )
    except Exception as e:
        logger.error(f"Control update failed for org {current_user.org_id}: {e}")
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update control",
        )


@router.get(
    "/{framework}/report",
    status_code=status.HTTP_200_OK,
    summary="Generate compliance report CSV",
)
async def get_report(
    framework: str,
    current_user: TokenData = Depends(require_role("admin")),
    db: AsyncSession = Depends(get_db),
):
    """
    Generate CSV report of all controls and their implementation status.

    Includes a disclaimer that this is a self-assessment, not a certification.

    **Admin-only endpoint**

    Path Parameters:
    - framework: SOC2, ISO27001, GDPR, or HIPAA

    Returns:
        CSV file with columns: control_code, description, status, evidence_notes,
        last_reviewed_at
    """
    if framework not in ("SOC2", "ISO27001", "GDPR", "HIPAA"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Framework must be SOC2, ISO27001, GDPR, or HIPAA",
        )

    try:
        csv_content = await generate_compliance_report(
            db, current_user.org_id, framework
        )
        filename = f"compliance_report_{framework}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
        return Response(
            content=csv_content,
            media_type="text/csv",
            headers={"Content-Disposition": f"attachment; filename={filename}"},
        )
    except Exception as e:
        logger.error(
            f"Report generation failed for org {current_user.org_id}, {framework}: {e}"
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to generate report",
        )


from datetime import datetime  # noqa: E402 — import at end to avoid circular
