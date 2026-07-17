"""Tests for compliance framework tracking endpoints.

T-2051 (SOC2), T-2052 (ISO27001), T-2053 (GDPR), T-2054 (HIPAA),
T-2055 (compliance report generation)
"""

import pytest
from httpx import ASGITransport, AsyncClient

from app.auth import hash_password
from app.compliance.frameworks import (
    DEFAULT_CONTROLS,
    get_framework_status,
    list_controls,
    seed_framework_controls,
)
from app.models.organization import Organization
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
async def seeded_admin_and_org(db_session):
    """Create org and admin user for testing."""
    org = Organization(name="Test Compliance Org", subscription_tier="enterprise")
    db_session.add(org)
    await db_session.flush()

    user = User(
        org_id=org.org_id,
        email=ADMIN_EMAIL,
        password_hash=hash_password(ADMIN_PASSWORD),
        role="admin",
        is_active=True,
    )
    db_session.add(user)
    await db_session.commit()

    return {"org_id": org.org_id, "user_id": user.user_id, "email": ADMIN_EMAIL}


@pytest.fixture
async def admin_token(client, seeded_admin_and_org):
    """Get admin JWT token."""
    response = await client.post(
        "/api/v1/auth/login",
        json={"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD},
    )
    assert response.status_code == 200
    return response.json()["access_token"]


@pytest.mark.asyncio
async def test_seed_framework_idempotent(db_session, seeded_admin_and_org):
    """Seeding twice doesn't duplicate controls."""
    org_id = seeded_admin_and_org["org_id"]

    count1 = await seed_framework_controls(db_session, org_id, "SOC2")
    assert count1 == len(DEFAULT_CONTROLS["SOC2"])

    count2 = await seed_framework_controls(db_session, org_id, "SOC2")
    assert count2 == 0  # Already seeded


@pytest.mark.asyncio
async def test_status_calculates_correctly(db_session, seeded_admin_and_org):
    """Status summary calculates percent_implemented correctly."""
    org_id = seeded_admin_and_org["org_id"]

    await seed_framework_controls(db_session, org_id, "SOC2")

    status = await get_framework_status(db_session, org_id, "SOC2")

    assert status["framework"] == "SOC2"
    assert status["total_controls"] == len(DEFAULT_CONTROLS["SOC2"])
    assert status["by_status"]["not_started"] == len(DEFAULT_CONTROLS["SOC2"])
    assert status["by_status"]["in_progress"] == 0
    assert status["by_status"]["implemented"] == 0
    assert status["by_status"]["verified"] == 0
    assert status["percent_implemented"] == 0.0


@pytest.mark.asyncio
async def test_report_csv_contains_disclaimer_and_columns(db_session, seeded_admin_and_org):
    """CSV report includes disclaimer and expected columns."""
    org_id = seeded_admin_and_org["org_id"]

    await seed_framework_controls(db_session, org_id, "GDPR")

    from app.compliance.frameworks import generate_compliance_report

    csv_content = await generate_compliance_report(db_session, org_id, "GDPR")

    assert "DISCLAIMER" in csv_content
    assert "self-reported" in csv_content.lower()
    assert "NOT a certification" in csv_content

    # Check CSV columns
    lines = csv_content.strip().split("\n")
    assert len(lines) > 2  # disclaimer + header + at least one control

    # Second line should be CSV header
    header = lines[1]
    assert "control_code" in header
    assert "description" in header
    assert "status" in header
    assert "evidence_notes" in header
    assert "last_reviewed_at" in header


@pytest.mark.asyncio
async def test_org_isolation(db_session, seeded_admin_and_org):
    """Controls from one org don't appear in another."""
    org1_id = seeded_admin_and_org["org_id"]

    # Create second org
    org2 = Organization(name="Other Org", subscription_tier="free")
    db_session.add(org2)
    await db_session.flush()
    org2_id = org2.org_id

    # Seed for org1
    await seed_framework_controls(db_session, org1_id, "ISO27001")

    # Org2 should have no controls
    controls_org2 = await list_controls(db_session, org2_id, "ISO27001")
    assert len(controls_org2) == 0

    # Org1 should have controls
    controls_org1 = await list_controls(db_session, org1_id, "ISO27001")
    assert len(controls_org1) == len(DEFAULT_CONTROLS["ISO27001"])


@pytest.mark.asyncio
async def test_non_admin_gets_403(client, admin_token, seeded_admin_and_org, db_session):
    """Non-admin users get 403 on framework endpoints."""
    org_id = seeded_admin_and_org["org_id"]

    # Create a viewer user
    viewer = User(
        org_id=org_id,
        email="viewer@example.com",
        password_hash=hash_password("password123"),
        role="viewer",
        is_active=True,
    )
    db_session.add(viewer)
    await db_session.commit()

    # Login as viewer
    response = await client.post(
        "/api/v1/auth/login",
        json={"email": "viewer@example.com", "password": "password123"},
    )
    viewer_token = response.json()["access_token"]

    # Try to seed (should 403)
    response = await client.post(
        "/api/v1/compliance/frameworks/SOC2/seed",
        headers={"Authorization": f"Bearer {viewer_token}"},
    )
    assert response.status_code == 403


@pytest.mark.asyncio
async def test_seed_endpoint_idempotent(client, admin_token):
    """POST /seed endpoint is idempotent."""
    response1 = await client.post(
        "/api/v1/compliance/frameworks/HIPAA/seed",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert response1.status_code == 200
    assert response1.json()["count"] == len(DEFAULT_CONTROLS["HIPAA"])

    response2 = await client.post(
        "/api/v1/compliance/frameworks/HIPAA/seed",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert response2.status_code == 200
    assert response2.json()["count"] == 0  # Already seeded


@pytest.mark.asyncio
async def test_status_endpoint_returns_summary(client, admin_token):
    """GET /{framework}/status returns correct summary."""
    # Seed first
    await client.post(
        "/api/v1/compliance/frameworks/GDPR/seed",
        headers={"Authorization": f"Bearer {admin_token}"},
    )

    response = await client.get(
        "/api/v1/compliance/frameworks/GDPR/status",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert response.status_code == 200

    data = response.json()
    assert data["framework"] == "GDPR"
    assert data["total_controls"] == len(DEFAULT_CONTROLS["GDPR"])
    assert "by_status" in data
    assert "percent_implemented" in data


@pytest.mark.asyncio
async def test_controls_endpoint_lists_controls(client, admin_token):
    """GET /{framework}/controls returns full list."""
    await client.post(
        "/api/v1/compliance/frameworks/ISO27001/seed",
        headers={"Authorization": f"Bearer {admin_token}"},
    )

    response = await client.get(
        "/api/v1/compliance/frameworks/ISO27001/controls",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert response.status_code == 200

    data = response.json()
    assert "controls" in data
    assert len(data["controls"]) == len(DEFAULT_CONTROLS["ISO27001"])

    # Check each control has expected fields
    for control in data["controls"]:
        assert "control_id" in control
        assert "control_code" in control
        assert "description" in control
        assert "status" in control
        assert control["status"] == "not_started"


@pytest.mark.asyncio
async def test_update_control_status(client, admin_token, db_session, seeded_admin_and_org):
    """PATCH control updates status and sets last_reviewed_at."""
    org_id = seeded_admin_and_org["org_id"]

    # Seed
    await client.post(
        "/api/v1/compliance/frameworks/SOC2/seed",
        headers={"Authorization": f"Bearer {admin_token}"},
    )

    # Get controls
    response = await client.get(
        "/api/v1/compliance/frameworks/SOC2/controls",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    control_id = response.json()["controls"][0]["control_id"]

    # Update status
    response = await client.patch(
        f"/api/v1/compliance/frameworks/controls/{control_id}",
        json={"status": "implemented", "evidence_notes": "We implemented this control"},
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert response.status_code == 204

    # Verify update
    response = await client.get(
        "/api/v1/compliance/frameworks/SOC2/controls",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    updated_control = next(
        (c for c in response.json()["controls"] if c["control_id"] == control_id),
        None,
    )
    assert updated_control["status"] == "implemented"
    assert updated_control["evidence_notes"] == "We implemented this control"
    assert updated_control["last_reviewed_at"] is not None


@pytest.mark.asyncio
async def test_report_endpoint_returns_csv(client, admin_token):
    """GET /{framework}/report returns CSV with disclaimer."""
    await client.post(
        "/api/v1/compliance/frameworks/HIPAA/seed",
        headers={"Authorization": f"Bearer {admin_token}"},
    )

    response = await client.get(
        "/api/v1/compliance/frameworks/HIPAA/report",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/csv")

    csv_content = response.text
    assert "DISCLAIMER" in csv_content
    assert "NOT a certification" in csv_content
    assert "control_code" in csv_content
