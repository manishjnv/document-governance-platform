"""Tests for admin operations: usage metrics, suspension, bulk import.

T-2084: Usage metrics
T-2088: User suspension/reactivation
T-2090: Bulk user import
"""

from datetime import datetime, timedelta

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.admin.usage import get_org_usage_metrics
from app.admin.user_lifecycle import (
    LastActiveAdminError,
    bulk_import_users,
    reactivate_user,
    suspend_user,
)
from app.auth import hash_password
from app.models.document import Document
from app.models.finding import Finding
from app.models.organization import Organization
from app.models.review import Review
from app.models.user import User
from main import app

ADMIN_EMAIL = "admin@example.com"
ADMIN_PASSWORD = "password123"


@pytest.fixture
async def client():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as c:
        yield c


@pytest.fixture
async def seeded_org_with_admin(db_session):
    """Create an org with one admin user."""
    org = Organization(name="Test Org", subscription_tier="enterprise")
    db_session.add(org)
    await db_session.flush()

    admin = User(
        org_id=org.org_id,
        email=ADMIN_EMAIL,
        password_hash=hash_password(ADMIN_PASSWORD),
        full_name="Admin User",
        role="admin",
        is_active=True,
    )
    db_session.add(admin)
    await db_session.commit()
    await db_session.refresh(admin)
    await db_session.refresh(org)

    return org, admin


class TestUsageMetrics:
    """Usage metrics endpoint and underlying function tests."""

    async def test_get_org_usage_metrics_empty_org(self, db_session, seeded_org_with_admin):
        """Empty org should return all zeros."""
        org, _ = seeded_org_with_admin
        metrics = await get_org_usage_metrics(db_session, org.org_id, months=1)

        assert metrics["documents_uploaded"] == 0
        assert metrics["reviews_run"] == 0
        assert metrics["findings_by_severity"] == {
            "critical": 0,
            "major": 0,
            "medium": 0,
            "low": 0,
            "info": 0,
        }
        assert metrics["total_storage_bytes"] == 0

    async def test_get_org_usage_metrics_with_data(self, db_session, seeded_org_with_admin):
        """Test metrics with actual data."""
        org, admin = seeded_org_with_admin
        now = datetime.utcnow()

        # Create document (within window)
        doc = Document(
            org_id=org.org_id,
            filename="test.pdf",
            original_filename="test.pdf",
            file_size_bytes=5000,
            file_type="pdf",
            s3_path="s3://bucket/test.pdf",
        )
        db_session.add(doc)
        await db_session.flush()

        # Create review (within window, completed)
        review = Review(
            org_id=org.org_id,
            doc_id=doc.doc_id,
            triggered_by_user_id=admin.user_id,
            status="completed",
            completed_at=now,
            critical_finding_count=1,
            major_finding_count=2,
        )
        db_session.add(review)
        await db_session.flush()

        # Create findings
        critical_finding = Finding(
            org_id=org.org_id,
            review_id=review.review_id,
            finding_source="agent",
            agent_name="test_agent",
            category="test",
            title="Critical Issue",
            description="Critical issue desc",
            severity="critical",
            recommendation="Fix it",
        )
        major_finding = Finding(
            org_id=org.org_id,
            review_id=review.review_id,
            finding_source="rule",
            rule_id="rule_1",
            category="test",
            title="Major Issue",
            description="Major issue desc",
            severity="major",
            recommendation="Fix it",
        )
        db_session.add_all([critical_finding, major_finding])
        await db_session.commit()

        metrics = await get_org_usage_metrics(db_session, org.org_id, months=1)

        assert metrics["documents_uploaded"] == 1
        assert metrics["reviews_run"] == 1
        assert metrics["findings_by_severity"]["critical"] == 1
        assert metrics["findings_by_severity"]["major"] == 1
        assert metrics["total_storage_bytes"] == 5000

    async def test_usage_metrics_endpoint_requires_admin(self, client, seeded_org_with_admin):
        """Non-admin should get 403."""
        org, _ = seeded_org_with_admin

        # Create non-admin user
        response = await client.post(
            "/api/v1/auth/login",
            json={"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD},
        )
        admin_token = response.json()["access_token"]

        # Now test with admin (should work)
        response = await client.get(
            "/api/v1/admin/usage?months=1",
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert response.status_code == 200

    async def test_usage_metrics_endpoint_unauthenticated(self, client):
        """Unauthenticated request should get 401."""
        response = await client.get("/api/v1/admin/usage?months=1")
        assert response.status_code == 401


class TestUserSuspension:
    """User suspension and reactivation tests."""

    async def test_suspend_user_success(self, db_session, seeded_org_with_admin):
        """Suspend an active user."""
        org, admin = seeded_org_with_admin

        # Create a reviewer to suspend
        reviewer = User(
            org_id=org.org_id,
            email="reviewer@example.com",
            password_hash=hash_password("pass123"),
            full_name="Reviewer",
            role="reviewer",
            is_active=True,
        )
        db_session.add(reviewer)
        await db_session.commit()
        await db_session.refresh(reviewer)

        # Suspend reviewer
        await suspend_user(db_session, org.org_id, reviewer.user_id)

        # Verify
        result = await db_session.execute(
            select(User).where(User.user_id == reviewer.user_id)
        )
        suspended_user = result.scalar_one()
        assert suspended_user.is_active is False

    async def test_suspend_user_not_found(self, db_session, seeded_org_with_admin):
        """Suspend nonexistent user should raise ValueError."""
        org, _ = seeded_org_with_admin
        import uuid

        with pytest.raises(ValueError):
            await suspend_user(db_session, org.org_id, uuid.uuid4())

    async def test_suspend_last_active_admin_blocked(self, db_session, seeded_org_with_admin):
        """Cannot suspend the last active admin."""
        org, admin = seeded_org_with_admin

        with pytest.raises(LastActiveAdminError):
            await suspend_user(db_session, org.org_id, admin.user_id)

    async def test_suspend_last_active_admin_blocked_even_if_multiple_admins_but_others_inactive(
        self, db_session, seeded_org_with_admin
    ):
        """Can't suspend if it would leave no active admins."""
        org, admin = seeded_org_with_admin

        # Add another admin but suspend them first
        admin2 = User(
            org_id=org.org_id,
            email="admin2@example.com",
            password_hash=hash_password("pass123"),
            full_name="Admin 2",
            role="admin",
            is_active=False,  # Already suspended
        )
        db_session.add(admin2)
        await db_session.commit()

        # Can't suspend the remaining active admin
        with pytest.raises(LastActiveAdminError):
            await suspend_user(db_session, org.org_id, admin.user_id)

    async def test_reactivate_user_success(self, db_session, seeded_org_with_admin):
        """Reactivate a suspended user."""
        org, _ = seeded_org_with_admin

        reviewer = User(
            org_id=org.org_id,
            email="reviewer@example.com",
            password_hash=hash_password("pass123"),
            full_name="Reviewer",
            role="reviewer",
            is_active=False,
        )
        db_session.add(reviewer)
        await db_session.commit()
        await db_session.refresh(reviewer)

        # Reactivate
        await reactivate_user(db_session, org.org_id, reviewer.user_id)

        result = await db_session.execute(
            select(User).where(User.user_id == reviewer.user_id)
        )
        reactivated_user = result.scalar_one()
        assert reactivated_user.is_active is True

    async def test_reactivate_user_not_found(self, db_session, seeded_org_with_admin):
        """Reactivate nonexistent user should raise ValueError."""
        org, _ = seeded_org_with_admin
        import uuid

        with pytest.raises(ValueError):
            await reactivate_user(db_session, org.org_id, uuid.uuid4())

    async def test_suspend_reactivate_endpoints(self, client, db_session, seeded_org_with_admin):
        """Test suspend/reactivate endpoints."""
        org, admin = seeded_org_with_admin

        # Create reviewer
        reviewer = User(
            org_id=org.org_id,
            email="reviewer@example.com",
            password_hash=hash_password("pass123"),
            full_name="Reviewer",
            role="reviewer",
            is_active=True,
        )
        db_session.add(reviewer)
        await db_session.commit()
        await db_session.refresh(reviewer)

        # Login as admin
        login_response = await client.post(
            "/api/v1/auth/login",
            json={"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD},
        )
        token = login_response.json()["access_token"]

        # Suspend reviewer
        response = await client.patch(
            f"/api/v1/admin/users/{reviewer.user_id}/suspend",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 204

        # Reactivate
        response = await client.patch(
            f"/api/v1/admin/users/{reviewer.user_id}/reactivate",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 204


class TestBulkImport:
    """Bulk user import tests."""

    async def test_bulk_import_valid_csv(self, db_session, seeded_org_with_admin):
        """Import multiple valid users."""
        org, _ = seeded_org_with_admin

        csv_content = """email,full_name,role
alice@example.com,Alice Smith,admin
bob@example.com,Bob Jones,reviewer
charlie@example.com,Charlie Brown,viewer
"""

        result = await bulk_import_users(db_session, org.org_id, csv_content)

        assert result["created"] == 3
        assert result["skipped"] == []
        assert result["errors"] == []

        # Verify users in DB
        users_result = await db_session.execute(
            select(User).where(User.org_id == org.org_id).order_by(User.email)
        )
        users = users_result.scalars().all()
        assert len(users) == 4  # 3 imported + 1 admin from fixture

    async def test_bulk_import_skips_duplicates(self, db_session, seeded_org_with_admin):
        """Skip emails that already exist."""
        org, admin = seeded_org_with_admin

        csv_content = f"""email,full_name,role
{admin.email},Admin,admin
alice@example.com,Alice,reviewer
"""

        result = await bulk_import_users(db_session, org.org_id, csv_content)

        assert result["created"] == 1  # Only alice
        assert len(result["skipped"]) == 1
        assert admin.email.lower() in result["skipped"][0]["reason"].lower()

    async def test_bulk_import_invalid_role(self, db_session, seeded_org_with_admin):
        """Invalid role should error."""
        org, _ = seeded_org_with_admin

        csv_content = """email,full_name,role
alice@example.com,Alice,superuser
bob@example.com,Bob,reviewer
"""

        result = await bulk_import_users(db_session, org.org_id, csv_content)

        assert result["created"] == 1  # Only bob
        assert len(result["errors"]) == 1
        assert "Invalid role" in result["errors"][0]["reason"]

    async def test_bulk_import_missing_email(self, db_session, seeded_org_with_admin):
        """Missing email should error."""
        org, _ = seeded_org_with_admin

        csv_content = """email,full_name,role
,Alice,reviewer
bob@example.com,Bob,admin
"""

        result = await bulk_import_users(db_session, org.org_id, csv_content)

        assert result["created"] == 1  # Only bob
        assert len(result["errors"]) == 1
        assert "Missing email" in result["errors"][0]["reason"]

    async def test_bulk_import_case_insensitive_duplicate(self, db_session, seeded_org_with_admin):
        """Case-insensitive email duplicate check."""
        org, _ = seeded_org_with_admin

        user = User(
            org_id=org.org_id,
            email="Alice@Example.COM",
            password_hash=hash_password("pass123"),
            full_name="Alice",
            role="reviewer",
            is_active=True,
        )
        db_session.add(user)
        await db_session.commit()

        csv_content = """email,full_name,role
alice@example.com,Alice Smith,admin
bob@example.com,Bob,reviewer
"""

        result = await bulk_import_users(db_session, org.org_id, csv_content)

        assert result["created"] == 1
        assert len(result["skipped"]) == 1

    async def test_bulk_import_bad_header(self, db_session, seeded_org_with_admin):
        """Wrong header should error."""
        org, _ = seeded_org_with_admin

        csv_content = """name,email
alice@example.com,Alice
"""

        result = await bulk_import_users(db_session, org.org_id, csv_content)

        assert result["created"] == 0
        assert len(result["errors"]) == 1
        assert "Invalid header" in result["errors"][0]["reason"]

    async def test_bulk_import_endpoint(self, client, db_session, seeded_org_with_admin):
        """Test bulk import endpoint."""
        org, admin = seeded_org_with_admin

        csv_content = """email,full_name,role
alice@example.com,Alice,admin
bob@example.com,Bob,reviewer
"""

        # Login
        login_response = await client.post(
            "/api/v1/auth/login",
            json={"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD},
        )
        token = login_response.json()["access_token"]

        # Upload CSV
        response = await client.post(
            "/api/v1/admin/users/bulk-import",
            files={"file": ("users.csv", csv_content, "text/csv")},
            headers={"Authorization": f"Bearer {token}"},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["created"] == 2
        assert data["skipped"] == []
        assert data["errors"] == []

    async def test_bulk_import_endpoint_requires_admin(self, client, db_session, seeded_org_with_admin):
        """Non-admin should get 403."""
        org, admin = seeded_org_with_admin

        # Create reviewer
        reviewer = User(
            org_id=org.org_id,
            email="reviewer@example.com",
            password_hash=hash_password("pass12345"),
            full_name="Reviewer",
            role="reviewer",
            is_active=True,
        )
        db_session.add(reviewer)
        await db_session.commit()

        # Login as reviewer
        login_response = await client.post(
            "/api/v1/auth/login",
            json={"email": "reviewer@example.com", "password": "pass12345"},
        )
        token = login_response.json()["access_token"]

        csv_content = """email,full_name,role
alice@example.com,Alice,admin
"""

        response = await client.post(
            "/api/v1/admin/users/bulk-import",
            files={"file": ("users.csv", csv_content, "text/csv")},
            headers={"Authorization": f"Bearer {token}"},
        )

        assert response.status_code == 403

    async def test_bulk_import_bad_file_encoding(self, client, db_session, seeded_org_with_admin):
        """Non-UTF8 file should error."""
        org, admin = seeded_org_with_admin

        # Login
        login_response = await client.post(
            "/api/v1/auth/login",
            json={"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD},
        )
        token = login_response.json()["access_token"]

        # Bad encoding
        bad_content = b"\xff\xfeNot UTF8"

        response = await client.post(
            "/api/v1/admin/users/bulk-import",
            files={"file": ("users.csv", bad_content)},
            headers={"Authorization": f"Bearer {token}"},
        )

        assert response.status_code == 400
