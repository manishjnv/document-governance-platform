"""Tests for the approval workflow service functions (T-2066).

Acceptance test: only the assigned approver can decide their own approval
row — a different user attempting to decide someone else's approval gets a
403 (HTTPException raised by decide_approval, translated to a 403 response
by FastAPI at the router layer).
"""

import uuid

import pytest
from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.collab.approvals import create_approval_request, decide_approval, list_approvals_for_review
from app.models.organization import Organization
from app.models.review import Review
from app.models.user import User


async def _make_org_users_review(db_session: AsyncSession, *, n_approvers: int = 2):
    # org_id set explicitly: the model's default=uuid.uuid4 is a flush-time
    # default, so reading org.org_id before add()+commit() would be None.
    org = Organization(org_id=uuid.uuid4(), name=f"org-{uuid.uuid4()}")
    approvers = [
        User(user_id=uuid.uuid4(), org_id=org.org_id, email=f"approver{i}@example.com")
        for i in range(n_approvers)
    ]
    review = Review(review_id=uuid.uuid4(), org_id=org.org_id, doc_id=uuid.uuid4())
    db_session.add_all([org, review, *approvers])
    await db_session.commit()
    return org, approvers, review


@pytest.mark.asyncio
async def test_create_approval_request_one_row_per_approver(db_session: AsyncSession):
    org, approvers, review = await _make_org_users_review(db_session, n_approvers=3)
    approver_ids = [a.user_id for a in approvers]

    approvals = await create_approval_request(
        db_session, org_id=org.org_id, review_id=review.review_id, approver_ids=approver_ids
    )

    assert len(approvals) == 3
    assert {a.approver_id for a in approvals} == set(approver_ids)
    assert all(a.status == "pending" for a in approvals)

    listed = await list_approvals_for_review(db_session, org_id=org.org_id, review_id=review.review_id)
    assert len(listed) == 3


@pytest.mark.asyncio
async def test_only_named_approver_can_decide(db_session: AsyncSession):
    org, approvers, review = await _make_org_users_review(db_session, n_approvers=2)
    approver_a, approver_b = approvers

    approvals = await create_approval_request(
        db_session, org_id=org.org_id, review_id=review.review_id, approver_ids=[approver_a.user_id]
    )
    approval = approvals[0]

    # A different user (approver_b) attempting to decide approver_a's row gets 403.
    with pytest.raises(HTTPException) as exc_info:
        await decide_approval(
            db_session,
            org_id=org.org_id,
            review_id=review.review_id,
            approval_id=approval.approval_id,
            approver_id=approver_b.user_id,
            approval_status="approved",
            notes=None,
        )
    assert exc_info.value.status_code == 403

    # The named approver succeeds.
    decided = await decide_approval(
        db_session,
        org_id=org.org_id,
        review_id=review.review_id,
        approval_id=approval.approval_id,
        approver_id=approver_a.user_id,
        approval_status="approved",
        notes="looks good",
    )
    assert decided.status == "approved"
    assert decided.notes == "looks good"


@pytest.mark.asyncio
async def test_create_approval_request_missing_review_404(db_session: AsyncSession):
    org = Organization(org_id=uuid.uuid4(), name=f"org-{uuid.uuid4()}")
    user = User(user_id=uuid.uuid4(), org_id=org.org_id, email="approver@example.com")
    db_session.add_all([org, user])
    await db_session.commit()

    with pytest.raises(HTTPException) as exc_info:
        await create_approval_request(
            db_session, org_id=org.org_id, review_id=uuid.uuid4(), approver_ids=[user.user_id]
        )
    assert exc_info.value.status_code == 404


@pytest.mark.asyncio
async def test_decide_approval_rejected(db_session: AsyncSession):
    org, approvers, review = await _make_org_users_review(db_session, n_approvers=1)
    approver = approvers[0]

    approvals = await create_approval_request(
        db_session, org_id=org.org_id, review_id=review.review_id, approver_ids=[approver.user_id]
    )

    decided = await decide_approval(
        db_session,
        org_id=org.org_id,
        review_id=review.review_id,
        approval_id=approvals[0].approval_id,
        approver_id=approver.user_id,
        approval_status="rejected",
        notes="needs revision",
    )
    assert decided.status == "rejected"
    assert decided.notes == "needs revision"
