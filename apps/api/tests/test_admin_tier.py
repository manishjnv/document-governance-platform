"""Tests for the platform-admin org tier toggle (GET /admin/orgs, PATCH
/admin/orgs/{org_id}/tier). Same harness style as test_admin.py."""

import uuid

import pytest

from app.models.organization import Organization
from tests.test_admin import _make_client, _seed_org, _seed_user


async def _seed_org_named(db_session, name: str) -> Organization:
    """_seed_org always uses 'Acme Co'; organizations.name has a unique-while-
    active constraint, so a second org in the same test needs its own name."""
    org = Organization(org_id=uuid.uuid4(), name=name)
    db_session.add(org)
    await db_session.commit()
    await db_session.refresh(org)
    return org


@pytest.mark.asyncio
async def test_platform_admin_sets_pro(db_session, monkeypatch):
    from app.config import settings
    from app.models.audit_log import AuditLog
    from sqlalchemy import select

    monkeypatch.setattr(settings, "platform_admin_emails", "boss@example.com")

    org_a = await _seed_org(db_session)
    boss = await _seed_user(db_session, org_a.org_id, "admin", "boss@example.com")
    org_b = await _seed_org_named(db_session, "Other Org")

    client = _make_client(
        db_session, org_a.org_id, role="admin", user_id=boss.user_id, email="boss@example.com"
    )

    resp = await client.get("/api/v1/admin/orgs")
    assert resp.status_code == 200
    body = {row["org_id"]: row for row in resp.json()}
    assert str(org_a.org_id) in body
    assert str(org_b.org_id) in body
    assert body[str(org_a.org_id)]["user_count"] == 1
    assert body[str(org_a.org_id)]["subscription_tier"] == "free"

    resp = await client.patch(
        f"/api/v1/admin/orgs/{org_b.org_id}/tier", json={"subscription_tier": "pro"}
    )
    assert resp.status_code == 200
    assert resp.json()["subscription_tier"] == "pro"

    await db_session.refresh(org_b)
    assert org_b.subscription_tier == "pro"

    rows = (
        await db_session.execute(
            select(AuditLog).where(AuditLog.resource_type == "organization")
        )
    ).scalars().all()
    assert len(rows) == 1
    assert rows[0].details["new"] == "pro"


@pytest.mark.asyncio
async def test_org_admin_gets_403(db_session, monkeypatch):
    from app.config import settings

    monkeypatch.setattr(settings, "platform_admin_emails", "boss@example.com")

    org_a = await _seed_org(db_session)
    await _seed_user(db_session, org_a.org_id, "admin", "a@example.com")
    org_b = await _seed_org_named(db_session, "Other Org")

    client = _make_client(db_session, org_a.org_id, role="admin", email="a@example.com")

    resp = await client.patch(
        f"/api/v1/admin/orgs/{org_b.org_id}/tier", json={"subscription_tier": "pro"}
    )
    assert resp.status_code == 403


@pytest.mark.asyncio
async def test_invalid_tier_422(db_session, monkeypatch):
    from app.config import settings

    monkeypatch.setattr(settings, "platform_admin_emails", "boss@example.com")

    org_a = await _seed_org(db_session)
    boss = await _seed_user(db_session, org_a.org_id, "admin", "boss@example.com")
    org_b = await _seed_org_named(db_session, "Other Org")

    client = _make_client(
        db_session, org_a.org_id, role="admin", user_id=boss.user_id, email="boss@example.com"
    )
    resp = await client.patch(
        f"/api/v1/admin/orgs/{org_b.org_id}/tier", json={"subscription_tier": "gold"}
    )
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_self_downgrade_400(db_session, monkeypatch):
    from app.config import settings

    monkeypatch.setattr(settings, "platform_admin_emails", "boss@example.com")

    org_a = await _seed_org(db_session)
    boss = await _seed_user(db_session, org_a.org_id, "admin", "boss@example.com")

    client = _make_client(
        db_session, org_a.org_id, role="admin", user_id=boss.user_id, email="boss@example.com"
    )
    resp = await client.patch(
        f"/api/v1/admin/orgs/{org_a.org_id}/tier", json={"subscription_tier": "enterprise"}
    )
    assert resp.status_code == 400
