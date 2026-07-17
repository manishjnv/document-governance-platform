"""T-2001: helpers for turning raw user search input into a safe tsquery.

websearch_to_tsquery() (unlike to_tsquery/plainto_tsquery) already tolerates
free-form user input -- unbalanced quotes, bare "-", stray operators -- so
there is no manual escaping to write here. The only real job left is
rejecting an empty/whitespace-only query before it reaches the DB.
"""

from __future__ import annotations

from sqlalchemy import func
from sqlalchemy.sql.functions import Function

_SEARCH_CONFIG = "english"


def sanitize_query(raw: str) -> str:
    """Collapse whitespace and reject an empty query.

    Raises:
        ValueError: if `raw` is empty or whitespace-only.
    """
    cleaned = " ".join(raw.split())
    if not cleaned:
        raise ValueError("search query must not be empty")
    return cleaned


def build_tsquery(raw: str) -> Function:
    """Build a websearch_to_tsquery() SQL expression from raw user input."""
    return func.websearch_to_tsquery(_SEARCH_CONFIG, sanitize_query(raw))
