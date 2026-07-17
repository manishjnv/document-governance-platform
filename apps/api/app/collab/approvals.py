"""Approval workflow service functions (T-2066)."""

from __future__ import annotations

import uuid

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.approval import Approval
from app.models.review import Review


async def create_approval_request(
    db: AsyncSession,
    *,
    org_id: uuid.UUID,
    review_id: uuid.UUID,
    approver_ids: list[uuid.UUID],
) -> list[Approval]:
    """Create one pending Approval row per approver for a review."""
    review = await db.get(Review, review_id)
    if review is None or review.deleted_at is not None or review.org_id != org_id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Review not found")

    approvals = [
        Approval(
            approval_id=uuid.uuid4(),
            org_id=org_id,
            review_id=review_id,
            approver_id=approver_id,
            status="pending",
        )
        for approver_id in approver_ids
    ]
    db.add_all(approvals)
    await db.commit()
    for approval in approvals:
        await db.refresh(approval)
    return approvals


async def list_approvals_for_review(
    db: AsyncSession, *, org_id: uuid.UUID, review_id: uuid.UUID
) -> list[Approval]:
    """List all approval rows (any status) for a review."""
    result = await db.execute(
        select(Approval).where(Approval.org_id == org_id, Approval.review_id == review_id)
    )
    return list(result.scalars().all())


async def decide_approval(
    db: AsyncSession,
    *,
    org_id: uuid.UUID,
    review_id: uuid.UUID,
    approval_id: uuid.UUID,
    approver_id: uuid.UUID,
    approval_status: str,
    notes: str | None,
) -> Approval:
    """Record an approver's decision. Only the named approver on this row may act."""
    result = await db.execute(
        select(Approval).where(
            Approval.approval_id == approval_id,
            Approval.org_id == org_id,
            Approval.review_id == review_id,
        )
    )
    approval = result.scalar_one_or_none()
    if approval is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Approval not found")

    if approval.approver_id != approver_id:
        raise HTTPException(
            status.HTTP_403_FORBIDDEN, "Only the named approver can decide this approval"
        )

    approval.status = approval_status
    approval.notes = notes
    await db.commit()
    await db.refresh(approval)
    return approval
