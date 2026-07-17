"""Document/review data retention policy management.

T-2046: document/review data retention (auto-delete after N days)
- Soft-delete (deleted_at) Document rows past the org's retention window
- Separate from app/compliance/retention.py's audit_retention_days, which
  hard-deletes audit_logs rows and is scoped to a fixed 30/90/365 set.
  data_retention_days is an open positive-integer policy for documents.
"""

import logging
from datetime import datetime, timedelta
from uuid import UUID

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)


async def get_data_retention_days(db: AsyncSession, org_id: UUID) -> int:
    """
    Get org's document/review retention policy (in days).

    Args:
        db: Database session
        org_id: Organization ID

    Returns:
        Retention days (> 0)

    Raises:
        ValueError: If org not found
    """
    result = await db.execute(
        text("SELECT data_retention_days FROM organizations WHERE org_id = :org_id"),
        {"org_id": org_id},
    )
    row = result.first()

    if not row:
        raise ValueError(f"Organization {org_id} not found")

    return row[0]


async def set_data_retention_days(db: AsyncSession, org_id: UUID, days: int) -> None:
    """
    Set org's document/review retention policy.

    Args:
        db: Database session
        org_id: Organization ID
        days: Retention days (must be > 0)

    Raises:
        ValueError: If org not found or days <= 0
    """
    if days <= 0:
        raise ValueError(f"Invalid data retention days: {days}. Must be > 0.")

    result = await db.execute(
        text(
            """
            UPDATE organizations
            SET data_retention_days = :days, updated_at = clock_timestamp()
            WHERE org_id = :org_id
            """
        ),
        {"org_id": org_id, "days": days},
    )

    if result.rowcount == 0:
        raise ValueError(f"Organization {org_id} not found")

    logger.info(f"Updated data retention policy for org {org_id} to {days} days")
    await db.commit()


async def purge_expired_documents(db: AsyncSession, org_id: UUID) -> int:
    """
    Soft-delete (set deleted_at) Document rows for org older than the org's
    data_retention_days.

    # ponytail: no scheduler wired up (no Celery worker runs in this repo
    # yet); call this from a Celery beat task or cron once one exists.

    Args:
        db: Database session
        org_id: Organization ID

    Returns:
        Count of documents soft-deleted

    Raises:
        ValueError: If org not found
    """
    retention_days = await get_data_retention_days(db, org_id)
    cutoff_date = datetime.utcnow() - timedelta(days=retention_days)

    result = await db.execute(
        text(
            """
            UPDATE documents
            SET deleted_at = clock_timestamp()
            WHERE org_id = :org_id AND deleted_at IS NULL AND created_at < :cutoff_date
            """
        ),
        {"org_id": org_id, "cutoff_date": cutoff_date},
    )

    purged_count = result.rowcount
    if purged_count > 0:
        logger.info(
            f"Soft-deleted {purged_count} expired documents for org {org_id} "
            f"(retention: {retention_days} days)"
        )

    await db.commit()
    return purged_count
