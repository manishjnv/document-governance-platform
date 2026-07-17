"""Tests for document similarity (T-2026), duplicate detection (T-2027),
and version history/diff (T-2028, T-2029).

Similarity/duplicate functions are plain async functions and are tested
directly against `db_session` (conftest.py's real-Postgres, TRUNCATE-isolated
fixture). Versions/changes are tested at the HTTP layer, but through a
standalone FastAPI app wrapping just `documents_extra.router` rather than
`from main import app` -- documents_extra.router isn't wired into main.py yet
(main.py is off limits for this task; see the ponytail note atop
app/routers/documents_extra.py), so the real app wouldn't route these paths.
Wrapping the router directly still drives the real dependency chain
(get_db/get_current_user overridden), matching the httpx.AsyncClient +
ASGITransport pattern used elsewhere in this suite (see test_auth.py) rather
than the sync TestClient, which breaks across event loops.
"""

import uuid
from datetime import datetime, timedelta, timezone

import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient

import app.models.kb_article  # noqa: F401 -- registers KBArticle for SQLAlchemy's
# mapper configure step. Organization.kb_articles (another Wave-2 task, not this
# one) declares a string-referenced relationship("KBArticle") but
# app/models/__init__.py doesn't import it yet, so any DB-backed test in this
# process blows up in mapper configuration without this. Remove once
# app/models/__init__.py imports KBArticle itself (out of scope here --
# app/models/__init__.py is off limits for this task).
from app.db.session import get_db
from app.dependencies import get_current_user
from app.insights.similarity import compute_similarity, find_duplicates, find_similar_documents
from app.models.document import Document
from app.models.organization import Organization
from app.models.user import User
from app.routers.documents_extra import router as documents_extra_router
from app.schemas.auth import TokenData


def _make_doc(
    org_id: uuid.UUID,
    document_group_id: uuid.UUID | None = None,
    version: int = 1,
    parsed_text: str = "",
    filename: str = "doc.pdf",
) -> Document:
    return Document(
        doc_id=uuid.uuid4(),
        document_group_id=document_group_id or uuid.uuid4(),
        org_id=org_id,
        filename=filename,
        original_filename=filename,
        file_size_bytes=1024,
        file_type="pdf",
        s3_path=f"s3://bucket/{filename}",
        version=version,
        parsed_text=parsed_text,
    )


class TestComputeSimilarity:
    """Unit tests, no DB."""

    def test_identical_text_is_near_one(self):
        text = "the quick brown fox jumps over the lazy dog"
        assert compute_similarity(text, text) == pytest.approx(1.0)

    def test_unrelated_text_is_low(self):
        a = "payment terms net thirty days invoice schedule"
        b = "server rack cooling temperature humidity sensor"
        assert compute_similarity(a, b) < 0.2

    def test_empty_text_is_zero(self):
        assert compute_similarity("", "something") == 0.0
        assert compute_similarity("something", "") == 0.0
        assert compute_similarity("   ", "something here") == 0.0


class TestFindSimilarDocuments:
    async def test_finds_similar_above_threshold_excludes_unrelated_and_self(self, db_session):
        org = Organization(name="Org A")
        db_session.add(org)
        await db_session.flush()

        base_text = "scope of work includes design development testing deployment support"
        target = _make_doc(org.org_id, parsed_text=base_text, filename="target.pdf")
        similar = _make_doc(
            org.org_id,
            parsed_text="scope of work includes design development testing deployment",
            filename="similar.pdf",
        )
        unrelated = _make_doc(
            org.org_id,
            parsed_text="quarterly financial report revenue expenses forecast",
            filename="unrelated.pdf",
        )
        db_session.add_all([target, similar, unrelated])
        await db_session.commit()

        results = await find_similar_documents(
            db_session, org.org_id, target.doc_id, threshold=0.5
        )

        doc_ids = {r["doc_id"] for r in results}
        assert str(similar.doc_id) in doc_ids
        assert str(unrelated.doc_id) not in doc_ids
        assert str(target.doc_id) not in doc_ids  # never includes itself
        assert results == sorted(results, key=lambda r: r["similarity"], reverse=True)

    async def test_org_scoped(self, db_session):
        org_a = Organization(name="Org A")
        org_b = Organization(name="Org B")
        db_session.add_all([org_a, org_b])
        await db_session.flush()

        text = "identical shared boilerplate contract language for testing purposes"
        target = _make_doc(org_a.org_id, parsed_text=text, filename="a.pdf")
        other_org_doc = _make_doc(org_b.org_id, parsed_text=text, filename="b.pdf")
        db_session.add_all([target, other_org_doc])
        await db_session.commit()

        results = await find_similar_documents(
            db_session, org_a.org_id, target.doc_id, threshold=0.5
        )
        assert results == []  # other org's identical-text doc never surfaces


class TestFindDuplicates:
    async def test_finds_near_identical_pair_not_unrelated(self, db_session):
        org = Organization(name="Org A")
        db_session.add(org)
        await db_session.flush()

        text = "master services agreement effective date parties obligations liability"
        doc_a = _make_doc(org.org_id, parsed_text=text, filename="msa_v1.pdf")
        # one extra word keeps cosine similarity > 0.9 (8 shared / sqrt(8)*sqrt(9) ~= 0.94)
        doc_b = _make_doc(org.org_id, parsed_text=text + " final", filename="msa_v2.pdf")
        doc_c = _make_doc(
            org.org_id,
            parsed_text="unrelated recipe ingredients cooking instructions",
            filename="recipe.pdf",
        )
        db_session.add_all([doc_a, doc_b, doc_c])
        await db_session.commit()

        pairs = await find_duplicates(db_session, org.org_id, threshold=0.9)

        pair_id_sets = [frozenset((p["doc_id_a"], p["doc_id_b"])) for p in pairs]
        assert frozenset((str(doc_a.doc_id), str(doc_b.doc_id))) in pair_id_sets
        for p in pairs:
            assert str(doc_c.doc_id) not in (p["doc_id_a"], p["doc_id_b"])
        assert len(pair_id_sets) == len(set(pair_id_sets))  # each pair appears once


def _token(org_id: uuid.UUID, user_id: uuid.UUID) -> TokenData:
    now = datetime.now(timezone.utc)
    return TokenData(
        user_id=user_id,
        email="user@example.com",
        org_id=org_id,
        role="admin",
        exp=now + timedelta(hours=1),
        iat=now,
        type="access",
    )


def _make_client(db_session, org_id: uuid.UUID, user_id: uuid.UUID) -> AsyncClient:
    app = FastAPI()
    app.include_router(documents_extra_router)

    async def _override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = _override_get_db
    app.dependency_overrides[get_current_user] = lambda: _token(org_id, user_id)

    return AsyncClient(transport=ASGITransport(app=app), base_url="http://testserver")


class TestVersionsAndChanges:
    async def test_versions_newest_first_and_changes_diff(self, db_session):
        org = Organization(name="Org A")
        db_session.add(org)
        await db_session.flush()
        user = User(org_id=org.org_id, email="u@example.com")
        db_session.add(user)
        await db_session.flush()

        group_id = uuid.uuid4()
        v1 = _make_doc(
            org.org_id,
            document_group_id=group_id,
            version=1,
            parsed_text="line one\nline two\nline three",
            filename="doc_v1.pdf",
        )
        v2 = _make_doc(
            org.org_id,
            document_group_id=group_id,
            version=2,
            parsed_text="line one\nline three\nline four",
            filename="doc_v2.pdf",
        )
        db_session.add_all([v1, v2])
        await db_session.commit()

        async with _make_client(db_session, org.org_id, user.user_id) as client:
            resp = await client.get(f"/api/v1/documents/{v2.doc_id}/versions")
            assert resp.status_code == 200
            versions = resp.json()
            assert [v["version"] for v in versions] == [2, 1]
            assert {v["doc_id"] for v in versions} == {str(v1.doc_id), str(v2.doc_id)}

            resp = await client.get(f"/api/v1/documents/{v2.doc_id}/versions/1/changes")
            assert resp.status_code == 200
            changes = resp.json()
            assert changes["doc_a_version"] == 2
            assert changes["doc_b_version"] == 1
            # going from v2 to v1: "line four" disappears, "line two" reappears
            assert "line four" in changes["removed"]
            assert "line two" in changes["added"]

    async def test_versions_and_changes_never_cross_orgs(self, db_session):
        org_a = Organization(name="Org A")
        org_b = Organization(name="Org B")
        db_session.add_all([org_a, org_b])
        await db_session.flush()
        user_a = User(org_id=org_a.org_id, email="a@example.com")
        db_session.add(user_a)
        await db_session.flush()

        group_id = uuid.uuid4()
        doc_a = _make_doc(
            org_a.org_id, document_group_id=group_id, version=1, parsed_text="a", filename="a.pdf"
        )
        doc_b = _make_doc(
            org_b.org_id, document_group_id=group_id, version=2, parsed_text="b", filename="b.pdf"
        )
        db_session.add_all([doc_a, doc_b])
        await db_session.commit()

        async with _make_client(db_session, org_a.org_id, user_a.user_id) as client:
            # org_a's own doc: versions list must not include org_b's row,
            # even though it shares document_group_id.
            resp = await client.get(f"/api/v1/documents/{doc_a.doc_id}/versions")
            assert resp.status_code == 200
            versions = resp.json()
            assert len(versions) == 1
            assert versions[0]["doc_id"] == str(doc_a.doc_id)

            # org_b's doc_id isn't resolvable at all as org_a.
            resp = await client.get(f"/api/v1/documents/{doc_b.doc_id}/versions")
            assert resp.status_code == 404

            # can't diff against a version that only exists in another org.
            resp = await client.get(f"/api/v1/documents/{doc_a.doc_id}/versions/2/changes")
            assert resp.status_code == 404
