"""Additional insights endpoints for recommendations, trends, and risk analysis."""

import logging
from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import and_, desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.analytics.trends import analyze_score_trends
from app.db.session import get_db
from app.dependencies import get_current_user
from app.insights.recommendations import generate_recommended_actions
from app.insights.risk_heuristic import predict_document_risk
from app.models.document import Document
from app.models.finding import Finding
from app.models.review import Review
from app.schemas.auth import TokenData

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1", tags=["insights-extra"])


@router.post("/documents/{doc_id}/insights/recommendations")
async def get_document_recommendations(
    doc_id: UUID,
    current_user: TokenData = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """
    Generate recommended actions for a document based on its latest review findings.

    Args:
        doc_id: Document UUID
        current_user: Current authenticated user
        db: Database session

    Returns:
        {"recommendations": ["action1", "action2", ...]}
    """
    # Verify document exists and belongs to user's org
    doc_query = select(Document).where(
        and_(
            Document.doc_id == doc_id,
            Document.org_id == current_user.org_id,
            Document.deleted_at.is_(None),
        )
    )
    doc_result = await db.execute(doc_query)
    document = doc_result.scalar_one_or_none()

    if not document:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Document not found",
        )

    # Get latest completed review for this document
    review_query = (
        select(Review)
        .where(
            and_(
                Review.doc_id == doc_id,
                Review.org_id == current_user.org_id,
                Review.status == "completed",
                Review.deleted_at.is_(None),
            )
        )
        .order_by(desc(Review.created_at))
        .limit(1)
    )
    review_result = await db.execute(review_query)
    review = review_result.scalar_one_or_none()

    if not review:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No completed review found for this document",
        )

    # Get findings for this review
    findings_query = select(Finding).where(
        and_(
            Finding.review_id == review.review_id,
            Finding.org_id == current_user.org_id,
            Finding.deleted_at.is_(None),
        )
    )
    findings_result = await db.execute(findings_query)
    findings = findings_result.scalars().all()

    # Convert findings to dicts for Claude
    findings_dicts = [
        {
            "severity": f.severity,
            "title": f.title,
            "description": f.description,
            "recommendation": f.recommendation,
        }
        for f in findings
    ]

    # Generate recommendations using Claude
    # Document text is available but we truncate in the function
    document_text = (document.parsed_text or "")[:1000] or "Document content unavailable"

    recommendations = await generate_recommended_actions(
        document_text=document_text,
        findings=findings_dicts,
    )

    return {"recommendations": recommendations}


@router.get("/analytics/trends")
async def get_score_trends(
    category: Optional[str] = None,
    months: int = 6,
    current_user: TokenData = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """
    Get review score trends for the current organization.

    Args:
        category: Optional category name (e.g., 'completeness', 'clarity')
        months: Number of months to analyze (default 6)
        current_user: Current authenticated user
        db: Database session

    Returns:
        {
            "points": [{"month": "2026-02", "avg_score": 71.2, "review_count": 4}, ...],
            "direction": "improving" | "worsening" | "flat"
        }
    """
    try:
        trends = await analyze_score_trends(
            db=db,
            org_id=current_user.org_id,
            category=category,
            months=months,
        )
        return trends
    except Exception as e:
        logger.error(f"Error analyzing trends: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error analyzing trends",
        )


@router.get("/documents/{doc_id}/insights/risk")
async def get_document_risk(
    doc_id: UUID,
    current_user: TokenData = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """
    Predict document risk based on latest review findings.

    Args:
        doc_id: Document UUID
        current_user: Current authenticated user
        db: Database session

    Returns:
        {
            "risk_score": 65.0,
            "risk_band": "high",
            "basis": "heuristic",
            "finding_count_by_severity": {"critical": 1, "major": 2}
        }
    """
    # Verify document exists and belongs to user's org
    doc_query = select(Document).where(
        and_(
            Document.doc_id == doc_id,
            Document.org_id == current_user.org_id,
            Document.deleted_at.is_(None),
        )
    )
    doc_result = await db.execute(doc_query)
    document = doc_result.scalar_one_or_none()

    if not document:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Document not found",
        )

    # Get latest completed review for this document
    review_query = (
        select(Review)
        .where(
            and_(
                Review.doc_id == doc_id,
                Review.org_id == current_user.org_id,
                Review.status == "completed",
                Review.deleted_at.is_(None),
            )
        )
        .order_by(desc(Review.created_at))
        .limit(1)
    )
    review_result = await db.execute(review_query)
    review = review_result.scalar_one_or_none()

    if not review:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No completed review found for this document",
        )

    # Get findings for this review
    findings_query = select(Finding).where(
        and_(
            Finding.review_id == review.review_id,
            Finding.org_id == current_user.org_id,
            Finding.deleted_at.is_(None),
        )
    )
    findings_result = await db.execute(findings_query)
    findings = findings_result.scalars().all()

    # Convert findings to dicts for risk prediction
    findings_dicts = [{"severity": f.severity} for f in findings]

    # Predict risk using deterministic heuristic
    risk = predict_document_risk(findings_dicts)

    return risk
