"""Tests that project is mandatory on upload (either an existing project_id
or a project_name that creates one) and that a document can be retroactively
tagged into a project via PATCH /{doc_id}/project.
"""

import pytest
from httpx import ASGITransport, AsyncClient

from app.auth import hash_password
from app.models.document import Document
from app.models.organization import Organization
from app.models.project import Project
from app.models.user import User
from main import app


@pytest.fixture
async def client():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as c:
        yield c


@pytest.fixture
async def org_with_admin(db_session):
    org = Organization(name="Upload Project Test Org", subscription_tier="enterprise")
    db_session.add(org)
    await db_session.flush()

    admin = User(
        org_id=org.org_id, email="admin@uploadprojecttest.com",
        password_hash=hash_password("password123"), role="admin", is_active=True,
    )
    db_session.add(admin)
    await db_session.commit()
    return {"org": org, "admin": admin}


async def _login(client, email, password="password123"):
    response = await client.post("/api/v1/auth/login", json={"email": email, "password": password})
    return response.json()["access_token"]


class TestUploadRequiresProject:
    async def test_upload_without_project_rejected(self, client, org_with_admin):
        token = await _login(client, "admin@uploadprojecttest.com")
        response = await client.post(
            f"/api/v1/documents/upload?org_id={org_with_admin['org'].org_id}",
            files={"file": ("sow.pdf", b"%PDF-1.4 fake", "application/pdf")},
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 422
        assert "project" in response.json()["detail"].lower()

    async def test_upload_with_project_name_succeeds(self, client, org_with_admin):
        token = await _login(client, "admin@uploadprojecttest.com")
        response = await client.post(
            f"/api/v1/documents/upload?org_id={org_with_admin['org'].org_id}&project_name=New+Project",
            files={"file": ("sow.pdf", b"%PDF-1.4 fake", "application/pdf")},
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 202
        assert response.json()["project_id"] is not None

    async def test_upload_with_blank_project_name_rejected(self, client, org_with_admin):
        token = await _login(client, "admin@uploadprojecttest.com")
        response = await client.post(
            f"/api/v1/documents/upload?org_id={org_with_admin['org'].org_id}&project_name=%20%20",
            files={"file": ("sow.pdf", b"%PDF-1.4 fake", "application/pdf")},
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 422


class TestRetroactiveProjectTag:
    async def test_tag_document_with_existing_project(self, client, db_session, org_with_admin):
        org, admin = org_with_admin["org"], org_with_admin["admin"]
        project = Project(org_id=org.org_id, name="Existing Project")
        db_session.add(project)
        await db_session.flush()

        doc = Document(
            org_id=org.org_id, uploaded_by_user_id=admin.user_id,
            filename="orphan.pdf", original_filename="orphan.pdf", file_size_bytes=1024,
            file_type="pdf", s3_path="s3://bucket/orphan.pdf",
        )
        db_session.add(doc)
        await db_session.commit()
        assert doc.project_id is None

        token = await _login(client, "admin@uploadprojecttest.com")
        response = await client.patch(
            f"/api/v1/documents/{doc.doc_id}/project?project_id={project.project_id}",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 200
        assert response.json()["project_id"] == str(project.project_id)

    async def test_tag_document_missing_project_rejected(self, client, db_session, org_with_admin):
        org, admin = org_with_admin["org"], org_with_admin["admin"]
        doc = Document(
            org_id=org.org_id, uploaded_by_user_id=admin.user_id,
            filename="orphan2.pdf", original_filename="orphan2.pdf", file_size_bytes=1024,
            file_type="pdf", s3_path="s3://bucket/orphan2.pdf",
        )
        db_session.add(doc)
        await db_session.commit()

        token = await _login(client, "admin@uploadprojecttest.com")
        response = await client.patch(
            f"/api/v1/documents/{doc.doc_id}/project",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 422
