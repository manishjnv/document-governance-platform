"""Per-org entitlement gate for LLM-spending "run" actions (review triggers,
MITRE assessment runs). Free-tier orgs can create/configure everything but
can't kick off a paid pipeline run until upgraded (or a platform admin)."""

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import Depends, HTTPException, status

from app.config import settings
from app.db.session import get_db
from app.dependencies import get_current_user
from app.models.organization import Organization
from app.schemas.auth import TokenData

RUNS_DISABLED_DETAIL = (
    "Assessments are not enabled for your organisation yet. Use the "
    "request-access form to contact us and we will switch it on."
)


def runs_enabled(*, subscription_tier: str, email: str) -> bool:
    if not settings.require_paid_tier_for_runs:
        return True
    platform_admins = {
        e.strip().lower() for e in settings.platform_admin_emails.split(",") if e.strip()
    }
    if email.strip().lower() in platform_admins:
        return True
    return subscription_tier in ("pro", "enterprise")


async def require_runs_enabled(
    current_user: TokenData = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> TokenData:
    result = await db.execute(
        select(Organization.subscription_tier).where(
            Organization.org_id == current_user.org_id
        )
    )
    tier = result.scalar_one_or_none()
    # Missing org -> fail closed, same as any other invalid-tier state.
    if tier is None or not runs_enabled(subscription_tier=tier, email=current_user.email):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=RUNS_DISABLED_DETAIL)
    return current_user
