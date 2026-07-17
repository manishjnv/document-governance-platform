"""Prediction endpoints: missing sections, anomalies, confidence intervals.

T-2030: Version comparison setup (contract definition)
T-2033: Missing sections via section_recommender
T-2034: Anomaly detection on scores
T-2035: Confidence intervals on risk predictions
"""

import logging
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import and_, desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.analytics.anomaly import detect_score_anomalies
from app.analytics.confidence import add_confidence_interval
from app.db.session import get_db
from app.dependencies import get_current_user
from app.insights.risk_heuristic import predict_document_risk
from app.insights.section_recommender import suggest_missing_sections
from app.models.document import Document
from app.models.finding import Finding
from app.models.review import Review
from app.schemas.auth import TokenData

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/predictions", tags=["predictions"])


async def _get_org_document(db: AsyncSession, doc_id: UUID, current_user: TokenData) -> Document:
    """Org-scoped document lookup."""
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


async def _get_org_review(db: AsyncSession, review_id: UUID, current_user: TokenData) -> Review:
    """Org-scoped review lookup."""
    result = await db.execute(
        select(Review).where(
            and_(
                Review.review_id == review_id,
                Review.org_id == current_user.org_id,
                Review.deleted_at.is_(None),
            )
        )
    )
    review = result.scalar_one_or_none()
    if not review:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Review not found")
    return review


@router.get("/documents/{doc_id}/missing-sections", summary="Suggest missing sections")
async def get_missing_sections(
    doc_id: UUID,
    current_user: TokenData = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Suggest sections missing from a document based on its type.

    Returns:
        {
            "doc_id": str,
            "document_type": str | None,
            "missing_sections": [str, ...]
        }
    """
    doc = await _get_org_document(db, doc_id, current_user)

    missing = suggest_missing_sections(doc.document_type or "", doc.parsed_sections or {})

    return {
        "doc_id": str(doc_id),
        "document_type": doc.document_type,
        "missing_sections": missing,
    }


@router.get("/reviews/{review_id}/anomaly", summary="Detect score anomalies")
async def get_anomaly_detection(
    review_id: UUID,
    current_user: TokenData = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Detect if a review's score is an anomaly in the org's history.

    Returns:
        {
            "review_id": str,
            "overall_score": float | None,
            "org_mean": float | None,
            "org_stdev": float | None,
            "is_anomaly": bool,
            "deviation": float | None
        }
    """
    # Verify the review exists and belongs to this org
    await _get_org_review(db, review_id, current_user)

    result = await detect_score_anomalies(db, current_user.org_id, review_id)
    return result


@router.get(
    "/documents/{doc_id}/risk-confidence", summary="Predict risk with confidence bounds"
)
async def get_risk_with_confidence(
    doc_id: UUID,
    current_user: TokenData = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Predict document risk and wrap with confidence bounds based on finding count.

    Returns:
        {
            "doc_id": str,
            "risk_prediction": {
                "risk_score": float,
                "risk_band": str,
                "basis": str,
                "finding_count_by_severity": {...}
            },
            "confidence_interval": {
                "risk_score": float,
                "lower_bound": float,
                "upper_bound": float,
                "confidence": str
            }
        }
    """
    doc = await _get_org_document(db, doc_id, current_user)

    # Load the latest completed review for this document
    review_result = await db.execute(
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
    latest_review = review_result.scalar_one_or_none()

    if not latest_review:
        # No completed review: return zero risk, low confidence
        return {
            "doc_id": str(doc_id),
            "risk_prediction": {
                "risk_score": 0.0,
                "risk_band": "low",
                "basis": "heuristic",
                "finding_count_by_severity": {},
            },
            "confidence_interval": {
                "risk_score": 0.0,
                "lower_bound": 0.0,
                "upper_bound": 0.0,
                "confidence": "low",
            },
        }

    # Load findings for this review
    findings_result = await db.execute(
        select(Finding).where(
            and_(
                Finding.review_id == latest_review.review_id,
                Finding.org_id == current_user.org_id,
                Finding.deleted_at.is_(None),
            )
        )
    )
    findings = findings_result.scalars().all()

    # Convert findings to dicts for predict_document_risk
    findings_dicts = [
        {"severity": finding.severity, "category": finding.category}
        for finding in findings
    ]

    # Predict risk
    risk_prediction = predict_document_risk(findings_dicts)

    # Add confidence interval based on finding count
    confidence = add_confidence_interval(
        risk_prediction["risk_score"], len(findings_dicts)
    )

    return {
        "doc_id": str(doc_id),
        "risk_prediction": risk_prediction,
        "confidence_interval": confidence,
    }
