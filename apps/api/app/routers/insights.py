"""AI document insights API endpoints: summary, key risks, comparison.

T-2021: AI summary generation
T-2022: Key risks extraction
T-2024: Document comparison
"""

import logging
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import and_, desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.dependencies import get_current_user
from app.insights.ai_insights import compare_documents, extract_key_risks, generate_summary
from app.models.document import Document
from app.models.finding import Finding
from app.models.review import Review
from app.schemas.auth import TokenData

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/documents", tags=["insights"])
# Separate router: /api/v1/insights/compare doesn't live under /api/v1/documents,
# and an APIRouter only carries one prefix — kept in this same file per the task spec.
compare_router = APIRouter(prefix="/api/v1/insights", tags=["insights"])


async def _get_org_document(db: AsyncSession, doc_id: UUID, current_user: TokenData) -> Document:
    """Org-scoped document lookup, matching app/routers/insights_extra.py's
    convention (direct org_id filter in the WHERE clause). 404 covers both
    "doesn't exist" and "belongs to another org" — never leaks cross-org
    existence via a 403."""
    result = await db.execute(
        select(Document).where(
            and_(
                Document.doc_id == doc_id,
                Document.org_id == current_user.org_id,
                Document.deleted_at.is_(None),
            )
        )
    )
    doc = result.scalar_one_or_none()
    if not doc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Document not found")
    return doc


@router.post("/{doc_id}/insights/summary", summary="Generate AI executive summary")
async def get_document_summary(
    doc_id: UUID,
    current_user: TokenData = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Generate a 3-5 sentence executive summary for a document.

    # ponytail: computed on demand every call, no persistence/caching table —
    # add if this endpoint gets hit often enough to matter.
    """
    doc = await _get_org_document(db, doc_id, current_user)
    summary = await generate_summary(doc.parsed_text or "")
    return {"doc_id": str(doc_id), "summary": summary}


@router.post("/{doc_id}/insights/risks", summary="Extract top key risks via AI")
async def get_document_risks(
    doc_id: UUID,
    current_user: TokenData = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Extract the top 3 key risks for a document, informed by its latest
    review's findings plus the document text."""
    doc = await _get_org_document(db, doc_id, current_user)

    review_result = await db.execute(
        select(Review)
        .where(
            and_(
                Review.doc_id == doc_id,
                Review.org_id == current_user.org_id,
                Review.deleted_at.is_(None),
            )
        )
        .order_by(desc(Review.created_at))
        .limit(1)
    )
    latest_review = review_result.scalar_one_or_none()

    findings_dicts: list[dict] = []
    if latest_review:
        findings_result = await db.execute(
            select(Finding).where(
                and_(
                    Finding.review_id == latest_review.review_id,
                    Finding.org_id == current_user.org_id,
                    Finding.deleted_at.is_(None),
                )
            )
        )
        findings_dicts = [
            {
                "severity": f.severity,
                "category": f.category,
                "title": f.title,
                "description": f.description,
                "recommendation": f.recommendation,
            }
            for f in findings_result.scalars().all()
        ]

    risks = await extract_key_risks(doc.parsed_text or "", findings_dicts)
    return {"doc_id": str(doc_id), "risks": risks}


@compare_router.post("/compare", summary="Semantic comparison of two documents")
async def compare_two_documents(
    doc_id_a: UUID = Query(..., description="First document ID"),
    doc_id_b: UUID = Query(..., description="Second document ID"),
    current_user: TokenData = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Semantic (not line-diff) comparison of two documents. Both must
    belong to the caller's org — each lookup is independently org-scoped."""
    doc_a = await _get_org_document(db, doc_id_a, current_user)
    doc_b = await _get_org_document(db, doc_id_b, current_user)

    comparison = await compare_documents(doc_a.parsed_text or "", doc_b.parsed_text or "")
    return {"doc_id_a": str(doc_id_a), "doc_id_b": str(doc_id_b), **comparison}
