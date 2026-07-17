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
