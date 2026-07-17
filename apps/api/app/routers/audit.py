"""T-2044: audit log search/filter API.

Read-only over the append-only audit_logs table (T-2042, already migrated).
Restricted to admin/reviewer -- audit trails carry IP/user-agent and
cross-user action history, which is more sensitive than the day-to-day
document/review data those two roles already see.
"""

from datetime import datetime
from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.dependencies import require_role
from app.models.audit_log import AuditLog
from app.schemas.auth import TokenData

router = APIRouter(prefix="/api/v1/audit-logs", tags=["audit"])


@router.get("", summary="Search audit logs")
async def search_audit_logs(
    user_id: Optional[UUID] = Query(None),
    action: Optional[str] = Query(None, description="Exact match, e.g. 'document.uploaded'"),
    resource_type: Optional[str] = Query(None),
    date_from: Optional[datetime] = Query(None),
    date_to: Optional[datetime] = Query(None),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=500),
    current_user: TokenData = Depends(require_role("admin", "reviewer")),
    db: AsyncSession = Depends(get_db),
):
    """List/search the caller's org audit trail, newest first."""
    query = select(AuditLog).where(AuditLog.org_id == current_user.org_id)

    if user_id is not None:
        query = query.where(AuditLog.user_id == user_id)
    if action is not None:
        query = query.where(AuditLog.action == action)
    if resource_type is not None:
        query = query.where(AuditLog.resource_type == resource_type)
    if date_from is not None:
        query = query.where(AuditLog.created_at >= date_from)
    if date_to is not None:
        query = query.where(AuditLog.created_at <= date_to)

    query = query.order_by(AuditLog.created_at.desc()).offset(skip).limit(limit)

    result = await db.execute(query)
    rows = result.scalars().all()

    return [
        {
            "log_id": row.log_id,
            "org_id": str(row.org_id),
            "user_id": str(row.user_id) if row.user_id else None,
            "action": row.action,
            "resource_type": row.resource_type,
            "resource_id": str(row.resource_id) if row.resource_id else None,
            "details": row.details,
            "ip_address": row.ip_address,
            "user_agent": row.user_agent,
            "created_at": row.created_at.isoformat(),
        }
        for row in rows
    ]
