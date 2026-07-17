"""Tests for admin_extra router endpoints.

T-2083: Subscription tier display
T-2089: User activity monitoring
"""

import pytest
from datetime import datetime, timedelta
from uuid import uuid4

from httpx import ASGITransport, AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import AsyncSessionLocal
from app.models.organization import Organization
from app.models.user import User
from app.models.audit_log import AuditLog
from app.models.enums import UserRole, AuditResourceType, SubscriptionTier
from app.auth import create_access_token


@pytest.fixture
async def test_db_with_admin(db_session: AsyncSession):
    """Create test organization and admin user."""
    org_id = uuid4()
    org = Organization(
        org_id=org_id,
        name="Test Organization",
        subscription_tier=SubscriptionTier.PRO.value,
    )
    db_session.add(org)
    await db_session.flush()

    admin_id = uuid4()
    admin = User(
        user_id=admin_id,
        org_id=org_id,
        email="admin@test.example.com",
        full_name="Admin User",
        role=UserRole.ADMIN.value,
        is_active=True,
    )
    db_session.add(admin)

    # Also create a regular user
    user_id = uuid4()
    regular = User(
        user_id=user_id,
        org_id=org_id,
        email="user@test.example.com",
        full_name="Regular User",
        role=UserRole.VIEWER.value,
        is_active=True,
    )
    db_session.add(regular)

    await db_session.commit()

    return {
        "org_id": org_id,
        "admin_id": admin_id,
        "admin_email": "admin@test.example.com",
        "user_id": user_id,
        "user_email": "user@test.example.com",
    }


@pytest.fixture
async def test_audit_logs(db_session: AsyncSession, test_db_with_admin: dict):
    """Create test audit log entries."""
    org_id = test_db_with_admin["org_id"]
    user_id = test_db_with_admin["user_id"]

    now = datetime.utcnow()

    # Create 5 audit logs for regular_user within the last 30 days
    for i in range(5):
        log = AuditLog(
            org_id=org_id,
            user_id=user_id,
            action=f"test_action_{i}",
            resource_type=AuditResourceType.DOCUMENT.value,
            resource_id=uuid4(),
            details={"test": f"data_{i}"},
            created_at=now - timedelta(days=i),
        )
        db_session.add(log)

    # Create one log outside the 30-day window
    old_log = AuditLog(
        org_id=org_id,
        user_id=user_id,
        action="old_action",
        resource_type=AuditResourceType.REVIEW.value,
        resource_id=uuid4(),
        details={"test": "old_data"},
        created_at=now - timedelta(days=45),
    )
    db_session.add(old_log)

    await db_session.commit()


@pytest.mark.asyncio
async def test_get_subscription_tier_admin(test_db_with_admin: dict):
    """Test subscription tier endpoint returns correct tier for admin."""
    from main import app

    # Generate valid JWT token
    access_token, _ = create_access_token(
        user_id=test_db_with_admin["admin_id"],
        email=test_db_with_admin["admin_email"],
        org_id=test_db_with_admin["org_id"],
        role="admin",
    )

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://testserver") as client:
        response = await client.get(
            "/api/v1/admin/subscription",
            headers={"Authorization": f"Bearer {access_token}"},
        )

    assert response.status_code == 200
    data = response.json()
    assert data["subscription_tier"] == "pro"
    assert data["org_id"] == str(test_db_with_admin["org_id"])


@pytest.mark.asyncio
async def test_get_subscription_tier_non_admin(test_db_with_admin: dict):
    """Test subscription tier endpoint rejects non-admin users."""
    from main import app

    # Generate token for non-admin user
    access_token, _ = create_access_token(
        user_id=test_db_with_admin["user_id"],
        email=test_db_with_admin["user_email"],
        org_id=test_db_with_admin["org_id"],
        role="viewer",
    )

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://testserver") as client:
        response = await client.get(
            "/api/v1/admin/subscription",
            headers={"Authorization": f"Bearer {access_token}"},
        )

    assert response.status_code == 403
    assert "Insufficient permissions" in response.json()["detail"]


@pytest.mark.asyncio
async def test_get_subscription_tier_no_auth():
    """Test subscription tier endpoint requires authentication."""
    from main import app

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://testserver") as client:
        response = await client.get("/api/v1/admin/subscription")

    assert response.status_code == 401


@pytest.mark.asyncio
async def test_get_user_activity_admin(test_db_with_admin: dict, test_audit_logs):
    """Test activity endpoint returns correct logs for target user."""
    from main import app

    access_token, _ = create_access_token(
        user_id=test_db_with_admin["admin_id"],
        email=test_db_with_admin["admin_email"],
        org_id=test_db_with_admin["org_id"],
        role="admin",
    )

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://testserver") as client:
        response = await client.get(
            f"/api/v1/admin/users/{test_db_with_admin['user_id']}/activity?days=30",
            headers={"Authorization": f"Bearer {access_token}"},
        )

    assert response.status_code == 200
    data = response.json()
    assert data["count"] == 5  # Only logs within 30 days
    assert len(data["logs"]) == 5
    # Verify they're sorted newest first
    assert data["logs"][0]["action"] == "test_action_0"
    assert data["logs"][4]["action"] == "test_action_4"


@pytest.mark.asyncio
async def test_get_user_activity_with_custom_days(test_db_with_admin: dict, test_audit_logs):
    """Test activity endpoint respects days parameter."""
    from main import app

    access_token, _ = create_access_token(
        user_id=test_db_with_admin["admin_id"],
        email=test_db_with_admin["admin_email"],
        org_id=test_db_with_admin["org_id"],
        role="admin",
    )

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://testserver") as client:
        # Request with 50 day window to include the old log
        response = await client.get(
            f"/api/v1/admin/users/{test_db_with_admin['user_id']}/activity?days=50",
            headers={"Authorization": f"Bearer {access_token}"},
        )

    assert response.status_code == 200
    data = response.json()
    assert data["count"] == 6  # Now includes the old log


@pytest.mark.asyncio
async def test_get_user_activity_non_admin(test_db_with_admin: dict):
    """Test activity endpoint rejects non-admin users."""
    from main import app

    access_token, _ = create_access_token(
        user_id=test_db_with_admin["user_id"],
        email=test_db_with_admin["user_email"],
        org_id=test_db_with_admin["org_id"],
        role="viewer",
    )

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://testserver") as client:
        response = await client.get(
            f"/api/v1/admin/users/{test_db_with_admin['admin_id']}/activity",
            headers={"Authorization": f"Bearer {access_token}"},
        )

    assert response.status_code == 403
    assert "Insufficient permissions" in response.json()["detail"]


@pytest.mark.asyncio
async def test_get_user_activity_user_not_found(test_db_with_admin: dict):
    """Test activity endpoint returns 404 for non-existent user."""
    from main import app

    access_token, _ = create_access_token(
        user_id=test_db_with_admin["admin_id"],
        email=test_db_with_admin["admin_email"],
        org_id=test_db_with_admin["org_id"],
        role="admin",
    )

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://testserver") as client:
        fake_user_id = uuid4()
        response = await client.get(
            f"/api/v1/admin/users/{fake_user_id}/activity",
            headers={"Authorization": f"Bearer {access_token}"},
        )

    assert response.status_code == 404
    assert "User not found" in response.json()["detail"]


@pytest.mark.asyncio
async def test_get_user_activity_cross_org_isolation(
    test_db_with_admin: dict, db_session: AsyncSession
):
    """Test activity endpoint doesn't leak users from other organizations."""
    from main import app

    # Create a second organization with a user
    org2_id = uuid4()
    org2 = Organization(
        org_id=org2_id,
        name="Other Organization",
        subscription_tier=SubscriptionTier.FREE.value,
    )
    db_session.add(org2)
    await db_session.flush()

    user2_id = uuid4()
    user2 = User(
        user_id=user2_id,
        org_id=org2_id,
        email="user@other.example.com",
        full_name="Other User",
        role=UserRole.VIEWER.value,
        is_active=True,
    )
    db_session.add(user2)
    await db_session.commit()

    # Admin from org1 tries to access user from org2
    access_token, _ = create_access_token(
        user_id=test_db_with_admin["admin_id"],
        email=test_db_with_admin["admin_email"],
        org_id=test_db_with_admin["org_id"],
        role="admin",
    )

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://testserver") as client:
        response = await client.get(
            f"/api/v1/admin/users/{user2_id}/activity",
            headers={"Authorization": f"Bearer {access_token}"},
        )

    # Should be 404, not 200 (doesn't leak that user exists in another org)
    assert response.status_code == 404
    assert "User not found" in response.json()["detail"]


@pytest.mark.asyncio
async def test_get_user_activity_no_logs(test_db_with_admin: dict):
    """Test activity endpoint returns empty list when user has no activity."""
    from main import app

    access_token, _ = create_access_token(
        user_id=test_db_with_admin["admin_id"],
        email=test_db_with_admin["admin_email"],
        org_id=test_db_with_admin["org_id"],
        role="admin",
    )

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://testserver") as client:
        response = await client.get(
            f"/api/v1/admin/users/{test_db_with_admin['user_id']}/activity?days=30",
            headers={"Authorization": f"Bearer {access_token}"},
        )

    assert response.status_code == 200
    data = response.json()
    assert data["count"] == 0
    assert data["logs"] == []
