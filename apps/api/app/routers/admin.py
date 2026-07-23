"""Org settings, branding, and user-directory admin endpoints.

T-2081: Org settings backend
T-2082: Org branding
T-2086: User directory + role assignment
"""

import logging
from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.admin.organizations import get_organization, update_organization
from app.admin.users import LastAdminError, list_org_users, update_user_role
from app.db.session import get_db
from app.dependencies import require_role
from app.models.organization import Organization
from app.models.user import User
from app.schemas.auth import TokenData

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/v1/admin", tags=["admin"])

HEX_COLOR_PATTERN = r"^#[0-9A-Fa-f]{6}$"


class OrganizationSettingsUpdate(BaseModel):
    """PATCH /organization body. Only fields the client sends are updated."""

    name: Optional[str] = Field(None, min_length=1, max_length=255)
    logo_url: Optional[str] = Field(None, max_length=1024)
    brand_primary_color: Optional[str] = Field(None, pattern=HEX_COLOR_PATTERN)
    brand_secondary_color: Optional[str] = Field(None, pattern=HEX_COLOR_PATTERN)


class UserRoleUpdate(BaseModel):
    """PATCH /users/{user_id}/role body."""

    role: str = Field(..., pattern="^(admin|reviewer|viewer)$")


def _org_response(org: Organization) -> dict:
    return {
        "org_id": str(org.org_id),
        "name": org.name,
        "subscription_tier": org.subscription_tier,
        "logo_url": org.logo_url,
        "brand_primary_color": org.brand_primary_color,
        "brand_secondary_color": org.brand_secondary_color,
    }


def _user_response(user: User) -> dict:
    return {
        "user_id": str(user.user_id),
        "email": user.email,
        "full_name": user.full_name,
        "role": user.role,
        "is_active": user.is_active,
        "last_login": user.last_login.isoformat() if user.last_login else None,
    }


# ---------------------------------------------------------------------------
# Admin overview -- everything an admin wants at a glance, in plain words.
# ---------------------------------------------------------------------------

_ACTION_LABELS = {
    "user.login": "Signed in with password",
    "user.login.otp": "Signed in with an email code",
    "user.login.google": "Signed in with Google",
    "document.uploaded": "Uploaded a document",
    "review.completed": "Ran an AI review",
    "organization.created": "Created the workspace",
    "access.granted": "Was given access",
    "access.revoked": "Had access removed",
}

_LOGIN_ACTIONS = ("user.login", "user.login.otp", "user.login.google")

_LOGIN_METHOD = {
    "user.login": "Password",
    "user.login.otp": "Email code",
    "user.login.google": "Google",
}


def _humanize_action(action: str) -> str:
    return _ACTION_LABELS.get(action, action.replace(".", " ").replace("_", " ").capitalize())


def _device_from_ua(user_agent: Optional[str]) -> Optional[str]:
    """'Chrome on Windows'-style summary. Deliberately a keyword scan, not a
    UA-parser dependency -- good enough for an admin glance."""
    if not user_agent:
        return None
    ua = user_agent.lower()
    if "edg/" in ua or "edge" in ua:
        browser = "Edge"
    elif "firefox" in ua:
        browser = "Firefox"
    elif "chrome" in ua and "chromium" not in ua:
        browser = "Chrome"
    elif "safari" in ua:
        browser = "Safari"
    else:
        browser = "Browser"
    if "android" in ua:
        os_name = "Android"
    elif "iphone" in ua or "ipad" in ua or "ios" in ua:
        os_name = "iPhone/iPad"
    elif "mac os" in ua or "macintosh" in ua:
        os_name = "Mac"
    elif "windows" in ua:
        os_name = "Windows"
    elif "linux" in ua:
        os_name = "Linux"
    else:
        os_name = "Unknown device"
    mobile = " (mobile)" if ("mobile" in ua and "ipad" not in ua) else ""
    return f"{browser} on {os_name}{mobile}"


@router.get("/overview", summary="Admin overview: people, sign-ins, activity, AI usage")
async def get_admin_overview(
    current_user: TokenData = Depends(require_role("admin")),
    db: AsyncSession = Depends(get_db),
):
    """Everything an admin wants at a glance, read-only. Org-scoped for a
    normal workspace admin; platform-wide (every workspace) when the caller
    is in settings.platform_admin_emails -- each new email signup creates
    its own org, so the product owner needs the cross-org view."""
    from datetime import datetime, timedelta

    from sqlalchemy import func, select, true

    from app.config import settings
    from app.models.audit_log import AuditLog
    from app.models.document import Document
    from app.models.finding import Finding
    from app.models.review import Review

    org_id = UUID(str(current_user.org_id))
    platform_admins = {
        e.strip().lower() for e in settings.platform_admin_emails.split(",") if e.strip()
    }
    is_platform = (current_user.email or "").lower() in platform_admins

    # Per-model org conditions; true() (no filter) for the platform view.
    audit_in_scope = true() if is_platform else (AuditLog.org_id == org_id)
    doc_in_scope = true() if is_platform else (Document.org_id == org_id)
    review_in_scope = true() if is_platform else (Review.org_id == org_id)
    finding_in_scope = true() if is_platform else (Finding.org_id == org_id)

    now = datetime.utcnow()
    week_ago = now - timedelta(days=7)
    month_ago = now - timedelta(days=30)

    org_names: dict = {}
    if is_platform:
        users = (
            await db.execute(select(User).where(User.deleted_at.is_(None)).order_by(User.created_at))
        ).scalars().all()
        org_names = dict((await db.execute(select(Organization.org_id, Organization.name))).all())
    else:
        users = await list_org_users(db, org_id, 0, 1000)

    # Per-user document / review counts + last activity, in three grouped
    # queries instead of N per user.
    doc_counts = dict(
        (await db.execute(
            select(Document.uploaded_by_user_id, func.count())
            .where(doc_in_scope, Document.deleted_at.is_(None))
            .group_by(Document.uploaded_by_user_id)
        )).all()
    )
    review_counts = dict(
        (await db.execute(
            select(Review.triggered_by_user_id, func.count())
            .where(review_in_scope, Review.deleted_at.is_(None))
            .group_by(Review.triggered_by_user_id)
        )).all()
    )
    last_activity = dict(
        (await db.execute(
            select(AuditLog.user_id, func.max(AuditLog.created_at))
            .where(audit_in_scope)
            .group_by(AuditLog.user_id)
        )).all()
    )

    people = [
        {
            "name": u.full_name or u.email.split("@")[0],
            "email": u.email,
            "role": u.role,
            "active": u.is_active,
            "joined": u.created_at.isoformat() if u.created_at else None,
            "last_sign_in": u.last_login.isoformat() if u.last_login else None,
            "documents_uploaded": doc_counts.get(u.user_id, 0),
            "reviews_run": review_counts.get(u.user_id, 0),
            "last_activity": (
                last_activity[u.user_id].isoformat() if last_activity.get(u.user_id) else None
            ),
            # Workspace name -- only populated in the platform-wide view.
            "workspace": org_names.get(u.org_id),
        }
        for u in users
    ]
    names_by_id = {u.user_id: (u.full_name or u.email) for u in users}

    # Sign-ins (from the audit trail; device/IP captured at login as of
    # 2026-07-23 -- older rows have neither).
    signin_rows = (
        await db.execute(
            select(AuditLog)
            .where(audit_in_scope, AuditLog.action.in_(_LOGIN_ACTIONS))
            .order_by(AuditLog.created_at.desc())
            .limit(50)
        )
    ).scalars().all()
    signins_7d = (
        await db.execute(
            select(func.count()).where(
                audit_in_scope,
                AuditLog.action.in_(_LOGIN_ACTIONS),
                AuditLog.created_at >= week_ago,
            )
        )
    ).scalar() or 0
    signins_30d = (
        await db.execute(
            select(func.count()).where(
                audit_in_scope,
                AuditLog.action.in_(_LOGIN_ACTIONS),
                AuditLog.created_at >= month_ago,
            )
        )
    ).scalar() or 0

    # Recent activity feed (all actions, humanized).
    activity_rows = (
        await db.execute(
            select(AuditLog)
            .where(audit_in_scope)
            .order_by(AuditLog.created_at.desc())
            .limit(100)
        )
    ).scalars().all()

    # Documents + AI usage.
    docs_total = (
        await db.execute(
            select(func.count()).where(doc_in_scope, Document.deleted_at.is_(None))
        )
    ).scalar() or 0
    docs_7d = (
        await db.execute(
            select(func.count()).where(
                doc_in_scope,
                Document.deleted_at.is_(None),
                Document.created_at >= week_ago,
            )
        )
    ).scalar() or 0

    review_stats = (
        await db.execute(
            select(
                func.count(),
                func.count().filter(Review.status == "completed"),
                func.count().filter(Review.status == "failed"),
                func.count().filter(Review.created_at >= week_ago),
                func.avg(Review.processing_time_seconds),
                func.max(Review.completed_at),
            ).where(review_in_scope, Review.deleted_at.is_(None))
        )
    ).one()
    reviews_total, reviews_completed, reviews_failed, reviews_7d, avg_seconds, last_review_at = review_stats

    findings_total = (
        await db.execute(
            select(func.count()).where(finding_in_scope, Finding.deleted_at.is_(None))
        )
    ).scalar() or 0

    # AI models actually used -- from recent reviews' audit metadata.
    recent_meta = (
        await db.execute(
            select(Review.audit_meta)
            .where(review_in_scope, Review.audit_meta.isnot(None))
            .order_by(Review.completed_at.desc())
            .limit(20)
        )
    ).scalars().all()
    models_in_use = sorted(
        {m for meta in recent_meta for m in (meta.get("models_used") or {}).values() if m}
    )

    # Each completed review runs 6 specialist reviewers + 1 consistency
    # check = 7 AI calls (before any retries) -- an honest approximation.
    return {
        "generated_at": now.isoformat() + "Z",
        "totals": {
            "members": len(people),
            "active_members": sum(1 for p in people if p["active"]),
            "sign_ins_last_7_days": signins_7d,
            "sign_ins_last_30_days": signins_30d,
            "documents": docs_total,
            "documents_last_7_days": docs_7d,
            "reviews": reviews_total,
            "reviews_last_7_days": reviews_7d,
            "findings": findings_total,
        },
        "people": people,
        "recent_sign_ins": [
            {
                "who": names_by_id.get(r.user_id, "Unknown"),
                "when": r.created_at.isoformat(),
                "how": _LOGIN_METHOD.get(r.action, "Unknown"),
                "device": _device_from_ua(r.user_agent),
                "from_ip": r.ip_address,
            }
            for r in signin_rows
        ],
        "recent_activity": [
            {
                "who": names_by_id.get(r.user_id, "Someone"),
                "what": _humanize_action(r.action),
                "when": r.created_at.isoformat(),
            }
            for r in activity_rows
        ],
        "ai_usage": {
            "reviews_completed": reviews_completed or 0,
            "reviews_failed": reviews_failed or 0,
            "checks_per_review": 7,
            "ai_calls_estimate": (reviews_completed or 0) * 7,
            "average_review_seconds": round(float(avg_seconds), 1) if avg_seconds else None,
            "models_in_use": models_in_use,
            "last_review_at": last_review_at.isoformat() if last_review_at else None,
        },
    }


@router.get("/organization", summary="Get current org settings")
async def get_organization_settings(
    current_user: TokenData = Depends(require_role("admin")),
    db: AsyncSession = Depends(get_db),
):
    """T-2081: current org's settings (name, subscription tier, branding)."""
    org = await get_organization(db, UUID(str(current_user.org_id)))
    if org is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Organization not found"
        )
    return _org_response(org)


@router.patch("/organization", summary="Update org name/branding")
async def patch_organization_settings(
    body: OrganizationSettingsUpdate,
    current_user: TokenData = Depends(require_role("admin")),
    db: AsyncSession = Depends(get_db),
):
    """T-2082: update name and/or branding (logo_url, brand colors)."""
    fields = body.model_dump(exclude_unset=True)
    org = await update_organization(db, UUID(str(current_user.org_id)), **fields)
    if org is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Organization not found"
        )
    return _org_response(org)


@router.get("/users", summary="List org users")
async def get_org_users(
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=1000),
    current_user: TokenData = Depends(require_role("admin")),
    db: AsyncSession = Depends(get_db),
):
    """T-2086: paginated user directory for the caller's org."""
    users = await list_org_users(db, UUID(str(current_user.org_id)), skip, limit)
    return [_user_response(u) for u in users]


@router.patch("/users/{user_id}/role", summary="Change a user's role")
async def patch_user_role(
    user_id: UUID,
    body: UserRoleUpdate,
    current_user: TokenData = Depends(require_role("admin")),
    db: AsyncSession = Depends(get_db),
):
    """T-2086: change a user's role. Refuses to demote the last active admin."""
    try:
        user = await update_user_role(
            db, UUID(str(current_user.org_id)), user_id, body.role
        )
    except LastAdminError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))

    if user is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="User not found"
        )
    return _user_response(user)
