"""T-2036/T-2037/T-2038/T-2039: Knowledge base CRUD, search, and finding integrations.

Covers FAQ database (T-2036), best practices guide (T-2039), similar findings
search (T-2037), and issue resolution lookups (T-2038). All functions are
org-scoped (pass current_user.org_id).
"""

from __future__ import annotations

import uuid
from typing import Any, Optional

from sqlalchemy import and_, desc, func, literal_column, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.sql.elements import ColumnElement

from app.models.finding import Finding
from app.models.kb_article import KBArticle
from app.search.indexer import build_tsquery

_CONFIG = "english"


def _weighted(column: ColumnElement, weight: str) -> ColumnElement:
    """Weighted tsvector for ranking, matching app/search/engine.py's style.

    setweight()'s 2nd arg is Postgres's internal "char" type. A normal
    bound VARCHAR param has no implicit cast to "char", so this must be
    a literal, not func.setweight(..., weight).
    """
    return func.setweight(
        func.to_tsvector(_CONFIG, func.coalesce(column, "")), literal_column(f"'{weight}'")
    )


async def create_article(
    db: AsyncSession,
    org_id: uuid.UUID,
    article_type: str,
    title: str,
    content: str,
    tags: Optional[list[str]] = None,
    created_by_user_id: Optional[uuid.UUID] = None,
) -> KBArticle:
    """Create a new knowledge base article (FAQ, best practice, or guide).

    Args:
        db: AsyncSession
        org_id: Organization UUID (from current_user.org_id)
        article_type: One of 'faq', 'best_practice', 'guide'
        title: Article title
        content: Article body
        tags: Optional list of tags (stored as JSONB array)
        created_by_user_id: Optional user who created the article

    Returns:
        KBArticle: the created article
    """
    article = KBArticle(
        org_id=org_id,
        article_type=article_type,
        title=title,
        content=content,
        tags=tags or [],
        created_by_user_id=created_by_user_id,
    )
    db.add(article)
    await db.flush()
    await db.refresh(article)
    return article


async def list_articles(
    db: AsyncSession,
    org_id: uuid.UUID,
    article_type: Optional[str] = None,
    skip: int = 0,
    limit: int = 50,
) -> list[KBArticle]:
    """List knowledge base articles for an org, optionally filtered by type.

    Args:
        db: AsyncSession
        org_id: Organization UUID (from current_user.org_id)
        article_type: Optional filter: 'faq', 'best_practice', 'guide'
        skip: Pagination offset
        limit: Pagination limit

    Returns:
        list[KBArticle]: matching articles, ordered by created_at desc
    """
    filters = [
        KBArticle.org_id == org_id,
        KBArticle.deleted_at.is_(None),
    ]
    if article_type:
        filters.append(KBArticle.article_type == article_type)

    stmt = (
        select(KBArticle)
        .where(*filters)
        .order_by(desc(KBArticle.created_at))
        .offset(skip)
        .limit(limit)
    )
    result = await db.execute(stmt)
    return result.scalars().all()


async def search_articles(
    db: AsyncSession,
    org_id: uuid.UUID,
    query: str,
    skip: int = 0,
    limit: int = 20,
) -> list[dict]:
    """Full-text search over knowledge base articles (title + content).

    Reuses the same weighted tsvector + ts_rank pattern as
    app/search/engine.py to maintain consistency.

    Args:
        db: AsyncSession
        org_id: Organization UUID (from current_user.org_id)
        query: Search query (free-form user input, sanitized by build_tsquery)
        skip: Pagination offset
        limit: Pagination limit

    Returns:
        list[dict]: results with article_id, article_type, title, snippet, rank
    """
    tsquery = build_tsquery(query)

    # title ('A') outranks content ('B')
    search_vector = (
        _weighted(KBArticle.title, "A")
        .op("||")(_weighted(KBArticle.content, "B"))
    )

    filters = [
        KBArticle.org_id == org_id,
        KBArticle.deleted_at.is_(None),
        search_vector.op("@@")(tsquery),
    ]

    # normalization=32 -> rank / (rank + 1); keeps rank in [0, 1).
    rank = func.ts_rank(search_vector, tsquery, 32).label("rank")
    snippet = func.ts_headline(_CONFIG, func.coalesce(KBArticle.content, ""), tsquery).label(
        "snippet"
    )

    stmt = (
        select(KBArticle, rank, snippet)
        .where(*filters)
        .order_by(rank.desc())
        .offset(skip)
        .limit(limit)
    )
    rows = (await db.execute(stmt)).all()

    return [
        {
            "article_id": str(article.article_id),
            "article_type": article.article_type,
            "title": article.title,
            "snippet": snippet_value or "",
            "rank": float(rank_value),
        }
        for article, rank_value, snippet_value in rows
    ]


async def delete_article(
    db: AsyncSession,
    org_id: uuid.UUID,
    article_id: uuid.UUID,
) -> None:
    """Soft-delete a knowledge base article.

    Args:
        db: AsyncSession
        org_id: Organization UUID (from current_user.org_id)
        article_id: Article UUID to delete

    Raises:
        ValueError: if article not found or belongs to another org
    """
    result = await db.execute(
        select(KBArticle).where(
            and_(
                KBArticle.article_id == article_id,
                KBArticle.org_id == org_id,
                KBArticle.deleted_at.is_(None),
            )
        )
    )
    article = result.scalar_one_or_none()

    if not article:
        raise ValueError("Article not found")

    article.deleted_at = func.clock_timestamp()
    await db.flush()


async def search_similar_findings(
    db: AsyncSession,
    org_id: uuid.UUID,
    query: str,
    limit: int = 10,
) -> list[dict]:
    """T-2037: Full-text search over findings (title + description).

    Returns resolved and unresolved findings matching the query. Useful for
    finding similar issues the org has already encountered.

    Args:
        db: AsyncSession
        org_id: Organization UUID (from current_user.org_id)
        query: Search query over finding title/description
        limit: Max results

    Returns:
        list[dict]: results with finding_id, title, severity, review_id, rank
    """
    tsquery = build_tsquery(query)

    # title ('A') outranks description ('B')
    search_vector = (
        _weighted(Finding.title, "A")
        .op("||")(_weighted(Finding.description, "B"))
    )

    filters = [
        Finding.org_id == org_id,
        Finding.deleted_at.is_(None),
        search_vector.op("@@")(tsquery),
    ]

    rank = func.ts_rank(search_vector, tsquery, 32).label("rank")

    stmt = (
        select(Finding, rank)
        .where(*filters)
        .order_by(rank.desc())
        .limit(limit)
    )
    rows = (await db.execute(stmt)).all()

    return [
        {
            "finding_id": str(finding.finding_id),
            "title": finding.title,
            "severity": finding.severity,
            "review_id": str(finding.review_id),
            "rank": float(rank_value),
        }
        for finding, rank_value in rows
    ]


async def find_issue_resolution(
    db: AsyncSession,
    org_id: uuid.UUID,
    finding_category: str,
    limit: int = 10,
) -> list[dict]:
    """T-2038: Find past resolutions for a given finding category.

    Query resolved findings in the given category to show what
    recommendations led to resolution.

    Args:
        db: AsyncSession
        org_id: Organization UUID (from current_user.org_id)
        finding_category: Finding category to query (e.g., 'Clause Risk', 'Data Privacy')
        limit: Max results

    Returns:
        list[dict]: resolved findings with finding_id, title, description, recommendation
    """
    stmt = (
        select(Finding)
        .where(
            and_(
                Finding.org_id == org_id,
                Finding.category == finding_category,
                Finding.status == "resolved",
                Finding.deleted_at.is_(None),
            )
        )
        .order_by(desc(Finding.updated_at))
        .limit(limit)
    )
    findings = (await db.execute(stmt)).scalars().all()

    return [
        {
            "finding_id": str(f.finding_id),
            "title": f.title,
            "description": f.description,
            "recommendation": f.recommendation,
        }
        for f in findings
    ]
