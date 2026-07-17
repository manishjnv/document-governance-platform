"""Approval history audit endpoint (T-2070)."""

from __future__ import annotations

import uuid
from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.approval import Approval


async def get_approval_history(
    db: AsyncSession,
    *,
    org_id: uuid.UUID,
    review_id: uuid.UUID,
) -> list[dict]:
    """Fetch approval history for a review in audit format.

    Returns all Approval rows for a review, ordered by created_at (oldest first),
    in a dict format suitable for audit/history display.

    Note: This may substantially overlap with the Wave 1 endpoint
    GET /api/v1/reviews/{review_id}/approvals (see app/routers/approvals.py).
    The value-add here is the dedicated audit-style endpoint and ordered output.

    Args:
        db: Database session.
        org_id: Organization ID (for scoping).
        review_id: Review ID to fetch history for.

    Returns:
        List of dicts, each with approval_id, approver_id, status, notes, created_at, updated_at.
    """
    result = await db.execute(
        select(Approval)
        .where(Approval.org_id == org_id, Approval.review_id == review_id)
        .order_by(Approval.created_at)
    )
    approvals = result.scalars().all()

    return [
        {
            "approval_id": str(a.approval_id),
            "approver_id": str(a.approver_id),
            "status": a.status,
            "notes": a.notes,
            "created_at": a.created_at.isoformat(),
            "updated_at": a.updated_at.isoformat(),
        }
        for a in approvals
    ]
