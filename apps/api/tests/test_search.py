"""Tests for T-2001-T-2003 full-text document search.

Unit tests cover the pure-logic tsquery helpers (app.search.indexer) --
no DB needed. The acceptance-scenario test needs real PostgreSQL:
websearch_to_tsquery/ts_rank/ts_headline/GIN aren't available on the
SQLite in-memory `test_db` fixture used elsewhere in this suite (see
conftest.py), so it's marked @pytest.mark.integration and self-skips
if Postgres isn't reachable at settings.database_url.
"""

from __future__ import annotations

import uuid

import pytest

from app.search.indexer import build_tsquery, sanitize_query


class TestSanitizeQuery:
    """T-2001: pure-logic whitespace/empty-query handling."""

    def test_collapses_whitespace(self):
        assert sanitize_query("  hello   world  ") == "hello world"

    def test_rejects_empty(self):
        with pytest.raises(ValueError):
            sanitize_query("")

    def test_rejects_whitespace_only(self):
        with pytest.raises(ValueError):
            sanitize_query("   \t\n  ")


class TestBuildTsquery:
    """T-2001: build_tsquery wraps websearch_to_tsquery() with sanitized input."""

    def test_builds_websearch_to_tsquery_call(self):
        expr = build_tsquery("  payment   terms ")
        compiled = expr.compile()
        assert "websearch_to_tsquery" in str(compiled)
        assert "payment terms" in compiled.params.values()

    def test_propagates_empty_query_error(self):
        with pytest.raises(ValueError):
            build_tsquery("   ")


@pytest.mark.integration
@pytest.mark.asyncio
async def test_search_scoped_to_org_and_ranked():
    """Acceptance test (T-2001/T-2002/T-2003): 3 documents in org A (2
    contain the keyword, 1 doesn't) plus a 4th document in a different
    org that also contains the keyword. Searching org A returns exactly
    the 2 same-org matches, ranked, and never org B's document.
    """
    import os

    from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

    from app.models.document import Document
    from app.models.organization import Organization
    from app.models.user import User
    from app.search.engine import search_documents

    # Use the disposable test database (already schema-migrated by
    # migrations/*.sql — see conftest.py), never settings.database_url (the
    # real dev DB): this test used to create_all()/drop_all() tables=[...]
    # against dev, and drop_all() on `documents` failed loudly at teardown
    # only because other dev tables (reviews, comments, findings) FK-reference
    # it — a near-miss that would otherwise have dropped real dev tables out
    # from under every other test/manual run sharing that database.
    test_database_url = os.getenv(
        "TEST_DATABASE_URL",
        "postgresql+asyncpg://edgp_user:edgp_password@localhost:5432/edgp_test",
    )
    try:
        engine = create_async_engine(test_database_url)
        async with engine.connect():
            pass
    except Exception as exc:
        pytest.skip(f"PostgreSQL not reachable at {test_database_url}: {exc}")

    session_factory = async_sessionmaker(engine, expire_on_commit=False)

    def make_doc(org: Organization, filename: str, text: str) -> Document:
        return Document(
            doc_id=uuid.uuid4(),
            org_id=org.org_id,
            filename=filename,
            original_filename=filename,
            file_size_bytes=100,
            file_type="pdf",
            s3_path=f"s3://bucket/{uuid.uuid4()}",
            version=1,
            parsed_text=text,
            document_type="SOW",
        )

    try:
        async with session_factory() as db:
            org_a = Organization(org_id=uuid.uuid4(), name=f"Org A {uuid.uuid4()}")
            org_b = Organization(org_id=uuid.uuid4(), name=f"Org B {uuid.uuid4()}")
            db.add_all([org_a, org_b])
            await db.flush()

            match_1 = make_doc(
                org_a, "contract1.pdf", "This agreement covers indemnification clauses."
            )
            match_2 = make_doc(
                org_a, "contract2.pdf", "Indemnification terms are defined in section 4."
            )
            no_match = make_doc(
                org_a, "contract3.pdf", "This document has nothing relevant in it."
            )
            other_org_match = make_doc(
                org_b, "contract4.pdf", "Indemnification obligations apply here too."
            )

            db.add_all([match_1, match_2, no_match, other_org_match])
            await db.commit()

            results, total = await search_documents(db, org_a.org_id, "indemnification")

            assert total == 2
            result_ids = {r["doc_id"] for r in results}
            assert result_ids == {str(match_1.doc_id), str(match_2.doc_id)}
            assert str(other_org_match.doc_id) not in result_ids
            assert str(no_match.doc_id) not in result_ids

            # Ranked: non-increasing rank order.
            ranks = [r["rank"] for r in results]
            assert ranks == sorted(ranks, reverse=True)
    finally:
        # Delete only the rows this test inserted (org_a/org_b cascade to
        # their documents) -- never touch table structure on a database
        # other tests/fixtures/manual runs share.
        async with session_factory() as cleanup_db:
            for org in (org_a, org_b):
                await cleanup_db.delete(await cleanup_db.get(Organization, org.org_id))
            await cleanup_db.commit()
        await engine.dispose()
