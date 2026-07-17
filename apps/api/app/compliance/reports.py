"""Compliance report generation and export.

T-2045: Audit report generation and compliance export
- Export audit logs as CSV for compliance/audit purposes
"""

import csv
import io
import json
import logging
from datetime import datetime
from typing import Optional
from uuid import UUID

from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.audit_log import AuditLog

logger = logging.getLogger(__name__)


async def export_audit_logs_csv(
    db: AsyncSession,
    org_id: UUID,
    date_from: Optional[datetime] = None,
    date_to: Optional[datetime] = None,
) -> str:
    """
    Export audit logs as CSV for compliance/audit purposes.

    Queries AuditLog rows for org within date range, formats as CSV.
    Uses stdlib csv module and StringIO for lightweight generation.

    Args:
        db: Database session
        org_id: Organization ID (filters org-scoped)
        date_from: Optional start date (inclusive)
        date_to: Optional end date (inclusive)

    Returns:
        CSV string with columns: log_id, created_at, user_id, action,
        resource_type, resource_id, details
    """
    # Build query filter
    filters = [AuditLog.org_id == org_id]

    if date_from:
        filters.append(AuditLog.created_at >= date_from)

    if date_to:
        filters.append(AuditLog.created_at <= date_to)

    # Query audit logs
    query = select(AuditLog).where(and_(*filters)).order_by(AuditLog.created_at.desc())
    result = await db.execute(query)
    rows = result.scalars().all()

    # Build CSV
    output = io.StringIO()
    writer = csv.DictWriter(
        output,
        fieldnames=[
            "log_id",
            "created_at",
            "user_id",
            "action",
            "resource_type",
            "resource_id",
            "details",
        ],
    )

    writer.writeheader()

    for row in rows:
        writer.writerow(
            {
                "log_id": row.log_id,
                "created_at": row.created_at.isoformat() if row.created_at else "",
                "user_id": str(row.user_id) if row.user_id else "",
                "action": row.action,
                "resource_type": row.resource_type,
                "resource_id": str(row.resource_id) if row.resource_id else "",
                "details": json.dumps(row.details) if row.details else "",
            }
        )

    csv_content = output.getvalue()
    logger.info(
        f"Exported {len(rows)} audit logs for org {org_id} "
        f"(from {date_from} to {date_to})"
    )

    return csv_content
