"""Tests for the Project API (Phase A of Document Lifecycle plan)."""

import pytest
from httpx import ASGITransport, AsyncClient

from app.auth import hash_password
from app.models.document import Document
from app.models.organization import Organization
from app.models.project import Project
from app.models.review import Review
from app.models.user import User
from main import app
from datetime import datetime, timezone


@pytest.fixture
async def client():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as c:
        yield c


@pytest.fixture
async def org_with_admin(db_session):
    org = Organization(name="Project Test Org", subscription_tier="enterprise")
    db_session.add(org)
    await db_session.flush()

    admin = User(
        org_id=org.org_id, email="admin@projecttest.com",
        password_hash=hash_password("password123"), role="admin", is_active=True,
    )
    db_session.add(admin)
    await db_session.commit()
    return {"org": org, "admin": admin}


async def _login(client, email, password="password123"):
    response = await client.post("/api/v1/auth/login", json={"email": email, "password": password})
    return response.json()["access_token"]


class TestCreateProject:
    async def test_create_project(self, client, org_with_admin):
        token = await _login(client, "admin@projecttest.com")
        response = await client.post(
            f"/api/v1/projects?org_id={org_with_admin['org'].org_id}",
            json={"name": "Acme Migration"},
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 201
        body = response.json()
        assert body["name"] == "Acme Migration"
        assert body["document_count"] == 0

    async def test_duplicate_name_rejected(self, client, org_with_admin, db_session):
        db_session.add(Project(org_id=org_with_admin["org"].org_id, name="Dup Project"))
        await db_session.commit()

        token = await _login(client, "admin@projecttest.com")
        response = await client.post(
            f"/api/v1/projects?org_id={org_with_admin['org'].org_id}",
            json={"name": "Dup Project"},
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 409


class TestListProjectsRollup:
    async def test_rollup_stats(self, client, org_with_admin, db_session):
        org = org_with_admin["org"]
        project = Project(org_id=org.org_id, name="Rollup Project")
        db_session.add(project)
        await db_session.flush()

        doc = Document(
            org_id=org.org_id,
            uploaded_by_user_id=org_with_admin["admin"].user_id,
            project_id=project.project_id,
            filename="sow.pdf",
            original_filename="sow.pdf",
            file_size_bytes=1024,
            file_type="pdf",
            s3_path="s3://bucket/sow.pdf",
        )
        db_session.add(doc)
        await db_session.flush()

        review = Review(
            org_id=org.org_id,
            doc_id=doc.doc_id,
            status="completed",
            overall_score=72.5,
            completed_at=datetime.now(timezone.utc),
        )
        db_session.add(review)
        await db_session.commit()

        token = await _login(client, "admin@projecttest.com")
        response = await client.get(
            f"/api/v1/projects?org_id={org.org_id}",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 200
        rollup = next(p for p in response.json() if p["name"] == "Rollup Project")
        assert rollup["document_count"] == 1
        assert rollup["average_latest_score"] == 72.5
