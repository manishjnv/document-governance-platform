"""Knowledge base API endpoints.

T-2036: FAQ database
T-2037: Similar findings search
T-2038: Issue resolution database
T-2039: Best practices guide
T-2040: Knowledge base search UI
"""

import logging
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.dependencies import get_current_user
from app.insights.knowledge import (
    create_article,
    delete_article,
    find_issue_resolution,
    list_articles,
    search_articles,
    search_similar_findings,
)
from app.models.kb_article import KBArticle
from app.schemas.auth import TokenData

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/knowledge-base", tags=["knowledge-base"])


class ArticleCreate:
    """Request schema for creating an article."""

    def __init__(
        self,
        article_type: str,
        title: str,
        content: str,
        tags: list[str] | None = None,
    ):
        self.article_type = article_type
        self.title = title
        self.content = content
        self.tags = tags or []


class ArticleRead:
    """Response schema for an article."""

    def __init__(self, article: KBArticle):
        self.article_id = str(article.article_id)
        self.article_type = article.article_type
        self.title = article.title
        self.content = article.content
        self.tags = article.tags
        self.created_by_user_id = str(article.created_by_user_id) if article.created_by_user_id else None
        self.created_at = article.created_at.isoformat()
        self.updated_at = article.updated_at.isoformat()


@router.post(
    "/articles",
    status_code=status.HTTP_201_CREATED,
    summary="Create knowledge base article",
)
async def post_article(
    article_type: str = Query(..., description="Type: faq, best_practice, or guide"),
    title: str = Query(..., description="Article title"),
    content: str = Query(..., description="Article content"),
    tags: list[str] = Query([], description="Optional tags"),
    current_user: TokenData = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Create a new knowledge base article.

    **T-2036/T-2039: FAQ and Best Practices Database**
    - article_type: one of 'faq', 'best_practice', 'guide'
    - Returns: article_id, article_type, title, content, tags, created_at
    """
    if article_type not in ("faq", "best_practice", "guide"):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="article_type must be 'faq', 'best_practice', or 'guide'",
        )

    article = await create_article(
        db,
        current_user.org_id,
        article_type,
        title,
        content,
        tags,
        current_user.user_id,
    )
    await db.commit()

    return {
        "article_id": str(article.article_id),
        "article_type": article.article_type,
        "title": article.title,
        "content": article.content,
        "tags": article.tags,
        "created_by_user_id": str(article.created_by_user_id) if article.created_by_user_id else None,
        "created_at": article.created_at.isoformat(),
        "updated_at": article.updated_at.isoformat(),
    }


@router.get(
    "/articles",
    status_code=status.HTTP_200_OK,
    summary="List knowledge base articles",
)
async def get_articles(
    article_type: str | None = Query(None, description="Filter by type: faq, best_practice, guide"),
    skip: int = Query(0, ge=0, description="Pagination offset"),
    limit: int = Query(50, ge=1, le=200, description="Pagination limit"),
    current_user: TokenData = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """List knowledge base articles for the org.

    **T-2036/T-2039: FAQ and Best Practices Database**
    - Optional filter by article_type
    - Returns: list of articles (paginated)
    """
    articles = await list_articles(
        db,
        current_user.org_id,
        article_type=article_type,
        skip=skip,
        limit=limit,
    )

    return {
        "articles": [
            {
                "article_id": str(a.article_id),
                "article_type": a.article_type,
                "title": a.title,
                "content": a.content,
                "tags": a.tags,
                "created_by_user_id": str(a.created_by_user_id) if a.created_by_user_id else None,
                "created_at": a.created_at.isoformat(),
                "updated_at": a.updated_at.isoformat(),
            }
            for a in articles
        ]
    }


@router.delete(
    "/articles/{article_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete knowledge base article",
)
async def delete_kb_article(
    article_id: UUID,
    current_user: TokenData = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> None:
    """Soft-delete a knowledge base article.

    **T-2036/T-2039: FAQ and Best Practices Database**
    """
    try:
        await delete_article(db, current_user.org_id, article_id)
        await db.commit()
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Article not found",
        )


@router.get(
    "/articles/search",
    status_code=status.HTTP_200_OK,
    summary="Full-text search knowledge base",
)
async def search_kb(
    q: str = Query(..., min_length=1, description="Search query"),
    skip: int = Query(0, ge=0, description="Pagination offset"),
    limit: int = Query(20, ge=1, le=100, description="Pagination limit"),
    current_user: TokenData = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Full-text search over knowledge base (title + content).

    **T-2040: Knowledge Base Search UI**
    - Returns: ranked results with snippet excerpt
    """
    try:
        results = await search_articles(db, current_user.org_id, q, skip, limit)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(e),
        )

    return {"results": results, "query": q}


@router.get(
    "/similar-findings",
    status_code=status.HTTP_200_OK,
    summary="Search similar findings",
)
async def similar_findings(
    q: str = Query(..., min_length=1, description="Search query over finding titles/descriptions"),
    limit: int = Query(10, ge=1, le=50, description="Max results"),
    current_user: TokenData = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """T-2037: Full-text search over findings (title + description).

    Find similar issues the org has already discovered. Useful for identifying
    patterns and checking if a new finding is novel or a known issue.
    """
    try:
        results = await search_similar_findings(db, current_user.org_id, q, limit)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(e),
        )

    return {"results": results, "query": q}


@router.get(
    "/issue-resolutions",
    status_code=status.HTTP_200_OK,
    summary="Find past issue resolutions",
)
async def issue_resolutions(
    category: str = Query(..., description="Finding category (e.g., 'Clause Risk')"),
    limit: int = Query(10, ge=1, le=50, description="Max results"),
    current_user: TokenData = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """T-2038: Find past resolutions for a finding category.

    Shows what recommendations successfully resolved similar findings,
    helping teams learn from past solutions.
    """
    results = await find_issue_resolution(db, current_user.org_id, category, limit)

    return {"results": results, "category": category}
