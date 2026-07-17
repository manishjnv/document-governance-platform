"""GDPR data export and right-to-be-forgotten (T-2047, T-2048).

export_user_data assembles everything the org holds about a user.
delete_user_data anonymizes the User row itself (right-to-be-forgotten is
about *their* personal data, not the org-owned documents/reviews/comments
they happened to create) -- those rows are left in place, still pointing at
the now-anonymized user_id, so the org's audit trail stays intact.
"""

from __future__ import annotations

import logging
import uuid
from datetime import datetime
from decimal import Decimal
from typing import Any

from sqlalchemy import func, select
from sqlalchemy import inspect as sa_inspect
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.document import Document
from app.models.finding import Finding
from app.models.review import Review
from app.models.user import User

try:
    from app.models.comment import Comment
except ImportError:  # pragma: no cover - defensive only, Wave 1 already landed Comment
    Comment = None  # type: ignore[assignment,misc]

logger = logging.getLogger(__name__)


def _row_to_dict(obj: Any) -> dict[str, Any]:
    """Serialize an ORM row to a plain JSON-safe dict (all mapped columns)."""
    out: dict[str, Any] = {}
    for col in sa_inspect(obj).mapper.column_attrs:
        val = getattr(obj, col.key)
        if isinstance(val, uuid.UUID):
            val = str(val)
        elif isinstance(val, datetime):
            val = val.isoformat()
        elif isinstance(val, Decimal):
            val = float(val)
        out[col.key] = val
    return out


async def export_user_data(db: AsyncSession, org_id: uuid.UUID, user_id: uuid.UUID) -> dict:
    """
    Export everything the org holds about a user: documents they uploaded,
    reviews they triggered, comments they made, findings assigned to them.

    Args:
        db: Database session
        org_id: Organization ID (scopes every query)
        user_id: User ID to export

    Returns:
        Plain JSON-serializable dict
    """
    doc_rows = await db.execute(
        select(Document).where(
            Document.org_id == org_id,
            Document.uploaded_by_user_id == user_id,
            Document.deleted_at.is_(None),
        )
    )
    review_rows = await db.execute(
        select(Review).where(
            Review.org_id == org_id,
            Review.triggered_by_user_id == user_id,
            Review.deleted_at.is_(None),
        )
    )
    finding_rows = await db.execute(
        select(Finding).where(
            Finding.org_id == org_id,
            Finding.assigned_to_user_id == user_id,
            Finding.deleted_at.is_(None),
        )
    )

    comments: list[dict[str, Any]] = []
    if Comment is not None:
        comment_rows = await db.execute(
            select(Comment).where(
                Comment.org_id == org_id,
                Comment.user_id == user_id,
                Comment.deleted_at.is_(None),
            )
        )
        comments = [_row_to_dict(c) for c in comment_rows.scalars().all()]

    return {
        "user_id": str(user_id),
        "org_id": str(org_id),
        "exported_at": datetime.utcnow().isoformat(),
        "documents": [_row_to_dict(d) for d in doc_rows.scalars().all()],
        "reviews": [_row_to_dict(r) for r in review_rows.scalars().all()],
        "findings": [_row_to_dict(f) for f in finding_rows.scalars().all()],
        "comments": comments,
    }


async def delete_user_data(db: AsyncSession, org_id: uuid.UUID, user_id: uuid.UUID) -> dict:
    """
    Right-to-be-forgotten: anonymize the User row (redact email, deactivate,
    soft-delete). Does NOT touch documents/reviews/comments the user created
    -- those are org-owned content, not the user's personal data, and stay
    attributed to the (now-anonymized) user_id for audit-trail continuity.

    Args:
        db: Database session
        org_id: Organization ID
        user_id: User ID to anonymize

    Returns:
        Summary dict of what was touched

    Raises:
        ValueError: If user not found in org
    """
    result = await db.execute(
        select(User).where(
            User.org_id == org_id, User.user_id == user_id, User.deleted_at.is_(None)
        )
    )
    user = result.scalar_one_or_none()
    if user is None:
        raise ValueError(f"User {user_id} not found in org {org_id}")

    redacted_email = f"redacted-{user_id}@deleted.invalid"
    user.email = redacted_email
    user.full_name = None
    user.is_active = False
    user.deleted_at = datetime.utcnow()

    doc_count = await db.scalar(
        select(func.count()).select_from(Document).where(
            Document.org_id == org_id,
            Document.uploaded_by_user_id == user_id,
            Document.deleted_at.is_(None),
        )
    )
    review_count = await db.scalar(
        select(func.count()).select_from(Review).where(
            Review.org_id == org_id,
            Review.triggered_by_user_id == user_id,
            Review.deleted_at.is_(None),
        )
    )
    comment_count = 0
    if Comment is not None:
        comment_count = await db.scalar(
            select(func.count()).select_from(Comment).where(
                Comment.org_id == org_id,
                Comment.user_id == user_id,
                Comment.deleted_at.is_(None),
            )
        )

    await db.commit()

    logger.info(f"Anonymized user {user_id} in org {org_id} (GDPR right-to-be-forgotten)")

    return {
        "user_id": str(user_id),
        "org_id": str(org_id),
        "anonymized": True,
        "redacted_email": redacted_email,
        "documents_retained": doc_count or 0,
        "reviews_retained": review_count or 0,
        "comments_retained": comment_count or 0,
    }
