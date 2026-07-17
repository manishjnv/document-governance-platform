"""Approval notification service (T-2069, in-app only)."""

from __future__ import annotations

import uuid
import logging

from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)


async def notify_approvers(
    db: AsyncSession,
    *,
    org_id: uuid.UUID,
    review_id: uuid.UUID,
    approver_user_ids: list[uuid.UUID],
) -> None:
    """Create in-app notifications for approvers on a review.

    Gracefully handles the case where the Notification model is not yet available
    (e.g., in a parallel work-in-progress scenario). Logs and continues rather
    than raising, so approval flow never breaks.

    Args:
        db: Database session.
        org_id: Organization ID.
        review_id: Review being approved.
        approver_user_ids: List of user IDs to notify.
    """
    try:
        from app.models.notification import Notification

        for user_id in approver_user_ids:
            notification = Notification(
                notif_id=uuid.uuid4(),
                org_id=org_id,
                user_id=user_id,
                type="approval_requested",
                content=f"You have a pending approval request for review {review_id}",
                read=False,
            )
            db.add(notification)

        await db.commit()
        logger.info(f"Created {len(approver_user_ids)} approval notifications for review {review_id}")

    except ImportError:
        logger.warning(
            "Notification model not yet available; skipping in-app notifications "
            "(approval workflow continues unaffected)"
        )
    except Exception as e:
        logger.error(f"Failed to create approval notifications: {e}", exc_info=True)
        # Never raise — approval workflow must not depend on notification availability
