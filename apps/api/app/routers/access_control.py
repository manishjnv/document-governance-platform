"""Fine-grained access control API (T-2056/T-2057/T-2058/T-2059/T-2060).

Grants: any authenticated org member may create/list/revoke resource
grants (delegation is a peer action, not an admin action). IP allowlist
management is admin-only -- it changes who can reach the org at all.
"""

from __future__ import annotations

from datetime import datetime
from typing import Literal, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.compliance.access_control import (
    grant_access,
    list_access_for_resource,
    revoke_access,
)
from app.compliance.ip_policy import add_ip_entry, list_ip_entries, remove_ip_entry
from app.db.session import get_db
from app.dependencies import get_current_user, require_role
from app.schemas.auth import TokenData

router = APIRouter(prefix="/api/v1/access", tags=["access-control"])


class GrantCreate(BaseModel):
    resource_type: Literal["document", "review"]
    resource_id: UUID
    grantee_user_id: UUID
    permission: Literal["view", "comment", "edit", "approve"]
    expires_at: Optional[datetime] = None


class IPEntryCreate(BaseModel):
    cidr: str = Field(..., max_length=43)
    description: Optional[str] = Field(None, max_length=255)


@router.post("/grants", status_code=status.HTTP_201_CREATED, summary="Grant resource access")
async def create_grant(
    body: GrantCreate,
    current_user: TokenData = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    grant = await grant_access(
        db,
        org_id=current_user.org_id,
        resource_type=body.resource_type,
        resource_id=body.resource_id,
        grantee_user_id=body.grantee_user_id,
        permission=body.permission,
        granted_by_user_id=current_user.user_id,
        expires_at=body.expires_at,
    )
    return {
        "grant_id": str(grant.grant_id),
        "resource_type": grant.resource_type,
        "resource_id": str(grant.resource_id),
        "grantee_user_id": str(grant.grantee_user_id),
        "permission": grant.permission,
        "granted_by_user_id": str(grant.granted_by_user_id) if grant.granted_by_user_id else None,
        "expires_at": grant.expires_at.isoformat() if grant.expires_at else None,
        "created_at": grant.created_at.isoformat(),
    }


@router.get("/grants", summary="List access grants for a resource")
async def get_grants(
    resource_type: Literal["document", "review"] = Query(...),
    resource_id: UUID = Query(...),
    current_user: TokenData = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    return await list_access_for_resource(
        db, org_id=current_user.org_id, resource_type=resource_type, resource_id=resource_id
    )


@router.delete("/grants/{grant_id}", status_code=status.HTTP_204_NO_CONTENT, summary="Revoke a grant")
async def delete_grant(
    grant_id: UUID,
    current_user: TokenData = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    await revoke_access(
        db, org_id=current_user.org_id, grant_id=grant_id, revoked_by_user_id=current_user.user_id
    )


@router.get(
    "/ip-allowlist",
    summary="List org IP allowlist entries",
    dependencies=[Depends(require_role("admin"))],
)
async def get_ip_allowlist(
    current_user: TokenData = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    entries = await list_ip_entries(db, current_user.org_id)
    return [
        {
            "entry_id": str(e.entry_id),
            "cidr": e.cidr,
            "description": e.description,
            "created_at": e.created_at.isoformat(),
        }
        for e in entries
    ]


@router.post(
    "/ip-allowlist",
    status_code=status.HTTP_201_CREATED,
    summary="Add an IP allowlist entry",
    dependencies=[Depends(require_role("admin"))],
)
async def add_ip_allowlist_entry(
    body: IPEntryCreate,
    current_user: TokenData = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    try:
        entry = await add_ip_entry(db, current_user.org_id, body.cidr, body.description)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Invalid CIDR"
        )
    return {
        "entry_id": str(entry.entry_id),
        "cidr": entry.cidr,
        "description": entry.description,
        "created_at": entry.created_at.isoformat(),
    }


@router.delete(
    "/ip-allowlist/{entry_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Remove an IP allowlist entry",
    dependencies=[Depends(require_role("admin"))],
)
async def delete_ip_allowlist_entry(
    entry_id: UUID,
    current_user: TokenData = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    await remove_ip_entry(db, current_user.org_id, entry_id)
