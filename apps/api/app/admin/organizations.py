"""Org settings + branding admin operations.

T-2081: Org settings backend
T-2082: Org branding (logo_url, brand_primary_color, brand_secondary_color)
"""

from __future__ import annotations

import uuid
from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.organization import Organization


async def get_organization(db: AsyncSession, org_id: uuid.UUID) -> Optional[Organization]:
    """Fetch an org's own settings row. None if not found or soft-deleted."""
    result = await db.execute(
        select(Organization).where(
            (Organization.org_id == org_id) & (Organization.deleted_at.is_(None))
        )
    )
    return result.scalar_one_or_none()


async def update_organization(
    db: AsyncSession, org_id: uuid.UUID, **fields
) -> Optional[Organization]:
    """Patch name/branding fields on an org. None if not found.

    Caller is expected to pass only fields the client actually sent
    (e.g. via Pydantic's `exclude_unset=True`) — a value of None here
    means "clear this field", not "leave unchanged".
    """
    org = await get_organization(db, org_id)
    if org is None:
        return None

    for key, value in fields.items():
        setattr(org, key, value)

    await db.commit()
    await db.refresh(org)
    return org
