"""Approval workflow API endpoints (T-2066)."""

import logging
from uuid import UUID

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.collab.approvals import (
    create_approval_request,
    decide_approval,
    list_approvals_for_review,
)
from app.db.session import get_db
from app.dependencies import get_current_user
from app.schemas.approval import ApprovalCreateRequest, ApprovalDecisionRequest, ApprovalRead
from app.schemas.auth import TokenData

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/v1/reviews", tags=["approvals"])


@router.post(
    "/{review_id}/approvals",
    response_model=list[ApprovalRead],
    status_code=status.HTTP_201_CREATED,
    summary="Request approval from a list of approvers",
)
async def request_approvals(
    review_id: UUID,
    body: ApprovalCreateRequest,
    current_user: TokenData = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    org_id = UUID(str(current_user.org_id))
    approvals = await create_approval_request(
        db, org_id=org_id, review_id=review_id, approver_ids=body.approver_ids
    )
    return [ApprovalRead.model_validate(a) for a in approvals]


@router.get(
    "/{review_id}/approvals",
    response_model=list[ApprovalRead],
    summary="List approvals for a review",
)
async def get_approvals(
    review_id: UUID,
    current_user: TokenData = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    org_id = UUID(str(current_user.org_id))
    approvals = await list_approvals_for_review(db, org_id=org_id, review_id=review_id)
    return [ApprovalRead.model_validate(a) for a in approvals]


@router.patch(
    "/{review_id}/approvals/{approval_id}",
    response_model=ApprovalRead,
    summary="Approve or reject (only the named approver may act)",
)
async def submit_decision(
    review_id: UUID,
    approval_id: UUID,
    body: ApprovalDecisionRequest,
    current_user: TokenData = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    org_id = UUID(str(current_user.org_id))
    approval = await decide_approval(
        db,
        org_id=org_id,
        review_id=review_id,
        approval_id=approval_id,
        approver_id=UUID(str(current_user.user_id)),
        approval_status=body.status,
        notes=body.notes,
    )
    return ApprovalRead.model_validate(approval)
