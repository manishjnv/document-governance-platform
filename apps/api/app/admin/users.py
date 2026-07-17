"""User directory + role assignment admin operations.

T-2086: User directory + role assignment
"""

from __future__ import annotations

import uuid
from typing import Optional

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.enums import UserRole
from app.models.user import User

VALID_ROLES = {role.value for role in UserRole}


class LastAdminError(Exception):
    """Raised when a role change would leave the org with zero active admins."""


async def list_org_users(
    db: AsyncSession, org_id: uuid.UUID, skip: int = 0, limit: int = 50
) -> list[User]:
    """Paginated, active-only user directory for an org."""
    result = await db.execute(
        select(User)
        .where((User.org_id == org_id) & (User.deleted_at.is_(None)))
        .order_by(User.created_at.desc())
        .offset(skip)
        .limit(limit)
    )
    return list(result.scalars().all())


async def update_user_role(
    db: AsyncSession, org_id: uuid.UUID, user_id: uuid.UUID, new_role: str
) -> Optional[User]:
    """Change a user's role within their org.

    Raises:
        ValueError: new_role isn't admin/reviewer/viewer.
        LastAdminError: the target is the org's last active admin and
            new_role would demote them — the org would be locked out.

    Returns:
        The updated User, or None if no matching active user in this org.
    """
    if new_role not in VALID_ROLES:
        raise ValueError(f"Invalid role: {new_role!r}")

    result = await db.execute(
        select(User).where(
            (User.user_id == user_id)
            & (User.org_id == org_id)
            & (User.deleted_at.is_(None))
        )
    )
    user = result.scalar_one_or_none()
    if user is None:
        return None

    if user.role == UserRole.ADMIN.value and new_role != UserRole.ADMIN.value:
        count_result = await db.execute(
            select(func.count()).select_from(User).where(
                (User.org_id == org_id)
                & (User.role == UserRole.ADMIN.value)
                & (User.is_active.is_(True))
                & (User.deleted_at.is_(None))
            )
        )
        if count_result.scalar_one() <= 1:
            raise LastAdminError(
                "Cannot demote the organization's last remaining admin"
            )

    user.role = new_role
    await db.commit()
    await db.refresh(user)
    return user
