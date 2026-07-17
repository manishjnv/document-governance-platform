"""Tests for admin endpoints (T-2081, T-2082, T-2086).

Builds a minimal standalone FastAPI app around just the admin router,
with get_db/get_current_user overridden — avoids main.py's
TrustedHostMiddleware (rejects the TestClient's "testserver" host) and
the hardcoded in-memory auth stub in app/routers/auth.py. Auth is
short-circuited by overriding get_current_user directly with a
TokenData built via model_construct(), since TokenData.org_id/user_id
are typed `int` (pre-existing Phase 1 auth/DB UUID mismatch, out of
scope here) but the real Organization/User PKs are UUID.
"""

import uuid
from datetime import datetime, timedelta

import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient

from app.db.session import get_db
from app.dependencies import get_current_user
from app.models.organization import Organization
from app.models.user import User
from app.routers.admin import router as admin_router
from app.schemas.auth import TokenData


def _token(org_id: uuid.UUID, role: str, user_id: uuid.UUID | None = None) -> TokenData:
    return TokenData.model_construct(
        user_id=user_id or uuid.uuid4(),
        email="user@example.com",
        org_id=org_id,
        role=role,
        exp=datetime.utcnow() + timedelta(hours=1),
        iat=datetime.utcnow(),
        type="access",
    )


def _make_client(db_session, org_id: uuid.UUID, role: str, user_id: uuid.UUID | None = None) -> AsyncClient:
    app = FastAPI()
    app.include_router(admin_router)

    async def _override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = _override_get_db
    app.dependency_overrides[get_current_user] = lambda: _token(org_id, role, user_id)
    return AsyncClient(transport=ASGITransport(app=app), base_url="http://testserver")


async def _seed_org(db_session) -> Organization:
    org = Organization(org_id=uuid.uuid4(), name="Acme Co")
    db_session.add(org)
    await db_session.commit()
    await db_session.refresh(org)
    return org


async def _seed_user(db_session, org_id: uuid.UUID, role: str, email: str) -> User:
    user = User(user_id=uuid.uuid4(), org_id=org_id, email=email, role=role)
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    return user


@pytest.mark.asyncio
async def test_branding_update_roundtrips(db_session):
    org = await _seed_org(db_session)
    client = _make_client(db_session, org.org_id, role="admin")

    resp = await client.patch(
        "/api/v1/admin/organization",
        json={
            "name": "Acme Corp",
            "logo_url": "https://cdn.example.com/logo.png",
            "brand_primary_color": "#112233",
            "brand_secondary_color": "#AABBCC",
        },
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["name"] == "Acme Corp"
    assert body["logo_url"] == "https://cdn.example.com/logo.png"
    assert body["brand_primary_color"] == "#112233"
    assert body["brand_secondary_color"] == "#AABBCC"

    # Round-trip via GET
    resp = await client.get("/api/v1/admin/organization")
    assert resp.status_code == 200
    body = resp.json()
    assert body["brand_primary_color"] == "#112233"
    assert body["brand_secondary_color"] == "#AABBCC"


@pytest.mark.asyncio
async def test_branding_update_rejects_bad_color(db_session):
    org = await _seed_org(db_session)
    client = _make_client(db_session, org.org_id, role="admin")

    resp = await client.patch(
        "/api/v1/admin/organization",
        json={"brand_primary_color": "not-a-color"},
    )
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_role_update_works(db_session):
    org = await _seed_org(db_session)
    await _seed_user(db_session, org.org_id, "admin", "admin@example.com")
    reviewer = await _seed_user(db_session, org.org_id, "reviewer", "reviewer@example.com")
    client = _make_client(db_session, org.org_id, role="admin")

    resp = await client.patch(
        f"/api/v1/admin/users/{reviewer.user_id}/role",
        json={"role": "admin"},
    )
    assert resp.status_code == 200
    assert resp.json()["role"] == "admin"

    resp = await client.get("/api/v1/admin/users")
    assert resp.status_code == 200
    roles = {u["user_id"]: u["role"] for u in resp.json()}
    assert roles[str(reviewer.user_id)] == "admin"


@pytest.mark.asyncio
async def test_cannot_demote_last_admin(db_session):
    org = await _seed_org(db_session)
    admin = await _seed_user(db_session, org.org_id, "admin", "solo-admin@example.com")
    client = _make_client(db_session, org.org_id, role="admin")

    resp = await client.patch(
        f"/api/v1/admin/users/{admin.user_id}/role",
        json={"role": "reviewer"},
    )
    assert resp.status_code == 400
    assert "last" in resp.json()["detail"].lower()

    # Role unchanged
    resp = await client.get("/api/v1/admin/users")
    roles = {u["user_id"]: u["role"] for u in resp.json()}
    assert roles[str(admin.user_id)] == "admin"


@pytest.mark.asyncio
async def test_can_demote_admin_when_another_remains(db_session):
    org = await _seed_org(db_session)
    admin1 = await _seed_user(db_session, org.org_id, "admin", "admin1@example.com")
    await _seed_user(db_session, org.org_id, "admin", "admin2@example.com")
    client = _make_client(db_session, org.org_id, role="admin")

    resp = await client.patch(
        f"/api/v1/admin/users/{admin1.user_id}/role",
        json={"role": "viewer"},
    )
    assert resp.status_code == 200
    assert resp.json()["role"] == "viewer"


@pytest.mark.asyncio
async def test_non_admin_gets_403_on_all_admin_endpoints(db_session):
    org = await _seed_org(db_session)
    target = await _seed_user(db_session, org.org_id, "reviewer", "target@example.com")
    client = _make_client(db_session, org.org_id, role="reviewer")

    assert (await client.get("/api/v1/admin/organization")).status_code == 403
    assert (
        await client.patch("/api/v1/admin/organization", json={"name": "x"})
    ).status_code == 403
    assert (await client.get("/api/v1/admin/users")).status_code == 403
    assert (
        await client.patch(
            f"/api/v1/admin/users/{target.user_id}/role", json={"role": "admin"}
        )
    ).status_code == 403
