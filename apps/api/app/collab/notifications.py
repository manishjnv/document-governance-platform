"""Notification service functions (T-2076 data model, T-2080 preferences).

REST-pollable notification store + per-user delivery settings.
"""

from __future__ import annotations

import uuid
from typing import Optional

from fastapi import HTTPException, status
from sqlalchemy import and_, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.notification import Notification, NotificationPreference


async def create_notification(
    db: AsyncSession,
    *,
    org_id: uuid.UUID,
    user_id: uuid.UUID,
    type: str,
    content: str,
) -> Notification:
    """Create a notification for a user in an org."""
    notif = Notification(
        org_id=org_id,
        user_id=user_id,
        type=type,
        content=content,
    )
    db.add(notif)
    await db.commit()
    await db.refresh(notif)
    return notif


async def list_notifications(
    db: AsyncSession,
    *,
    org_id: uuid.UUID,
    user_id: uuid.UUID,
    unread_only: bool = False,
    skip: int = 0,
    limit: int = 50,
) -> list[Notification]:
    """List notifications for a user in an org.

    Ordered by created_at DESC (newest first). Scoped by org_id for multi-tenancy.
    """
    query = select(Notification).where(
        and_(
            Notification.org_id == org_id,
            Notification.user_id == user_id,
        )
    )
    if unread_only:
        query = query.where(Notification.read == False)  # noqa: E712

    query = query.order_by(Notification.created_at.desc()).offset(skip).limit(limit)
    result = await db.execute(query)
    return list(result.scalars().all())


async def mark_read(
    db: AsyncSession,
    *,
    org_id: uuid.UUID,
    notif_id: uuid.UUID,
    user_id: uuid.UUID,
) -> None:
    """Mark a single notification as read.

    Verify the notification belongs to the user + org before marking.
    """
    notif = await db.get(Notification, notif_id)
    if notif is None or notif.org_id != org_id or notif.user_id != user_id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Notification not found")

    notif.read = True
    await db.commit()


async def mark_all_read(
    db: AsyncSession,
    *,
    org_id: uuid.UUID,
    user_id: uuid.UUID,
) -> int:
    """Mark all unread notifications as read for a user in an org.

    Returns the count of notifications updated.
    """
    stmt = (
        update(Notification)
        .where(
            and_(
                Notification.org_id == org_id,
                Notification.user_id == user_id,
                Notification.read == False,  # noqa: E712
            )
        )
        .values(read=True)
    )
    result = await db.execute(stmt)
    await db.commit()
    return result.rowcount


async def get_preferences(
    db: AsyncSession,
    *,
    user_id: uuid.UUID,
) -> Optional[NotificationPreference]:
    """Fetch notification preferences for a user, or None if not set."""
    result = await db.execute(
        select(NotificationPreference).where(NotificationPreference.user_id == user_id)
    )
    return result.scalar_one_or_none()


async def upsert_preferences(
    db: AsyncSession,
    *,
    org_id: uuid.UUID,
    user_id: uuid.UUID,
    **fields,
) -> NotificationPreference:
    """Create or update notification preferences for a user.

    If no preference row exists, create one with soft defaults.
    If one exists, update the given fields.
    """
    prefs = await get_preferences(db, user_id=user_id)

    if prefs is None:
        # Create with defaults, then override with any provided fields
        prefs = NotificationPreference(
            org_id=org_id,
            user_id=user_id,
            email_enabled=fields.get("email_enabled", True),
            in_app_enabled=fields.get("in_app_enabled", True),
            digest_frequency=fields.get("digest_frequency", "daily"),
        )
        db.add(prefs)
    else:
        # Update given fields only
        for key, value in fields.items():
            if hasattr(prefs, key):
                setattr(prefs, key, value)

    await db.commit()
    await db.refresh(prefs)
    return prefs
