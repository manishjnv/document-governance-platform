"""Analyze review score trends over time."""

import logging
from datetime import datetime, timezone
from decimal import Decimal
from typing import Optional

from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.review import Review

logger = logging.getLogger(__name__)


async def analyze_score_trends(
    db: AsyncSession,
    org_id,
    category: Optional[str] = None,
    months: int = 6,
) -> dict:
    """
    Analyze score trends for an organization over the past N months.

    Args:
        db: AsyncSession for database queries
        org_id: Organization UUID
        category: Optional category (score_completeness, score_clarity, etc.)
                  If None, uses overall_score
        months: Number of months to look back (default 6)

    Returns:
        {
            "points": [
                {"month": "2026-02", "avg_score": 71.2, "review_count": 4},
                ...
            ],
            "direction": "improving" | "worsening" | "flat"
        }
    """
    # Query completed reviews for this org, excluding soft-deleted
    query = select(Review).where(
        and_(
            Review.org_id == org_id,
            Review.status == "completed",
            Review.deleted_at.is_(None),
            Review.overall_score.isnot(None),
        )
    )

    result = await db.execute(query)
    reviews = result.scalars().all()

    if not reviews:
        return {"points": [], "direction": "flat"}

    # Group by month in Python (SQLite doesn't have date_trunc)
    # Key: "2026-02", Value: list of scores
    monthly_data = {}

    for review in reviews:
        # Use created_at from TimestampMixin
        month_key = review.created_at.strftime("%Y-%m")

        if month_key not in monthly_data:
            monthly_data[month_key] = []

        # Get score based on category
        if category:
            # e.g., category="completeness" -> score_completeness
            score_attr = f"score_{category}"
            score = getattr(review, score_attr, None)
        else:
            score = review.overall_score

        if score is not None:
            monthly_data[month_key].append(float(score))

    # Sort by month and compute averages
    points = []
    for month in sorted(monthly_data.keys()):
        scores = monthly_data[month]
        if scores:
            avg_score = sum(scores) / len(scores)
            points.append(
                {
                    "month": month,
                    "avg_score": round(avg_score, 2),
                    "review_count": len(scores),
                }
            )

    # Determine trend direction
    direction = _determine_trend(points)

    return {"points": points, "direction": direction}


def _determine_trend(points: list[dict]) -> str:
    """
    Determine trend direction by comparing first-half vs second-half averages.

    Args:
        points: List of {"month": str, "avg_score": float, "review_count": int}

    Returns:
        "improving" | "worsening" | "flat"
    """
    if len(points) < 2:
        return "flat"

    # Split into two halves
    mid = len(points) // 2
    first_half = points[:mid]
    second_half = points[mid:]

    if not first_half or not second_half:
        return "flat"

    first_avg = sum(p["avg_score"] for p in first_half) / len(first_half)
    second_avg = sum(p["avg_score"] for p in second_half) / len(second_half)

    # ponytail: simple heuristic; could add confidence intervals or statistical test later
    diff = second_avg - first_avg
    if abs(diff) < 2.0:  # Within 2 points = flat
        return "flat"
    elif diff > 0:
        return "improving"
    else:
        return "worsening"
