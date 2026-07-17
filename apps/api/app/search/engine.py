"""T-2001/T-2003: PostgreSQL full-text search over documents, org-scoped.

Combines filename + document_type + parsed_text into one weighted
tsvector (filename outranks document_type outranks parsed_text) and
ranks matches with ts_rank. `_SEARCH_VECTOR` must stay textually
identical to the expression indexed by
migrations/002_phase2_search.sql's idx_documents_search_combined_fts,
or Postgres can't use that GIN index for the match.
"""

from __future__ import annotations

import uuid
from datetime import date, timedelta
from typing import Optional

from sqlalchemy import func, literal_column, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.sql.elements import ColumnElement

from app.models.document import Document
from app.search.indexer import build_tsquery

_CONFIG = "english"


def _weighted(column: ColumnElement, weight: str) -> ColumnElement:
    # setweight()'s 2nd arg is Postgres's internal "char" type. A normal
    # bound VARCHAR param has no implicit cast to "char" (Postgres raises
    # "function setweight(tsvector, character varying) does not exist"),
    # so this must be a literal, not func.setweight(..., weight).
    return func.setweight(
        func.to_tsvector(_CONFIG, func.coalesce(column, "")), literal_column(f"'{weight}'")
    )


# documents.filename ('A') > documents.document_type ('B') > documents.parsed_text ('C')
_SEARCH_VECTOR = (
    _weighted(Document.filename, "A")
    .op("||")(_weighted(Document.document_type, "B"))
    .op("||")(_weighted(Document.parsed_text, "C"))
)


async def search_documents(
    db: AsyncSession,
    org_id: uuid.UUID,
    query: str,
    document_type: Optional[str] = None,
    date_from: Optional[date] = None,
    date_to: Optional[date] = None,
    skip: int = 0,
    limit: int = 20,
) -> tuple[list[dict], int]:
    """Full-text search over one org's documents.

    Always scoped by `org_id` (pass current_user.org_id -- never a
    client-supplied value) and `deleted_at IS NULL`.

    Returns:
        (results, total_count). Each result dict has doc_id, filename,
        document_type, rank (float in [0, 1)), snippet, created_at (all
        JSON-safe: doc_id/created_at are strings).
    """
    tsquery = build_tsquery(query)

    filters = [
        Document.org_id == org_id,
        Document.deleted_at.is_(None),
        _SEARCH_VECTOR.op("@@")(tsquery),
    ]
    if document_type:
        filters.append(Document.document_type == document_type)
    if date_from:
        filters.append(Document.created_at >= date_from)
    if date_to:
        # date_to is inclusive of the whole day.
        filters.append(Document.created_at < date_to + timedelta(days=1))

    total = (await db.execute(select(func.count(Document.doc_id)).where(*filters))).scalar_one()

    # normalization=32 -> rank / (rank + 1); keeps rank in [0, 1).
    rank = func.ts_rank(_SEARCH_VECTOR, tsquery, 32).label("rank")
    # ponytail: ts_headline only highlights within parsed_text, so a
    # filename/document_type-only match gets an empty snippet. Good
    # enough for a search-result excerpt; revisit if that's confusing
    # in the UI.
    snippet = func.ts_headline(_CONFIG, func.coalesce(Document.parsed_text, ""), tsquery).label(
        "snippet"
    )

    stmt = (
        select(Document, rank, snippet)
        .where(*filters)
        .order_by(rank.desc())
        .offset(skip)
        .limit(limit)
    )
    rows = (await db.execute(stmt)).all()

    results = [
        {
            "doc_id": str(doc.doc_id),
            "filename": doc.filename,
            "document_type": doc.document_type,
            "rank": float(rank_value),
            "snippet": snippet_value or "",
            "created_at": doc.created_at.isoformat(),
        }
        for doc, rank_value, snippet_value in rows
    ]
    return results, total
