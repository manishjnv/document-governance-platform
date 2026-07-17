"""Tests for document upload/delete security fixes (2026-07-17 audit):
- viewer role cannot delete documents (was previously unrestricted)
- uploaded filenames are sanitized before building the S3/local storage key
"""

import pytest
from httpx import ASGITransport, AsyncClient

from app.auth import hash_password
from app.models.document import Document
from app.models.organization import Organization
from app.models.user import User
from app.routers.documents import _sanitize_filename
from main import app


@pytest.fixture
async def client():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as c:
        yield c


@pytest.fixture
async def org_with_users(db_session):
    org = Organization(name="Doc Test Org", subscription_tier="enterprise")
    db_session.add(org)
    await db_session.flush()

    admin = User(
        org_id=org.org_id, email="admin@doctest.com",
        password_hash=hash_password("password123"), role="admin", is_active=True,
    )
    viewer = User(
        org_id=org.org_id, email="viewer@doctest.com",
        password_hash=hash_password("password123"), role="viewer", is_active=True,
    )
    db_session.add_all([admin, viewer])
    await db_session.flush()

    doc = Document(
        org_id=org.org_id,
        uploaded_by_user_id=admin.user_id,
        filename="report.pdf",
        original_filename="report.pdf",
        file_size_bytes=1024,
        file_type="pdf",
        s3_path="s3://bucket/report.pdf",
        document_type="SOW",
    )
    db_session.add(doc)
    await db_session.commit()
    await db_session.refresh(admin)
    await db_session.refresh(viewer)
    await db_session.refresh(doc)

    return {"org": org, "admin": admin, "viewer": viewer, "doc": doc}


async def _login(client, email, password="password123"):
    response = await client.post("/api/v1/auth/login", json={"email": email, "password": password})
    return response.json()["access_token"]


class TestDeleteDocumentRBAC:
    async def test_viewer_cannot_delete_document(self, client, org_with_users):
        token = await _login(client, "viewer@doctest.com")
        response = await client.delete(
            f"/api/v1/documents/{org_with_users['doc'].doc_id}",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 403

    async def test_admin_can_delete_document(self, client, org_with_users):
        token = await _login(client, "admin@doctest.com")
        response = await client.delete(
            f"/api/v1/documents/{org_with_users['doc'].doc_id}",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 204


class TestFilenameSanitization:
    def test_strips_path_traversal(self):
        assert _sanitize_filename("../../etc/passwd") == "passwd"

    def test_strips_absolute_path(self):
        assert _sanitize_filename("/etc/passwd") == "passwd"

    def test_strips_windows_path(self):
        assert _sanitize_filename("C:\\Windows\\System32\\evil.pdf") == "evil.pdf"

    def test_replaces_special_characters(self):
        assert _sanitize_filename("my file (final)!.pdf") == "my_file__final__.pdf"

    def test_preserves_safe_filename(self):
        assert _sanitize_filename("Statement_of_Work-v2.pdf") == "Statement_of_Work-v2.pdf"

    def test_empty_or_none_falls_back(self):
        assert _sanitize_filename("") == "document"
        assert _sanitize_filename(None) == "document"

    def test_leading_dots_stripped(self):
        """A bare "..pdf" or ".env"-style name shouldn't survive as a
        leading-dot (hidden-file-style) name in the storage key."""
        assert not _sanitize_filename("..pdf").startswith(".")
