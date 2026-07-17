"""Fine-grained per-resource access control (T-2056/T-2057/T-2058/T-2059).

grant_access/revoke_access reuse app.compliance.audit.log_action so every
grant/revoke lands in the existing audit_logs trail -- that's T-2059's
"who did what, when" half. The other half of T-2059 ("who currently has
access to this resource right now") is list_access_for_resource below;
*searching/filtering* the audit trail by resource_type/resource_id is
already served by the existing GET /api/v1/audit-logs endpoint
(app/routers/audit.py), so it isn't duplicated here.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.compliance.audit import log_action
from app.models.resource_grant import ResourceGrant


async def grant_access(
    db: AsyncSession,
    *,
    org_id: uuid.UUID,
    resource_type: str,
    resource_id: uuid.UUID,
    grantee_user_id: uuid.UUID,
    permission: str,
    granted_by_user_id: Optional[uuid.UUID],
    expires_at: Optional[datetime] = None,
) -> ResourceGrant:
    """Create a grant, audit-log it, and commit."""
    grant = ResourceGrant(
        org_id=org_id,
        resource_type=resource_type,
        resource_id=resource_id,
        grantee_user_id=grantee_user_id,
        permission=permission,
        granted_by_user_id=granted_by_user_id,
        expires_at=expires_at,
    )
    db.add(grant)
    await log_action(
        db,
        org_id=org_id,
        user_id=granted_by_user_id,
        action="access.granted",
        resource_type=resource_type,
        resource_id=resource_id,
        details={"grantee": str(grantee_user_id), "permission": permission},
    )
    await db.commit()
    await db.refresh(grant)
    return grant


async def check_access(
    db: AsyncSession,
    *,
    org_id: uuid.UUID,
    resource_type: str,
    resource_id: uuid.UUID,
    user_id: uuid.UUID,
    required_permission: str,
) -> bool:
    """True if a non-expired grant exists for this user/resource/permission."""
    now = datetime.now(timezone.utc)
    query = (
        select(ResourceGrant.grant_id)
        .where(
            ResourceGrant.org_id == org_id,
            ResourceGrant.resource_type == resource_type,
            ResourceGrant.resource_id == resource_id,
            ResourceGrant.grantee_user_id == user_id,
            ResourceGrant.permission == required_permission,
            (ResourceGrant.expires_at.is_(None)) | (ResourceGrant.expires_at > now),
        )
        .limit(1)
    )
    result = await db.execute(query)
    return result.first() is not None


async def revoke_access(
    db: AsyncSession,
    *,
    org_id: uuid.UUID,
    grant_id: uuid.UUID,
    revoked_by_user_id: Optional[uuid.UUID],
) -> None:
    """Hard-delete a grant and audit-log the revocation. No-op if not found
    (or not in the caller's org -- org isolation gate)."""
    result = await db.execute(
        select(ResourceGrant).where(
            ResourceGrant.org_id == org_id, ResourceGrant.grant_id == grant_id
        )
    )
    grant = result.scalar_one_or_none()
    if grant is None:
        return

    await log_action(
        db,
        org_id=org_id,
        user_id=revoked_by_user_id,
        action="access.revoked",
        resource_type=grant.resource_type,
        resource_id=grant.resource_id,
        details={"grantee": str(grant.grantee_user_id), "permission": grant.permission},
    )
    await db.delete(grant)
    await db.commit()


async def purge_expired_grants(db: AsyncSession, org_id: uuid.UUID) -> int:
    """Hard-delete grants past expires_at for org. Returns count deleted.

    ponytail: no scheduler wired up (no Celery worker runs in this repo
    yet); call this from a cron/beat task once one exists, same caveat as
    app.compliance.retention.purge_expired_audit_logs.
    """
    now = datetime.now(timezone.utc)
    result = await db.execute(
        delete(ResourceGrant).where(
            ResourceGrant.org_id == org_id,
            ResourceGrant.expires_at.is_not(None),
            ResourceGrant.expires_at <= now,
        )
    )
    await db.commit()
    return result.rowcount


async def list_access_for_resource(
    db: AsyncSession, *, org_id: uuid.UUID, resource_type: str, resource_id: uuid.UUID
) -> list[dict]:
    """Who currently has (non-expired) access to a resource, newest grant first."""
    now = datetime.now(timezone.utc)
    query = (
        select(ResourceGrant)
        .where(
            ResourceGrant.org_id == org_id,
            ResourceGrant.resource_type == resource_type,
            ResourceGrant.resource_id == resource_id,
            (ResourceGrant.expires_at.is_(None)) | (ResourceGrant.expires_at > now),
        )
        .order_by(ResourceGrant.created_at.desc())
    )
    result = await db.execute(query)
    return [
        {
            "grant_id": str(g.grant_id),
            "grantee_user_id": str(g.grantee_user_id),
            "permission": g.permission,
            "granted_by_user_id": str(g.granted_by_user_id) if g.granted_by_user_id else None,
            "expires_at": g.expires_at.isoformat() if g.expires_at else None,
            "created_at": g.created_at.isoformat(),
        }
        for g in result.scalars().all()
    ]
