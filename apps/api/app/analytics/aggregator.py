"""Per-document view tracking and single-document analytics (T-2006)."""

import logging
from typing import Optional
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.document_view import DocumentView
from app.models.review import Review

logger = logging.getLogger(__name__)


async def record_document_view(
    db: AsyncSession, org_id: UUID, doc_id: UUID, user_id: Optional[UUID]
) -> None:
    """Stage one document_views row. Does NOT commit -- same pattern as
    app.compliance.audit.log_action, so the caller folds it into whatever
    transaction it's already running."""
    db.add(DocumentView(org_id=org_id, doc_id=doc_id, user_id=user_id))


async def get_document_analytics(db: AsyncSession, org_id: UUID, doc_id: UUID) -> dict:
    """View counts plus the document's latest review outcome, if any.

    Caller is responsible for verifying the document exists and belongs to
    org_id first (see app.routers.analytics.document_analytics) -- this
    function just aggregates and returns zeros/None for a doc with no rows.
    """
    view_count = await db.scalar(
        select(func.count())
        .select_from(DocumentView)
        .where(DocumentView.org_id == org_id, DocumentView.doc_id == doc_id)
    )
    unique_viewer_count = await db.scalar(
        select(func.count(func.distinct(DocumentView.user_id))).where(
            DocumentView.org_id == org_id,
            DocumentView.doc_id == doc_id,
            DocumentView.user_id.isnot(None),
        )
    )

    latest_review = await db.scalar(
        select(Review)
        .where(
            Review.org_id == org_id,
            Review.doc_id == doc_id,
            Review.deleted_at.is_(None),
        )
        .order_by(Review.created_at.desc())
        .limit(1)
    )

    return {
        "doc_id": str(doc_id),
        "view_count": view_count or 0,
        "unique_viewer_count": unique_viewer_count or 0,
        "latest_review_score": (
            float(latest_review.overall_score)
            if latest_review and latest_review.overall_score is not None
            else None
        ),
        "latest_review_status": latest_review.status if latest_review else None,
    }
