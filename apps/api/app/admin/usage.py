"""Organization usage metrics and analytics.

T-2084: Organization usage metrics
T-2099: Usage analytics (same underlying metrics)
"""

from __future__ import annotations

import uuid
from datetime import datetime, timedelta

from sqlalchemy import and_, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.document import Document
from app.models.finding import Finding
from app.models.review import Review


async def get_org_usage_metrics(
    db: AsyncSession, org_id: uuid.UUID, months: int = 1
) -> dict:
    """Get org usage metrics for the past N months.

    Returns dict with:
        documents_uploaded: int — count of documents uploaded in window
        reviews_run: int — count of reviews completed in window
        findings_by_severity: dict[str, int] — {critical, major, medium, low, info}
        total_storage_bytes: int — sum of all org docs' file_size_bytes (not time-windowed)
        window_start: datetime — start of the reporting window
        window_end: datetime — end (now)
    """
    now = datetime.utcnow()
    window_start = now - timedelta(days=30 * months)

    # Document uploads in window (not soft-deleted)
    doc_count_result = await db.execute(
        select(func.count()).select_from(Document).where(
            and_(
                Document.org_id == org_id,
                Document.created_at >= window_start,
                Document.deleted_at.is_(None),
            )
        )
    )
    documents_uploaded = doc_count_result.scalar_one()

    # Reviews completed in window (not soft-deleted)
    review_count_result = await db.execute(
        select(func.count()).select_from(Review).where(
            and_(
                Review.org_id == org_id,
                Review.completed_at >= window_start,
                Review.deleted_at.is_(None),
            )
        )
    )
    reviews_run = review_count_result.scalar_one()

    # Findings by severity in window (not soft-deleted)
    findings_result = await db.execute(
        select(Finding.severity, func.count()).select_from(Finding).where(
            and_(
                Finding.org_id == org_id,
                Finding.created_at >= window_start,
                Finding.deleted_at.is_(None),
            )
        )
        .group_by(Finding.severity)
    )
    findings_rows = findings_result.all()
    findings_by_severity = {
        "critical": 0,
        "major": 0,
        "medium": 0,
        "low": 0,
        "info": 0,
    }
    for severity, count in findings_rows:
        if severity in findings_by_severity:
            findings_by_severity[severity] = count

    # Total storage (all documents, not time-windowed)
    storage_result = await db.execute(
        select(func.sum(Document.file_size_bytes)).where(
            and_(
                Document.org_id == org_id,
                Document.deleted_at.is_(None),
            )
        )
    )
    total_storage_bytes = storage_result.scalar_one() or 0

    return {
        "documents_uploaded": int(documents_uploaded),
        "reviews_run": int(reviews_run),
        "findings_by_severity": findings_by_severity,
        "total_storage_bytes": int(total_storage_bytes),
        "window_start": window_start.isoformat(),
        "window_end": now.isoformat(),
    }
