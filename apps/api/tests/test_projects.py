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

    async def test_case_variant_name_rejected(self, client, org_with_admin, db_session):
        """Capitalization alone must never be treated as a distinct project."""
        db_session.add(Project(org_id=org_with_admin["org"].org_id, name="Acme Corp"))
        await db_session.commit()

        token = await _login(client, "admin@projecttest.com")
        response = await client.post(
            f"/api/v1/projects?org_id={org_with_admin['org'].org_id}",
            json={"name": "ACME CORP"},
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 409

    async def test_fuzzy_near_duplicate_name_rejected(self, client, org_with_admin, db_session):
        db_session.add(Project(org_id=org_with_admin["org"].org_id, name="Acme Cloud Migration"))
        await db_session.commit()

        token = await _login(client, "admin@projecttest.com")
        response = await client.post(
            f"/api/v1/projects?org_id={org_with_admin['org'].org_id}",
            json={"name": "Acme Cloud Migration."},
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 409

    async def test_company_type_suffix_ignored(self, client, org_with_admin, db_session):
        """Corp/Ltd/LLP/Technologies/Tech etc. are company-type descriptors,
        not part of the distinctive name -- "Acme Corporation" and "Acme
        Ltd" are the same project."""
        db_session.add(Project(org_id=org_with_admin["org"].org_id, name="Acme Corporation"))
        await db_session.commit()

        token = await _login(client, "admin@projecttest.com")
        response = await client.post(
            f"/api/v1/projects?org_id={org_with_admin['org'].org_id}",
            json={"name": "Acme Ltd"},
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 409

    async def test_tech_technologies_treated_as_same_suffix(self, client, org_with_admin, db_session):
        db_session.add(Project(org_id=org_with_admin["org"].org_id, name="ABC Technologies"))
        await db_session.commit()

        token = await _login(client, "admin@projecttest.com")
        response = await client.post(
            f"/api/v1/projects?org_id={org_with_admin['org'].org_id}",
            json={"name": "ABC Tech"},
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 409

    async def test_distinct_name_not_rejected(self, client, org_with_admin, db_session):
        db_session.add(Project(org_id=org_with_admin["org"].org_id, name="Acme Corp"))
        await db_session.commit()

        token = await _login(client, "admin@projecttest.com")
        response = await client.post(
            f"/api/v1/projects?org_id={org_with_admin['org'].org_id}",
            json={"name": "Globex Corp"},
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 201


class TestNormalizeProjectName:
    def test_company_suffix_stripped(self):
        from app.routers.projects import _normalize_project_name

        assert _normalize_project_name("Acme Corporation") == "acme"
        assert _normalize_project_name("Acme Ltd") == "acme"
        assert _normalize_project_name("ABC Technologies") == "abc"
        assert _normalize_project_name("ABC Tech") == "abc"

    def test_name_entirely_suffix_falls_back_to_full_name(self):
        """Stripping shouldn't eat the whole name -- a project literally
        named "Technologies" must not become empty (which would otherwise
        match every other all-suffix name)."""
        from app.routers.projects import _normalize_project_name

        assert _normalize_project_name("Technologies") == "technologies"


class TestGetOrCreateProjectMatching:
    async def test_case_variant_reuses_existing_project(self, org_with_admin, db_session):
        from app.routers.projects import get_or_create_project

        org = org_with_admin["org"]
        existing = Project(org_id=org.org_id, name="Acme Corp")
        db_session.add(existing)
        await db_session.commit()

        project = await get_or_create_project(db_session, org.org_id, "acme corp")
        await db_session.commit()

        assert project.project_id == existing.project_id

    async def test_fuzzy_match_reuses_existing_project(self, org_with_admin, db_session):
        from app.routers.projects import get_or_create_project

        org = org_with_admin["org"]
        existing = Project(org_id=org.org_id, name="Acme Cloud Migration")
        db_session.add(existing)
        await db_session.commit()

        project = await get_or_create_project(db_session, org.org_id, "Acme Cloud Migration.")
        await db_session.commit()

        assert project.project_id == existing.project_id

    async def test_distinct_name_creates_new_project(self, org_with_admin, db_session):
        from app.routers.projects import get_or_create_project

        org = org_with_admin["org"]
        existing = Project(org_id=org.org_id, name="Acme Corp")
        db_session.add(existing)
        await db_session.commit()

        project = await get_or_create_project(db_session, org.org_id, "Totally Different Name")
        await db_session.commit()

        assert project.project_id != existing.project_id


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
