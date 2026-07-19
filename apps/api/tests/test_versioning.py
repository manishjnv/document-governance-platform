"""Tests for document versioning (Phase B of Document Lifecycle plan):
similarity-suggestion generation, accept/dismiss, and the retroactive
"link to existing document" action. Upload-new-version's HTTP path reuses
the same storage/parsing code already exercised by test_documents.py, so
it isn't re-tested at the HTTP layer here -- these tests target the new
logic (suggestion generation, group-linking) directly.
"""

from datetime import datetime, timezone

import pytest
from httpx import ASGITransport, AsyncClient

from app.auth import hash_password
from app.insights.similarity import _normalized_filename, filename_similarity, suggest_version_link
from app.models.document import Document
from app.models.document_link_suggestion import DocumentLinkSuggestion
from app.models.organization import Organization
from app.models.user import User
from main import app


@pytest.fixture
async def client():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as c:
        yield c


@pytest.fixture
async def org_with_admin(db_session):
    org = Organization(name="Version Test Org", subscription_tier="enterprise")
    db_session.add(org)
    await db_session.flush()

    admin = User(
        org_id=org.org_id, email="admin@versiontest.com",
        password_hash=hash_password("password123"), role="admin", is_active=True,
    )
    db_session.add(admin)
    await db_session.commit()
    return {"org": org, "admin": admin}


async def _login(client, email, password="password123"):
    response = await client.post("/api/v1/auth/login", json={"email": email, "password": password})
    return response.json()["access_token"]


def _make_doc(org, admin, filename, parsed_text, version=1, group_id=None):
    kwargs = dict(
        org_id=org.org_id,
        uploaded_by_user_id=admin.user_id,
        filename=filename,
        original_filename=filename,
        file_size_bytes=1024,
        file_type="pdf",
        s3_path=f"s3://bucket/{filename}",
        version=version,
        parsed_text=parsed_text,
    )
    if group_id is not None:
        kwargs["document_group_id"] = group_id
    return Document(**kwargs)


class TestFilenameSimilarity:
    def test_version_suffix_stripped(self):
        assert _normalized_filename("Acme_SOW_v2.pdf") == _normalized_filename("Acme_SOW_v3.pdf")

    def test_similar_names_score_high(self):
        assert filename_similarity("Acme SOW (revised).pdf", "Acme SOW.pdf") > 0.9

    def test_unrelated_names_score_low(self):
        assert filename_similarity("Acme SOW.pdf", "Totally Different Contract.pdf") < 0.5


class TestSuggestVersionLink:
    async def test_similar_text_generates_suggestion(self, db_session, org_with_admin):
        org, admin = org_with_admin["org"], org_with_admin["admin"]
        shared_text = "This Statement of Work covers cloud migration services. " * 20

        existing = _make_doc(org, admin, "sow.pdf", shared_text)
        db_session.add(existing)
        await db_session.flush()

        new_doc = _make_doc(org, admin, "sow_v2.pdf", shared_text)
        db_session.add(new_doc)
        await db_session.flush()

        suggestion = await suggest_version_link(db_session, org.org_id, new_doc)
        await db_session.commit()

        assert suggestion is not None
        assert suggestion.doc_id == new_doc.doc_id
        assert suggestion.suggested_doc_id == existing.doc_id
        assert suggestion.status == "pending"

    async def test_dissimilar_documents_no_suggestion(self, db_session, org_with_admin):
        org, admin = org_with_admin["org"], org_with_admin["admin"]

        existing = _make_doc(org, admin, "security_policy.pdf", "Access control and encryption standards.")
        db_session.add(existing)
        await db_session.flush()

        new_doc = _make_doc(org, admin, "invoice.pdf", "Payment due within thirty days of receipt.")
        db_session.add(new_doc)
        await db_session.flush()

        suggestion = await suggest_version_link(db_session, org.org_id, new_doc)
        assert suggestion is None


class TestResolveLinkSuggestion:
    async def test_accept_links_document_into_group(self, client, db_session, org_with_admin):
        org, admin = org_with_admin["org"], org_with_admin["admin"]

        existing = _make_doc(org, admin, "sow.pdf", "shared text")
        db_session.add(existing)
        await db_session.flush()

        new_doc = _make_doc(org, admin, "sow_v2.pdf", "shared text")
        db_session.add(new_doc)
        await db_session.flush()

        suggestion = DocumentLinkSuggestion(
            org_id=org.org_id,
            doc_id=new_doc.doc_id,
            suggested_doc_id=existing.doc_id,
            similarity_score="0.9000",
            status="pending",
        )
        db_session.add(suggestion)
        await db_session.commit()

        token = await _login(client, "admin@versiontest.com")
        response = await client.patch(
            f"/api/v1/documents/suggestions/{suggestion.suggestion_id}",
            json={"action": "accept"},
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 200
        assert response.json()["new_version"] == 2

        await db_session.refresh(new_doc)
        assert new_doc.document_group_id == existing.document_group_id
        assert new_doc.version == 2

    async def test_dismiss_leaves_document_unlinked(self, client, db_session, org_with_admin):
        org, admin = org_with_admin["org"], org_with_admin["admin"]

        existing = _make_doc(org, admin, "sow.pdf", "shared text")
        db_session.add(existing)
        await db_session.flush()
        new_doc = _make_doc(org, admin, "sow_v2.pdf", "shared text")
        db_session.add(new_doc)
        await db_session.flush()
        original_group_id = new_doc.document_group_id

        suggestion = DocumentLinkSuggestion(
            org_id=org.org_id,
            doc_id=new_doc.doc_id,
            suggested_doc_id=existing.doc_id,
            similarity_score="0.9000",
            status="pending",
        )
        db_session.add(suggestion)
        await db_session.commit()

        token = await _login(client, "admin@versiontest.com")
        response = await client.patch(
            f"/api/v1/documents/suggestions/{suggestion.suggestion_id}",
            json={"action": "dismiss"},
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 200

        await db_session.refresh(new_doc)
        assert new_doc.document_group_id == original_group_id


class TestRetroactiveLink:
    async def test_link_document_endpoint(self, client, db_session, org_with_admin):
        org, admin = org_with_admin["org"], org_with_admin["admin"]

        target = _make_doc(org, admin, "sow.pdf", "text")
        db_session.add(target)
        await db_session.flush()
        standalone = _make_doc(org, admin, "unrelated_upload.pdf", "other text")
        db_session.add(standalone)
        await db_session.commit()

        token = await _login(client, "admin@versiontest.com")
        response = await client.post(
            f"/api/v1/documents/{standalone.doc_id}/link",
            json={"target_doc_id": str(target.doc_id)},
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 200
        body = response.json()
        assert body["document_group_id"] == str(target.document_group_id)
        assert body["version"] == 2
