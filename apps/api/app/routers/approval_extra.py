"""Approval extras API endpoints — templates, history, mentions (T-2064, T-2067, T-2068, T-2069, T-2070)."""

import logging
from uuid import UUID

from fastapi import APIRouter, Depends, status
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.collab.approval_history import get_approval_history
from app.collab.approval_notify import notify_approvers
from app.collab.approval_templates import (
    apply_template,
    create_template,
    list_templates,
)
from app.db.session import get_db
from app.dependencies import get_current_user
from app.schemas.auth import TokenData

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/v1", tags=["approval-extra"])


# =====================================================================
# Schemas
# =====================================================================


class ApprovalTemplateCreate(BaseModel):
    """Create an approval template."""

    name: str = Field(..., min_length=1, max_length=255)
    approver_user_ids: list[UUID] = Field(..., min_length=1)
    mode: str = Field(default="parallel", pattern="^(parallel|serial)$")


class ApprovalTemplateRead(BaseModel):
    """Approval template response."""

    template_id: UUID
    org_id: UUID
    name: str
    approver_user_ids: list[UUID]
    mode: str


class ApplyTemplateRequest(BaseModel):
    """Apply a template to a review."""

    template_id: UUID


# =====================================================================
# Endpoints
# =====================================================================


@router.post(
    "/approval-templates",
    response_model=ApprovalTemplateRead,
    status_code=status.HTTP_201_CREATED,
    summary="Create an approval template",
)
async def create_approval_template(
    body: ApprovalTemplateCreate,
    current_user: TokenData = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    org_id = UUID(str(current_user.org_id))
    template = await create_template(
        db,
        org_id=org_id,
        name=body.name,
        approver_user_ids=body.approver_user_ids,
        mode=body.mode,
    )
    return ApprovalTemplateRead(
        template_id=template.template_id,
        org_id=template.org_id,
        name=template.name,
        approver_user_ids=template.approver_user_ids,
        mode=template.mode,
    )


@router.get(
    "/approval-templates",
    response_model=list[ApprovalTemplateRead],
    summary="List approval templates for org",
)
async def list_approval_templates(
    current_user: TokenData = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    org_id = UUID(str(current_user.org_id))
    templates = await list_templates(db, org_id=org_id)
    return [
        ApprovalTemplateRead(
            template_id=t.template_id,
            org_id=t.org_id,
            name=t.name,
            approver_user_ids=t.approver_user_ids,
            mode=t.mode,
        )
        for t in templates
    ]


@router.post(
    "/reviews/{review_id}/approval-templates/apply",
    status_code=status.HTTP_201_CREATED,
    summary="Apply an approval template to a review",
)
async def apply_approval_template(
    review_id: UUID,
    body: ApplyTemplateRequest,
    current_user: TokenData = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    org_id = UUID(str(current_user.org_id))
    approvals = await apply_template(
        db, org_id=org_id, template_id=body.template_id, review_id=review_id
    )
    # Trigger notifications for approvers (non-blocking; logs and continues on failure)
    approver_ids = [a.approver_id for a in approvals]
    await notify_approvers(db, org_id=org_id, review_id=review_id, approver_user_ids=approver_ids)

    return {
        "review_id": str(review_id),
        "approvals_created": len(approvals),
        "mode": approvals[0].status if approvals else None,  # Log for clarity
    }


@router.get(
    "/reviews/{review_id}/approval-history",
    summary="Get approval history for a review",
)
async def get_review_approval_history(
    review_id: UUID,
    current_user: TokenData = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    org_id = UUID(str(current_user.org_id))
    history = await get_approval_history(db, org_id=org_id, review_id=review_id)
    return {"review_id": str(review_id), "approvals": history}
