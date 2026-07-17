"""Approval template service functions (T-2068, T-2067)."""

from __future__ import annotations

import uuid
import logging

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.approval import Approval
from app.models.approval_template import ApprovalTemplate
from app.models.review import Review

logger = logging.getLogger(__name__)


async def create_template(
    db: AsyncSession,
    *,
    org_id: uuid.UUID,
    name: str,
    approver_user_ids: list[uuid.UUID],
    mode: str = "parallel",
) -> ApprovalTemplate:
    """Create an approval template for reuse."""
    template = ApprovalTemplate(
        template_id=uuid.uuid4(),
        org_id=org_id,
        name=name,
        approver_user_ids=approver_user_ids,
        mode=mode,
    )
    db.add(template)
    await db.commit()
    await db.refresh(template)
    return template


async def list_templates(
    db: AsyncSession,
    *,
    org_id: uuid.UUID,
) -> list[ApprovalTemplate]:
    """List all approval templates for an organization."""
    result = await db.execute(
        select(ApprovalTemplate).where(ApprovalTemplate.org_id == org_id)
    )
    return list(result.scalars().all())


async def apply_template(
    db: AsyncSession,
    *,
    org_id: uuid.UUID,
    template_id: uuid.UUID,
    review_id: uuid.UUID,
) -> list[Approval]:
    """Apply a template to a review, creating Approval rows for each approver.

    Parallel mode: all approvers start as 'pending'.
    Serial mode: only the first approver's row is created as 'pending'; remaining
                 approvers are NOT created. This is a partial stub — advancing through
                 serial approvers requires a CHECK constraint change on approvals.status
                 to add an intermediate 'awaiting_turn' or similar, which is out of this
                 task's scope.

    # ponytail: serial mode only activates its first approver's row; wiring "advance to
    # next approver on decision" needs a CHECK constraint change on approvals.status this
    # task doesn't own — flag for whoever owns app/models/approval.py
    """
    # Fetch template
    template = await db.get(ApprovalTemplate, template_id)
    if template is None or template.org_id != org_id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Template not found")

    # Fetch review
    review = await db.get(Review, review_id)
    if review is None or review.deleted_at is not None or review.org_id != org_id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Review not found")

    approver_ids = template.approver_user_ids
    if not isinstance(approver_ids, list):
        # In case JSONB loaded as dict/other type, try to coerce
        if isinstance(approver_ids, dict):
            approver_ids = list(approver_ids.values()) if approver_ids else []
        else:
            approver_ids = []

    approvals = []

    if template.mode == "parallel":
        # All approvers start as pending
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

    elif template.mode == "serial":
        # Only create first approver's row; log intent for remainder
        if approver_ids:
            first_approver_id = approver_ids[0]
            approval = Approval(
                approval_id=uuid.uuid4(),
                org_id=org_id,
                review_id=review_id,
                approver_id=first_approver_id,
                status="pending",
            )
            db.add(approval)
            await db.commit()
            await db.refresh(approval)
            approvals.append(approval)

            if len(approver_ids) > 1:
                logger.info(
                    f"Serial template applied; remaining approvers {approver_ids[1:]} "
                    f"queued but not yet activated (awaiting first decision)"
                )

    return approvals
