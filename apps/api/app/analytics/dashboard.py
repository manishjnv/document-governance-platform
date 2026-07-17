"""Review-metrics aggregation (T-2007) and org-wide performance dashboard (T-2008)."""

import logging
from datetime import datetime, timedelta, timezone
from typing import Optional
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.document import Document
from app.models.finding import Finding
from app.models.review import Review

logger = logging.getLogger(__name__)

_SEVERITIES = ("critical", "major", "medium", "low", "info")


async def get_review_metrics(
    db: AsyncSession,
    org_id: UUID,
    category: Optional[str] = None,
    months: int = 6,
) -> dict:
    """
    Average review scores by category, grouped by month.

    Same month-grouping-in-Python approach as
    app.analytics.trends.analyze_score_trends (real Postgres in tests, but
    grouping stays portable). Unlike that function, `months` actually bounds
    the query here via a created_at cutoff, rather than being accepted and
    unused.
    """
    cutoff = datetime.now(timezone.utc) - timedelta(days=30 * months)
    query = select(Review).where(
        Review.org_id == org_id,
        Review.status == "completed",
        Review.deleted_at.is_(None),
        Review.created_at >= cutoff,
    )
    result = await db.execute(query)
    reviews = result.scalars().all()

    monthly_data: dict[str, list[float]] = {}
    for review in reviews:
        score = getattr(review, f"score_{category}", None) if category else review.overall_score
        if score is None:
            continue
        month_key = review.created_at.strftime("%Y-%m")
        monthly_data.setdefault(month_key, []).append(float(score))

    points = [
        {
            "month": month,
            "avg_score": round(sum(scores) / len(scores), 2),
            "review_count": len(scores),
        }
        for month, scores in sorted(monthly_data.items())
    ]

    return {"category": category or "overall", "months": months, "points": points}


async def get_performance_dashboard(db: AsyncSession, org_id: UUID) -> dict:
    """T-2008: single aggregate payload -- total docs, total reviews, avg
    processing time, avg overall score, finding counts by severity."""
    return await _compute_dashboard_metrics(db, org_id)


async def _compute_dashboard_metrics(
    db: AsyncSession,
    org_id: UUID,
    date_from: Optional[datetime] = None,
    date_to: Optional[datetime] = None,
) -> dict:
    """Shared aggregate query behind get_performance_dashboard (T-2008,
    unfiltered) and reports.build_custom_report (T-2016, optional date
    window) -- one place for the five queries instead of duplicating them
    per caller."""
    doc_conditions = [Document.org_id == org_id, Document.deleted_at.is_(None)]
    review_conditions = [Review.org_id == org_id, Review.deleted_at.is_(None)]
    if date_from is not None:
        doc_conditions.append(Document.created_at >= date_from)
        review_conditions.append(Review.created_at >= date_from)
    if date_to is not None:
        doc_conditions.append(Document.created_at <= date_to)
        review_conditions.append(Review.created_at <= date_to)

    total_documents = await db.scalar(
        select(func.count()).select_from(Document).where(*doc_conditions)
    )
    total_reviews = await db.scalar(
        select(func.count()).select_from(Review).where(*review_conditions)
    )
    avg_processing_time = await db.scalar(
        select(func.avg(Review.processing_time_seconds)).where(
            *review_conditions, Review.processing_time_seconds.isnot(None)
        )
    )
    avg_overall_score = await db.scalar(
        select(func.avg(Review.overall_score)).where(
            *review_conditions, Review.overall_score.isnot(None)
        )
    )

    review_ids = select(Review.review_id).where(*review_conditions)
    severity_rows = await db.execute(
        select(Finding.severity, func.count())
        .where(
            Finding.org_id == org_id,
            Finding.deleted_at.is_(None),
            Finding.review_id.in_(review_ids),
        )
        .group_by(Finding.severity)
    )
    finding_counts = {severity: 0 for severity in _SEVERITIES}
    for severity, count in severity_rows.all():
        finding_counts[severity] = count

    return {
        "total_documents": total_documents or 0,
        "total_reviews": total_reviews or 0,
        "avg_processing_time_seconds": (
            round(float(avg_processing_time), 2) if avg_processing_time is not None else None
        ),
        "avg_overall_score": (
            round(float(avg_overall_score), 2) if avg_overall_score is not None else None
        ),
        "finding_counts_by_severity": finding_counts,
    }
