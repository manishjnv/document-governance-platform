"""Per-org entitlement gate for LLM-spending "run" actions (review triggers,
MITRE assessment runs). Free-tier orgs can create/configure everything but
can't kick off a paid pipeline run until upgraded (or a platform admin) --
unless the platform admin has granted them a fixed run_allowance, which is
consumed one per run."""

from sqlalchemy import select, update
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
RUNS_EXHAUSTED_DETAIL = (
    "Your organisation has used all of its granted runs. Use the "
    "request-access form to ask for more."
)


def _is_platform_admin(email: str) -> bool:
    platform_admins = {
        e.strip().lower() for e in settings.platform_admin_emails.split(",") if e.strip()
    }
    return email.strip().lower() in platform_admins


def runs_enabled(*, subscription_tier: str, email: str, run_allowance: int = 0) -> bool:
    if not settings.require_paid_tier_for_runs:
        return True
    if _is_platform_admin(email):
        return True
    return subscription_tier in ("pro", "enterprise") or run_allowance > 0


async def require_runs_enabled(
    current_user: TokenData = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> TokenData:
    """Allowance-aware gate: pro/enterprise/admin pass through unlimited;
    a free org with run_allowance > 0 consumes one (atomically, uncommitted
    -- the handler's own commit lands it, so a run that errors before
    commit doesn't consume an allowance)."""
    result = await db.execute(
        select(Organization.subscription_tier, Organization.run_allowance).where(
            Organization.org_id == current_user.org_id
        )
    )
    row = result.one_or_none()
    if row is None:
        # Missing org -> fail closed, same as any other invalid-tier state.
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=RUNS_DISABLED_DETAIL)
    tier, run_allowance = row

    if not settings.require_paid_tier_for_runs:
        return current_user
    if _is_platform_admin(current_user.email):
        return current_user
    if tier in ("pro", "enterprise"):
        return current_user

    if run_allowance > 0:
        consumed = await db.execute(
            update(Organization)
            .where(Organization.org_id == current_user.org_id, Organization.run_allowance > 0)
            .values(run_allowance=Organization.run_allowance - 1)
            .returning(Organization.run_allowance)
        )
        if consumed.first() is None:
            # Race: another request drained it between our SELECT and UPDATE.
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN, detail=RUNS_EXHAUSTED_DETAIL
            )
        return current_user

    raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=RUNS_DISABLED_DETAIL)


async def require_paid_runs(
    current_user: TokenData = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> TokenData:
    """Tier-only gate, no allowance -- used for bulk trigger and the Celery
    scheduled pull, which stay out of the per-run allowance economics."""
    result = await db.execute(
        select(Organization.subscription_tier).where(
            Organization.org_id == current_user.org_id
        )
    )
    tier = result.scalar_one_or_none()
    if tier is None or not runs_enabled(subscription_tier=tier, email=current_user.email):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=RUNS_DISABLED_DETAIL)
    return current_user
