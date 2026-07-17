"""Org-level IP allowlist (T-2060, optional feature).

is_ip_allowed returns True whenever the org has zero allowlist rows -- an
org that never added an entry hasn't opted into IP restriction, so the
default is allow, not deny. CIDR matching uses stdlib `ipaddress`, nothing
hand-rolled.
"""

from __future__ import annotations

import ipaddress
import uuid
from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.ip_allowlist import IPAllowlistEntry


async def is_ip_allowed(db: AsyncSession, org_id: uuid.UUID, ip_address: str) -> bool:
    """True if org has no allowlist entries (feature off) or ip_address
    falls inside at least one of the org's CIDR ranges."""
    result = await db.execute(
        select(IPAllowlistEntry.cidr).where(IPAllowlistEntry.org_id == org_id)
    )
    cidrs = [row[0] for row in result.all()]
    if not cidrs:
        return True

    try:
        ip = ipaddress.ip_address(ip_address)
    except ValueError:
        return False

    for cidr in cidrs:
        try:
            if ip in ipaddress.ip_network(cidr, strict=False):
                return True
        except ValueError:
            continue  # malformed row shouldn't 500 the whole check
    return False


async def add_ip_entry(
    db: AsyncSession, org_id: uuid.UUID, cidr: str, description: Optional[str] = None
) -> IPAllowlistEntry:
    ipaddress.ip_network(cidr, strict=False)  # raises ValueError if malformed -- fail fast
    entry = IPAllowlistEntry(org_id=org_id, cidr=cidr, description=description)
    db.add(entry)
    await db.commit()
    await db.refresh(entry)
    return entry


async def list_ip_entries(db: AsyncSession, org_id: uuid.UUID) -> list[IPAllowlistEntry]:
    result = await db.execute(
        select(IPAllowlistEntry)
        .where(IPAllowlistEntry.org_id == org_id)
        .order_by(IPAllowlistEntry.created_at.desc())
    )
    return list(result.scalars().all())


async def remove_ip_entry(db: AsyncSession, org_id: uuid.UUID, entry_id: uuid.UUID) -> None:
    """No-op if not found (or not in the caller's org)."""
    result = await db.execute(
        select(IPAllowlistEntry).where(
            IPAllowlistEntry.org_id == org_id, IPAllowlistEntry.entry_id == entry_id
        )
    )
    entry = result.scalar_one_or_none()
    if entry is None:
        return
    await db.delete(entry)
    await db.commit()
