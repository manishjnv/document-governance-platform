"""Search history and saved searches endpoints.

Implementation: T-2005
- Search history audit trail (POST /api/v1/search/history, GET /api/v1/search/history)
- Saved search templates (POST /api/v1/search/saved, GET /api/v1/search/saved, DELETE /api/v1/search/saved/{saved_id})
"""

import logging
from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import desc, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.pagination import PaginationParams, paginate
from app.db.session import get_db
from app.dependencies import get_current_user
from app.models.search_history import SavedSearch, SearchHistory
from app.schemas.auth import TokenData
from app.schemas.search import (
    SavedSearchCreate,
    SavedSearchRead,
    SavedSearchUpdate,
    SearchHistoryCreate,
    SearchHistoryRead,
)

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/v1/search", tags=["search-history"])


# =====================================================================
# Search History Endpoints
# =====================================================================


@router.post(
    "/history",
    status_code=status.HTTP_201_CREATED,
    response_model=SearchHistoryRead,
    summary="Log a search to history",
)
async def create_search_history(
    body: SearchHistoryCreate,
    current_user: TokenData = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Log a search query to the user's search history.
    Called automatically after every search to build an audit trail.

    **T-2005: Search history endpoint**
    - Auto-logged; user doesn't call directly
    - Filters are stored as JSONB for later retrieval
    """
    obj = SearchHistory(
        org_id=current_user.org_id,
        user_id=current_user.user_id,
        query=body.query,
        filters=body.filters.model_dump(exclude_none=True),
    )
    db.add(obj)
    await db.commit()
    await db.refresh(obj)
    return obj


@router.get(
    "/history",
    response_model=list[SearchHistoryRead],
    summary="Get search history for current user",
)
async def list_search_history(
    limit: int = Query(20, ge=1, le=100),
    current_user: TokenData = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Get the last `limit` searches for the current user, newest first.

    **T-2005: Search history list**
    - Scoped to current user and org
    - Returns newest first (created_at DESC)
    """
    stmt = (
        select(SearchHistory)
        .where(
            SearchHistory.user_id == current_user.user_id,
            SearchHistory.org_id == current_user.org_id,
        )
        .order_by(desc(SearchHistory.created_at))
        .limit(limit)
    )
    result = await db.execute(stmt)
    return result.scalars().all()


# =====================================================================
# Saved Searches Endpoints
# =====================================================================


@router.post(
    "/saved",
    status_code=status.HTTP_201_CREATED,
    response_model=SavedSearchRead,
    summary="Save a search template",
)
async def create_saved_search(
    body: SavedSearchCreate,
    current_user: TokenData = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Save a named search template for later reuse.

    **T-2005: Saved search creation**
    - Name must be unique per (user_id, name)
    - Filters are stored as JSONB for later retrieval
    """
    obj = SavedSearch(
        org_id=current_user.org_id,
        user_id=current_user.user_id,
        name=body.name,
        query=body.query,
        filters=body.filters.model_dump(exclude_none=True),
    )
    db.add(obj)
    try:
        await db.commit()
        await db.refresh(obj)
    except IntegrityError:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"A saved search named '{body.name}' already exists for this user.",
        )
    return obj


@router.get(
    "/saved",
    response_model=list[SavedSearchRead],
    summary="List saved searches for current user",
)
async def list_saved_searches(
    pagination: PaginationParams = Depends(),
    current_user: TokenData = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Get all saved search templates for the current user, newest first.

    **T-2005: Saved search list**
    - Scoped to current user and org
    - Returns newest first (created_at DESC)
    - Paginated (page/page_size query params), default page_size 50
    """
    stmt = (
        select(SavedSearch)
        .where(
            SavedSearch.user_id == current_user.user_id,
            SavedSearch.org_id == current_user.org_id,
        )
        .order_by(desc(SavedSearch.created_at))
    )
    page = await paginate(stmt, db, pagination)
    return page["items"]


@router.get(
    "/saved/{saved_id}",
    response_model=SavedSearchRead,
    summary="Get a saved search by ID",
)
async def get_saved_search(
    saved_id: UUID,
    current_user: TokenData = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Retrieve a saved search by ID.

    **T-2005: Saved search retrieval**
    - Scoped to current user and org
    - Returns 404 if not found
    """
    stmt = select(SavedSearch).where(
        SavedSearch.saved_id == saved_id,
        SavedSearch.user_id == current_user.user_id,
        SavedSearch.org_id == current_user.org_id,
    )
    result = await db.execute(stmt)
    obj = result.scalar_one_or_none()
    if not obj:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Saved search not found")
    return obj


@router.patch(
    "/saved/{saved_id}",
    response_model=SavedSearchRead,
    summary="Update a saved search",
)
async def update_saved_search(
    saved_id: UUID,
    body: SavedSearchUpdate,
    current_user: TokenData = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Update a saved search (name, query, filters).

    **T-2005: Saved search update**
    - Scoped to current user and org
    - All fields are optional; only provided fields are updated
    """
    stmt = select(SavedSearch).where(
        SavedSearch.saved_id == saved_id,
        SavedSearch.user_id == current_user.user_id,
        SavedSearch.org_id == current_user.org_id,
    )
    result = await db.execute(stmt)
    obj = result.scalar_one_or_none()
    if not obj:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Saved search not found")

    if body.name is not None:
        obj.name = body.name
    if body.query is not None:
        obj.query = body.query
    if body.filters is not None:
        obj.filters = body.filters.model_dump(exclude_none=True)

    try:
        await db.commit()
        await db.refresh(obj)
    except IntegrityError:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"A saved search named '{body.name}' already exists for this user.",
        )
    return obj


@router.delete(
    "/saved/{saved_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a saved search",
)
async def delete_saved_search(
    saved_id: UUID,
    current_user: TokenData = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Hard-delete a saved search. (SavedSearch rows are small, user-owned; hard delete is appropriate.)

    **T-2005: Saved search deletion**
    - Scoped to current user and org
    - Returns 404 if not found
    """
    stmt = select(SavedSearch).where(
        SavedSearch.saved_id == saved_id,
        SavedSearch.user_id == current_user.user_id,
        SavedSearch.org_id == current_user.org_id,
    )
    result = await db.execute(stmt)
    obj = result.scalar_one_or_none()
    if not obj:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Saved search not found")

    await db.delete(obj)
    await db.commit()
    return None
