"""Custom report builder (T-2016), report templates (T-2018), and the
report archive / history (T-2020)."""

import logging
from datetime import datetime, timezone
from typing import Optional
from uuid import UUID

from sqlalchemy import desc, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.analytics.dashboard import _compute_dashboard_metrics, get_review_metrics
from app.models.audit_log import AuditLog
from app.models.report_archive import ReportArchive

logger = logging.getLogger(__name__)

# T-2018: template name -> ordered metric keys it includes. "executive" is
# high-level only; "detailed" is everything; "compliance" leans on
# audit/retention-relevant keys (findings + audit trail volume).
REPORT_TEMPLATES: dict[str, list[str]] = {
    "executive": ["total_documents", "total_reviews", "avg_overall_score", "score_trends"],
    "detailed": [
        "total_documents",
        "total_reviews",
        "avg_processing_time_seconds",
        "avg_overall_score",
        "finding_counts_by_severity",
        "score_trends",
        "audit_log_count",
    ],
    "compliance": ["total_documents", "finding_counts_by_severity", "audit_log_count"],
}

# Keys computed from the shared dashboard aggregate (app.analytics.dashboard).
_DASHBOARD_KEYS = {
    "total_documents",
    "total_reviews",
    "avg_processing_time_seconds",
    "avg_overall_score",
    "finding_counts_by_severity",
}
_ALL_METRIC_KEYS = _DASHBOARD_KEYS | {"score_trends", "audit_log_count"}


async def build_custom_report(
    db: AsyncSession,
    org_id: UUID,
    metrics: list[str],
    date_from: Optional[datetime] = None,
    date_to: Optional[datetime] = None,
) -> dict:
    """Assemble a report dict from the requested metric keys, pulling from
    app.analytics.aggregator/dashboard. Unknown keys are dropped (logged),
    not errored -- callers get back whatever of their request is valid.
    """
    requested = [m for m in metrics if m in _ALL_METRIC_KEYS]
    unknown = [m for m in metrics if m not in _ALL_METRIC_KEYS]
    if unknown:
        logger.warning("build_custom_report: ignoring unknown metric keys %s", unknown)

    report: dict = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "date_from": date_from.isoformat() if date_from else None,
        "date_to": date_to.isoformat() if date_to else None,
        "metrics": {},
    }

    if any(k in _DASHBOARD_KEYS for k in requested):
        dashboard = await _compute_dashboard_metrics(db, org_id, date_from=date_from, date_to=date_to)
        for key in requested:
            if key in _DASHBOARD_KEYS:
                report["metrics"][key] = dashboard[key]

    if "score_trends" in requested:
        # ponytail: get_review_metrics buckets by `months`, not an arbitrary
        # date_from/date_to window -- fine for now since no template needs
        # exact-range trend lines; add range support if one does.
        report["metrics"]["score_trends"] = await get_review_metrics(db, org_id)

    if "audit_log_count" in requested:
        conditions = [AuditLog.org_id == org_id]
        if date_from is not None:
            conditions.append(AuditLog.created_at >= date_from)
        if date_to is not None:
            conditions.append(AuditLog.created_at <= date_to)
        count = await db.scalar(select(func.count()).select_from(AuditLog).where(*conditions))
        report["metrics"]["audit_log_count"] = count or 0

    return report


async def save_report_to_archive(
    db: AsyncSession,
    org_id: UUID,
    user_id: Optional[UUID],
    report_type: str,
    format: str,
    content: str,
) -> UUID:
    """T-2020: persist a generated report. Commits (mirrors
    app.analytics.reports being the terminal write for this request, same
    as e.g. app.routers.search_history's create endpoints)."""
    archived = ReportArchive(
        org_id=org_id,
        generated_by_user_id=user_id,
        report_type=report_type,
        format=format,
        content=content,
    )
    db.add(archived)
    await db.commit()
    await db.refresh(archived)
    return archived.report_id


async def list_report_archive(
    db: AsyncSession, org_id: UUID, skip: int = 0, limit: int = 50
) -> list[dict]:
    """T-2020: newest-first page of this org's archived reports."""
    result = await db.execute(
        select(ReportArchive)
        .where(ReportArchive.org_id == org_id)
        .order_by(desc(ReportArchive.created_at))
        .offset(skip)
        .limit(limit)
    )
    return [_serialize_archive_row(row) for row in result.scalars().all()]


async def get_archived_report(db: AsyncSession, org_id: UUID, report_id: UUID) -> Optional[dict]:
    """T-2020: fetch one archived report, org-scoped."""
    result = await db.execute(
        select(ReportArchive).where(
            ReportArchive.report_id == report_id, ReportArchive.org_id == org_id
        )
    )
    row = result.scalar_one_or_none()
    return _serialize_archive_row(row) if row else None


def _serialize_archive_row(row: ReportArchive) -> dict:
    return {
        "report_id": str(row.report_id),
        "report_type": row.report_type,
        "format": row.format,
        "filters": row.filters,
        "content": row.content,
        "created_at": row.created_at.isoformat(),
    }
