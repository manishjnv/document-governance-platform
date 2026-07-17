"""Audit log retention policy management.

T-2043: Audit log retention policies
- Hard-delete audit logs past retention window
- Support org-scoped retention policies (30/90/365 days)
"""

import logging
from datetime import datetime, timedelta
from uuid import UUID

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)


async def purge_expired_audit_logs(db: AsyncSession, org_id: UUID) -> int:
    """
    Hard-delete audit log rows for org older than retention window.

    Queries org's audit_retention_days via raw SQL (org model owned by
    parallel agent), calculates cutoff timestamp, and deletes rows.

    Args:
        db: Database session
        org_id: Organization ID

    Returns:
        Count of rows deleted

    Raises:
        ValueError: If org not found or invalid retention_days
    """
    # ponytail: no scheduler wired up (no Celery worker runs in this repo yet);
    # call this from a Celery beat task or cron once one exists.

    # Read org's retention_days via raw SQL
    result = await db.execute(
        text("SELECT audit_retention_days FROM organizations WHERE org_id = :org_id"),
        {"org_id": org_id},
    )
    row = result.first()

    if not row:
        raise ValueError(f"Organization {org_id} not found")

    retention_days = row[0]
    if retention_days not in (30, 90, 365):
        raise ValueError(f"Invalid retention_days: {retention_days}")

    cutoff_date = datetime.utcnow() - timedelta(days=retention_days)

    # Hard-delete expired audit logs
    delete_result = await db.execute(
        text(
            """
            DELETE FROM audit_logs
            WHERE org_id = :org_id AND created_at < :cutoff_date
            """
        ),
        {"org_id": org_id, "cutoff_date": cutoff_date},
    )

    deleted_count = delete_result.rowcount
    if deleted_count > 0:
        logger.info(
            f"Purged {deleted_count} audit logs for org {org_id} "
            f"(retention: {retention_days} days)"
        )

    await db.commit()
    return deleted_count


async def get_retention_days(db: AsyncSession, org_id: UUID) -> int:
    """
    Get org's audit retention policy (in days).

    Args:
        db: Database session
        org_id: Organization ID

    Returns:
        Retention days (30, 90, or 365)

    Raises:
        ValueError: If org not found
    """
    result = await db.execute(
        text("SELECT audit_retention_days FROM organizations WHERE org_id = :org_id"),
        {"org_id": org_id},
    )
    row = result.first()

    if not row:
        raise ValueError(f"Organization {org_id} not found")

    return row[0]


async def set_retention_days(db: AsyncSession, org_id: UUID, days: int) -> None:
    """
    Set org's audit retention policy.

    Args:
        db: Database session
        org_id: Organization ID
        days: Retention days (must be 30, 90, or 365)

    Raises:
        ValueError: If org not found or invalid days value
    """
    if days not in (30, 90, 365):
        raise ValueError(f"Invalid retention days: {days}. Must be 30, 90, or 365.")

    result = await db.execute(
        text(
            """
            UPDATE organizations
            SET audit_retention_days = :days, updated_at = clock_timestamp()
            WHERE org_id = :org_id
            """
        ),
        {"org_id": org_id, "days": days},
    )

    if result.rowcount == 0:
        raise ValueError(f"Organization {org_id} not found")

    logger.info(f"Updated retention policy for org {org_id} to {days} days")
    await db.commit()
