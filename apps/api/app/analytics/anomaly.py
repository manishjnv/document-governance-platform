"""Detect anomalies in review scores using statistical methods.

T-2034: Anomaly detection for risk/completeness scores
"""

import logging
import statistics
from typing import Optional
from uuid import UUID

from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.review import Review

logger = logging.getLogger(__name__)


async def detect_score_anomalies(
    db: AsyncSession, org_id: UUID, review_id: UUID
) -> dict:
    """
    Detect if a review's overall_score is an anomaly within the org's history.

    Compares the target review's overall_score against the org's historical
    mean/stdev of completed reviews (excluding the target review itself).
    Flags as anomaly if deviation is >2 standard deviations.

    Args:
        db: AsyncSession for database queries
        org_id: Organization UUID
        review_id: Target Review UUID

    Returns:
        {
            "review_id": str,
            "overall_score": float | None,
            "org_mean": float | None,
            "org_stdev": float | None,
            "is_anomaly": bool,
            "deviation": float | None,  # Number of standard deviations
        }
    """
    # Fetch the target review
    target_result = await db.execute(
        select(Review).where(
            and_(
                Review.review_id == review_id,
                Review.org_id == org_id,
                Review.deleted_at.is_(None),
            )
        )
    )
    target_review = target_result.scalar_one_or_none()

    if not target_review:
        return {
            "review_id": str(review_id),
            "overall_score": None,
            "org_mean": None,
            "org_stdev": None,
            "is_anomaly": False,
            "deviation": None,
        }

    target_score = target_review.overall_score
    if target_score is None:
        return {
            "review_id": str(review_id),
            "overall_score": None,
            "org_mean": None,
            "org_stdev": None,
            "is_anomaly": False,
            "deviation": None,
        }

    # Fetch all *completed* reviews for this org (excluding the target)
    historical_result = await db.execute(
        select(Review).where(
            and_(
                Review.org_id == org_id,
                Review.status == "completed",
                Review.review_id != review_id,
                Review.overall_score.isnot(None),
                Review.deleted_at.is_(None),
            )
        )
    )
    historical_reviews = historical_result.scalars().all()

    # Extract scores
    scores = [float(r.overall_score) for r in historical_reviews]

    # Guard for insufficient historical data
    if len(scores) < 2:
        logger.debug(
            f"Org {org_id}: only {len(scores)} historical reviews, "
            f"skipping anomaly check"
        )
        return {
            "review_id": str(review_id),
            "overall_score": float(target_score),
            "org_mean": None,
            "org_stdev": None,
            "is_anomaly": False,
            "deviation": None,
        }

    # Compute mean and stdev
    mean = statistics.mean(scores)
    stdev = statistics.stdev(scores)

    # Detect anomaly: >2 standard deviations from mean
    deviation = abs(float(target_score) - mean) / stdev if stdev > 0 else 0
    is_anomaly = deviation > 2.0

    logger.debug(
        f"Review {review_id}: score={target_score}, org_mean={mean:.2f}, "
        f"org_stdev={stdev:.2f}, deviation={deviation:.2f}, anomaly={is_anomaly}"
    )

    return {
        "review_id": str(review_id),
        "overall_score": float(target_score),
        "org_mean": round(mean, 2),
        "org_stdev": round(stdev, 2),
        "is_anomaly": is_anomaly,
        "deviation": round(deviation, 2),
    }
