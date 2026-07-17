"""Full-text document search API.

T-2002: GET /api/v1/search -- keyword search across the caller's org
documents, ranked (T-2003) and filterable by document_type/date range.
"""

from __future__ import annotations

from datetime import date
from typing import Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.dependencies import get_current_user
from app.schemas.auth import TokenData
from app.schemas.search import SearchResponse
from app.search.engine import search_documents

router = APIRouter(prefix="/api/v1/search", tags=["search"])


@router.get("", response_model=SearchResponse, summary="Search documents")
async def search(
    q: str = Query(..., min_length=1, description="Search query"),
    document_type: Optional[str] = Query(None, description="Filter by document type"),
    date_from: Optional[date] = Query(None, description="Only documents created on/after this date"),
    date_to: Optional[date] = Query(None, description="Only documents created on/before this date"),
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    current_user: TokenData = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Full-text search over documents in the caller's organization.

    Ranks matches across filename, document_type, and parsed_text
    (T-2003). Always scoped to `current_user.org_id` -- org_id is never
    a client-supplied parameter, so one org can never see another org's
    documents.
    """
    results, total = await search_documents(
        db,
        current_user.org_id,
        q,
        document_type=document_type,
        date_from=date_from,
        date_to=date_to,
        skip=skip,
        limit=limit,
    )
    return {
        "query": q,
        "total": total,
        "skip": skip,
        "limit": limit,
        "results": results,
    }
