"""Filter templates API endpoints. T-2015: Save, list, delete filter templates."""

import logging
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.pagination import PaginationParams, paginate
from app.db.session import get_db
from app.dependencies import get_current_user
from app.models.filter_template import FilterTemplate
from app.schemas.auth import TokenData
from app.search.filters import validate_filters

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/v1/filter-templates", tags=["filter-templates"])


@router.post("", status_code=status.HTTP_201_CREATED, summary="Save filter template")
async def save_filter_template(
    body: dict,
    current_user: TokenData = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Save a named filter template for the current user.

    Request body: {"name": str, "filters": dict}
    """
    name = body.get("name")
    filters = body.get("filters", {})

    if not name:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="name is required",
        )

    # Validate filters
    validation_errors = validate_filters(filters)
    if validation_errors:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=validation_errors,
        )

    # Create template
    template = FilterTemplate(
        org_id=UUID(str(current_user.org_id)),
        user_id=UUID(str(current_user.user_id)),
        name=name,
        filters=filters,
    )

    db.add(template)
    try:
        await db.commit()
        await db.refresh(template)
    except Exception as e:
        await db.rollback()
        logger.error(f"Failed to save filter template: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to save filter template",
        )

    return {
        "template_id": str(template.template_id),
        "name": template.name,
        "filters": template.filters,
        "created_at": template.created_at.isoformat(),
    }


@router.get("", summary="List filter templates")
async def list_filter_templates(
    pagination: PaginationParams = Depends(),
    current_user: TokenData = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """List all filter templates for the current user (paginated)."""
    query = (
        select(FilterTemplate)
        .where(FilterTemplate.user_id == UUID(str(current_user.user_id)))
        .order_by(FilterTemplate.created_at.desc())
    )
    page = await paginate(query, db, pagination)

    return [
        {
            "template_id": str(t.template_id),
            "name": t.name,
            "filters": t.filters,
            "created_at": t.created_at.isoformat(),
        }
        for t in page["items"]
    ]


@router.delete("/{template_id}", status_code=status.HTTP_204_NO_CONTENT, summary="Delete filter template")
async def delete_filter_template(
    template_id: UUID,
    current_user: TokenData = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Delete a filter template owned by the current user."""
    result = await db.execute(
        select(FilterTemplate).where(
            (FilterTemplate.template_id == template_id)
            & (FilterTemplate.user_id == UUID(str(current_user.user_id)))
        )
    )
    template = result.scalar_one_or_none()

    if not template:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Filter template not found",
        )

    try:
        await db.delete(template)
        await db.commit()
    except Exception as e:
        await db.rollback()
        logger.error(f"Failed to delete filter template: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to delete filter template",
        )
