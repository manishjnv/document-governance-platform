"""Admin customization config endpoints: rules, agents, scoring weights,
document types, field mappings.

T-2091: Custom rules management
T-2092: AI agent configuration
T-2093: Scoring weight customization
T-2094: Document type customization
T-2095: Field mappings

All admin-only, scoped to current_user.org_id. Separate router file/prefix
from app/routers/admin.py and admin_extra.py (which already own other
/api/v1/admin paths). Mounted in main.py (2026-07-18 router audit confirmed
this) with real test coverage in test_admin_config.py.
"""

import logging
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.admin.customization import (
    add_document_type,
    get_agent_config,
    get_document_types,
    get_field_mappings,
    get_rule_config,
    get_scoring_weights,
    remove_document_type,
    remove_field_mapping,
    set_agent_enabled,
    set_field_mapping,
    set_rule_enabled,
    set_scoring_weight,
)
from app.db.session import get_db
from app.dependencies import require_role
from app.schemas.auth import TokenData

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/v1/admin/config", tags=["admin-config"])


class RuleConfigUpdate(BaseModel):
    rule_id: str = Field(..., max_length=100)
    enabled: bool


class AgentConfigUpdate(BaseModel):
    agent_name: str = Field(..., max_length=100)
    enabled: bool


class ScoringWeightUpdate(BaseModel):
    category: str = Field(..., max_length=50)
    weight: float = Field(..., ge=0)


class DocumentTypeUpdate(BaseModel):
    """action=add creates/no-ops type_name; action=remove deletes it."""

    type_name: str = Field(..., min_length=1, max_length=50)
    action: str = Field(..., pattern="^(add|remove)$")


class FieldMappingUpdate(BaseModel):
    """action=set requires target_category; action=remove ignores it."""

    source_field: str = Field(..., min_length=1, max_length=100)
    action: str = Field(..., pattern="^(set|remove)$")
    target_category: Optional[str] = Field(None, max_length=50)


# ---------------------------------------------------------------------------
# T-2091: rules
# ---------------------------------------------------------------------------


@router.get("/rules", summary="Get org rule config")
async def get_rules_config(
    current_user: TokenData = Depends(require_role("admin")),
    db: AsyncSession = Depends(get_db),
):
    """All built-in rule_ids -> enabled for the caller's org."""
    return await get_rule_config(db, current_user.org_id)


@router.patch("/rules", summary="Enable/disable a built-in rule")
async def patch_rules_config(
    body: RuleConfigUpdate,
    current_user: TokenData = Depends(require_role("admin")),
    db: AsyncSession = Depends(get_db),
):
    try:
        await set_rule_enabled(db, current_user.org_id, body.rule_id, body.enabled)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    return await get_rule_config(db, current_user.org_id)


# ---------------------------------------------------------------------------
# T-2092: agents
# ---------------------------------------------------------------------------


@router.get("/agents", summary="Get org AI agent config")
async def get_agents_config(
    current_user: TokenData = Depends(require_role("admin")),
    db: AsyncSession = Depends(get_db),
):
    """All real reviewer agent names -> enabled for the caller's org."""
    return await get_agent_config(db, current_user.org_id)


@router.patch("/agents", summary="Enable/disable an AI reviewer agent")
async def patch_agents_config(
    body: AgentConfigUpdate,
    current_user: TokenData = Depends(require_role("admin")),
    db: AsyncSession = Depends(get_db),
):
    try:
        await set_agent_enabled(db, current_user.org_id, body.agent_name, body.enabled)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    return await get_agent_config(db, current_user.org_id)


# ---------------------------------------------------------------------------
# T-2093: scoring weights
# ---------------------------------------------------------------------------


@router.get("/scoring-weights", summary="Get org scoring weight config")
async def get_scoring_weights_config(
    current_user: TokenData = Depends(require_role("admin")),
    db: AsyncSession = Depends(get_db),
):
    """All real scoring categories -> weight for the caller's org."""
    return await get_scoring_weights(db, current_user.org_id)


@router.patch("/scoring-weights", summary="Set a scoring category weight")
async def patch_scoring_weights_config(
    body: ScoringWeightUpdate,
    current_user: TokenData = Depends(require_role("admin")),
    db: AsyncSession = Depends(get_db),
):
    try:
        await set_scoring_weight(db, current_user.org_id, body.category, body.weight)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    return await get_scoring_weights(db, current_user.org_id)


# ---------------------------------------------------------------------------
# T-2094: document types
# ---------------------------------------------------------------------------


@router.get("/document-types", summary="Get org custom document types")
async def get_document_types_config(
    current_user: TokenData = Depends(require_role("admin")),
    db: AsyncSession = Depends(get_db),
):
    return await get_document_types(db, current_user.org_id)


@router.patch("/document-types", summary="Add or remove a custom document type")
async def patch_document_types_config(
    body: DocumentTypeUpdate,
    current_user: TokenData = Depends(require_role("admin")),
    db: AsyncSession = Depends(get_db),
):
    if body.action == "add":
        await add_document_type(db, current_user.org_id, body.type_name)
    else:
        await remove_document_type(db, current_user.org_id, body.type_name)
    return await get_document_types(db, current_user.org_id)


# ---------------------------------------------------------------------------
# T-2095: field mappings
# ---------------------------------------------------------------------------


@router.get("/field-mappings", summary="Get org field mappings")
async def get_field_mappings_config(
    current_user: TokenData = Depends(require_role("admin")),
    db: AsyncSession = Depends(get_db),
):
    return await get_field_mappings(db, current_user.org_id)


@router.patch("/field-mappings", summary="Set or remove a field mapping")
async def patch_field_mappings_config(
    body: FieldMappingUpdate,
    current_user: TokenData = Depends(require_role("admin")),
    db: AsyncSession = Depends(get_db),
):
    if body.action == "set":
        if not body.target_category:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="target_category is required when action=set",
            )
        try:
            await set_field_mapping(
                db, current_user.org_id, body.source_field, body.target_category
            )
        except ValueError as e:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    else:
        await remove_field_mapping(db, current_user.org_id, body.source_field)
    return await get_field_mappings(db, current_user.org_id)
