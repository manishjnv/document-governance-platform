"""Notification API endpoints (T-2076 data model, T-2080 preferences).

T-2076 note: WebSocket real-time push is out of scope (no WS server infra in
this repo) — this is the REST-pollable notification store; wire Socket.io/
starlette websockets here if that lands later.
"""

import logging
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.collab.notifications import (
    create_notification,
    get_preferences,
    list_notifications,
    mark_all_read,
    mark_read,
    upsert_preferences,
)
from app.db.session import get_db
from app.dependencies import get_current_user
from app.schemas.auth import TokenData
from app.schemas.notification import (
    NotificationPreferenceRead,
    NotificationPreferenceUpdate,
    NotificationRead,
)

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/v1/notifications", tags=["notifications"])


@router.get(
    "",
    response_model=list[NotificationRead],
    summary="List notifications for current user",
)
async def list_user_notifications(
    unread_only: bool = False,
    skip: int = 0,
    limit: int = 50,
    current_user: TokenData = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """List notifications for the current user, filtered by read status."""
    org_id = UUID(str(current_user.org_id))
    user_id = UUID(str(current_user.user_id))

    notifications = await list_notifications(
        db,
        org_id=org_id,
        user_id=user_id,
        unread_only=unread_only,
        skip=skip,
        limit=limit,
    )
    return [NotificationRead.model_validate(n) for n in notifications]


@router.patch(
    "/{notif_id}/read",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Mark a notification as read",
)
async def mark_notification_read(
    notif_id: UUID,
    current_user: TokenData = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Mark a single notification as read."""
    org_id = UUID(str(current_user.org_id))
    user_id = UUID(str(current_user.user_id))

    await mark_read(
        db,
        org_id=org_id,
        notif_id=notif_id,
        user_id=user_id,
    )


@router.post(
    "/mark-all-read",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Mark all notifications as read",
)
async def mark_all_notifications_read(
    current_user: TokenData = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Mark all unread notifications as read for the current user."""
    org_id = UUID(str(current_user.org_id))
    user_id = UUID(str(current_user.user_id))

    await mark_all_read(
        db,
        org_id=org_id,
        user_id=user_id,
    )


@router.get(
    "/preferences",
    response_model=NotificationPreferenceRead,
    summary="Get notification preferences for current user",
)
async def get_user_preferences(
    current_user: TokenData = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Fetch notification preferences for the current user."""
    user_id = UUID(str(current_user.user_id))

    prefs = await get_preferences(db, user_id=user_id)
    if prefs is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Preferences not found")

    return NotificationPreferenceRead.model_validate(prefs)


@router.patch(
    "/preferences",
    response_model=NotificationPreferenceRead,
    summary="Update notification preferences for current user",
)
async def update_user_preferences(
    body: NotificationPreferenceUpdate,
    current_user: TokenData = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Update notification preferences. All fields are optional."""
    org_id = UUID(str(current_user.org_id))
    user_id = UUID(str(current_user.user_id))

    # Build dict of only non-None fields to update
    update_fields = {k: v for k, v in body.model_dump().items() if v is not None}

    prefs = await upsert_preferences(
        db,
        org_id=org_id,
        user_id=user_id,
        **update_fields,
    )

    return NotificationPreferenceRead.model_validate(prefs)
