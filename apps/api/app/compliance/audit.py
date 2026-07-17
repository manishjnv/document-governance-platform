"""T-2041: reusable audit-log write helper.

log_action() only builds the AuditLog row and db.add()s it -- it never
commits. Callers fold it into whatever transaction they're already running
(see app.routers.reviews.trigger_review, which builds several ORM objects
before a single final `await db.commit()`) so an audit entry lands atomically
with the action it records instead of needing its own round trip.
"""

from __future__ import annotations

from typing import Any, Optional

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.audit_log import AuditLog
from app.models.enums import AuditResourceType

_VALID_RESOURCE_TYPES = {t.value for t in AuditResourceType}


async def log_action(
    db: AsyncSession,
    *,
    org_id,
    user_id,
    action: str,
    resource_type: str,
    resource_id=None,
    details: Optional[dict[str, Any]] = None,
    ip_address: Optional[str] = None,
    user_agent: Optional[str] = None,
) -> None:
    """Stage an audit_logs row on `db`. Does NOT commit.

    Raises ValueError immediately if resource_type isn't one of
    AuditResourceType's values, so a typo fails fast in Python instead of
    surfacing as an opaque DB CHECK-constraint violation at commit time.
    """
    if resource_type not in _VALID_RESOURCE_TYPES:
        raise ValueError(
            f"Invalid resource_type {resource_type!r}. Must be one of: "
            f"{sorted(_VALID_RESOURCE_TYPES)}"
        )

    db.add(
        AuditLog(
            org_id=org_id,
            user_id=user_id,
            action=action,
            resource_type=resource_type,
            resource_id=resource_id,
            details=details or {},
            ip_address=ip_address,
            user_agent=user_agent,
        )
    )
