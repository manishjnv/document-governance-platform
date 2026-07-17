"""Tests for app/routers/admin_config.py (T-2091 - T-2095).

Set/get round-trip for each of the five config types, org isolation, and
non-admin 403. Follows tests/test_auth.py's pattern: httpx.AsyncClient
over ASGITransport(app=app), real seeded org/user rows via db_session,
real JWT via a real /api/v1/auth/login call -- not a sync TestClient and
not a hand-built TokenData.

admin_config.router isn't included in main.py yet (T-2091's instructions
forbid editing main.py -- a separate integration step wires it in), so
this file mounts it onto the imported `app` instance directly. That's a
test-only concern; app/routers/admin_config.py itself doesn't touch
main.py.
"""

import pytest
from httpx import ASGITransport, AsyncClient

import app.models.kb_article  # noqa: F401 -- registers KBArticle for SQLAlchemy's
# mapper configure step before Organization is touched. Organization.kb_articles
# (a different Wave-2 task, not this one) declares a string-referenced
# relationship("KBArticle") but app/models/__init__.py doesn't import it yet, so
# any DB-backed test in this process blows up in mapper configuration without
# this -- same workaround already used by test_document_similarity.py,
# test_notifications.py, test_knowledge_base.py. Remove once
# app/models/__init__.py imports KBArticle itself (out of scope here --
# app/models/__init__.py is off limits for T-2091-T-2095 too).
from app.auth import hash_password
from app.models.organization import Organization
from app.models.user import User
from app.routers.admin_config import router as admin_config_router
from main import app

# ponytail: main.py owns the real app.include_router(...) wiring long
# term (T-2091 explicitly forbids editing main.py); module-level code runs
# once per test session, so this just makes the router reachable here.
app.include_router(admin_config_router)

ADMIN_PASSWORD = "password123"


@pytest.fixture
async def client():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as c:
        yield c


async def _seed_org_and_user(db_session, *, email: str, role: str, org_name: str) -> Organization:
    org = Organization(name=org_name, subscription_tier="enterprise")
    db_session.add(org)
    await db_session.flush()

    user = User(
        org_id=org.org_id,
        email=email,
        password_hash=hash_password(ADMIN_PASSWORD),
        full_name="Test User",
        role=role,
        is_active=True,
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(org)
    return org, user


async def _login(client, email: str) -> str:
    response = await client.post(
        "/api/v1/auth/login",
        json={"email": email, "password": ADMIN_PASSWORD},
    )
    assert response.status_code == 200, response.text
    return response.json()["access_token"]


@pytest.fixture
async def admin_token(client, db_session):
    org, user = await _seed_org_and_user(
        db_session, email="admin@example.com", role="admin", org_name="Org A"
    )
    token = await _login(client, "admin@example.com")
    return token, org.org_id


@pytest.fixture
async def viewer_token(client, db_session):
    org, user = await _seed_org_and_user(
        db_session, email="viewer@example.com", role="viewer", org_name="Org Viewer"
    )
    token = await _login(client, "viewer@example.com")
    return token


def _auth(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


class TestRuleConfig:
    async def test_round_trip(self, client, admin_token):
        token, _ = admin_token

        resp = await client.get("/api/v1/admin/config/rules", headers=_auth(token))
        assert resp.status_code == 200
        assert resp.json()["SOW-002"] is True  # default enabled

        resp = await client.patch(
            "/api/v1/admin/config/rules",
            json={"rule_id": "SOW-002", "enabled": False},
            headers=_auth(token),
        )
        assert resp.status_code == 200
        assert resp.json()["SOW-002"] is False

        resp = await client.get("/api/v1/admin/config/rules", headers=_auth(token))
        assert resp.json()["SOW-002"] is False
        assert resp.json()["SOW-001"] is True  # untouched rule stays default

    async def test_unknown_rule_id_rejected(self, client, admin_token):
        token, _ = admin_token
        resp = await client.patch(
            "/api/v1/admin/config/rules",
            json={"rule_id": "NOT-A-REAL-RULE", "enabled": False},
            headers=_auth(token),
        )
        assert resp.status_code == 400

    async def test_non_admin_forbidden(self, client, viewer_token):
        resp = await client.get("/api/v1/admin/config/rules", headers=_auth(viewer_token))
        assert resp.status_code == 403


class TestAgentConfig:
    async def test_round_trip(self, client, admin_token):
        token, _ = admin_token

        resp = await client.get("/api/v1/admin/config/agents", headers=_auth(token))
        assert resp.status_code == 200
        assert resp.json()["ScopeReviewer"] is True

        resp = await client.patch(
            "/api/v1/admin/config/agents",
            json={"agent_name": "ScopeReviewer", "enabled": False},
            headers=_auth(token),
        )
        assert resp.status_code == 200
        assert resp.json()["ScopeReviewer"] is False

        resp = await client.get("/api/v1/admin/config/agents", headers=_auth(token))
        assert resp.json()["ScopeReviewer"] is False
        assert resp.json()["SecurityReviewer"] is True

    async def test_unknown_agent_rejected(self, client, admin_token):
        token, _ = admin_token
        resp = await client.patch(
            "/api/v1/admin/config/agents",
            json={"agent_name": "NotARealAgent", "enabled": False},
            headers=_auth(token),
        )
        assert resp.status_code == 400

    async def test_non_admin_forbidden(self, client, viewer_token):
        resp = await client.get("/api/v1/admin/config/agents", headers=_auth(viewer_token))
        assert resp.status_code == 403


class TestScoringWeights:
    async def test_round_trip(self, client, admin_token):
        token, _ = admin_token

        resp = await client.get("/api/v1/admin/config/scoring-weights", headers=_auth(token))
        assert resp.status_code == 200
        assert resp.json()["completeness"] == 0.20  # platform default

        resp = await client.patch(
            "/api/v1/admin/config/scoring-weights",
            json={"category": "completeness", "weight": 2.5},
            headers=_auth(token),
        )
        assert resp.status_code == 200
        assert resp.json()["completeness"] == 2.5

        resp = await client.get("/api/v1/admin/config/scoring-weights", headers=_auth(token))
        assert resp.json()["completeness"] == 2.5
        assert resp.json()["clarity"] == 0.15  # untouched category stays default

    async def test_unknown_category_rejected(self, client, admin_token):
        token, _ = admin_token
        resp = await client.patch(
            "/api/v1/admin/config/scoring-weights",
            json={"category": "not_a_real_category", "weight": 1.0},
            headers=_auth(token),
        )
        assert resp.status_code == 400

    async def test_negative_weight_rejected(self, client, admin_token):
        token, _ = admin_token
        resp = await client.patch(
            "/api/v1/admin/config/scoring-weights",
            json={"category": "completeness", "weight": -1.0},
            headers=_auth(token),
        )
        assert resp.status_code == 422  # Pydantic ge=0

    async def test_non_admin_forbidden(self, client, viewer_token):
        resp = await client.get(
            "/api/v1/admin/config/scoring-weights", headers=_auth(viewer_token)
        )
        assert resp.status_code == 403


class TestDocumentTypes:
    async def test_round_trip(self, client, admin_token):
        token, _ = admin_token

        resp = await client.get("/api/v1/admin/config/document-types", headers=_auth(token))
        assert resp.status_code == 200
        assert resp.json() == []

        resp = await client.patch(
            "/api/v1/admin/config/document-types",
            json={"type_name": "MSA", "action": "add"},
            headers=_auth(token),
        )
        assert resp.status_code == 200
        assert resp.json() == ["MSA"]

        resp = await client.patch(
            "/api/v1/admin/config/document-types",
            json={"type_name": "MSA", "action": "remove"},
            headers=_auth(token),
        )
        assert resp.status_code == 200
        assert resp.json() == []

    async def test_non_admin_forbidden(self, client, viewer_token):
        resp = await client.get(
            "/api/v1/admin/config/document-types", headers=_auth(viewer_token)
        )
        assert resp.status_code == 403


class TestFieldMappings:
    async def test_round_trip(self, client, admin_token):
        token, _ = admin_token

        resp = await client.get("/api/v1/admin/config/field-mappings", headers=_auth(token))
        assert resp.status_code == 200
        assert resp.json() == {}

        resp = await client.patch(
            "/api/v1/admin/config/field-mappings",
            json={"source_field": "vendor_name", "action": "set", "target_category": "commercial"},
            headers=_auth(token),
        )
        assert resp.status_code == 200
        assert resp.json() == {"vendor_name": "commercial"}

        resp = await client.patch(
            "/api/v1/admin/config/field-mappings",
            json={"source_field": "vendor_name", "action": "remove"},
            headers=_auth(token),
        )
        assert resp.status_code == 200
        assert resp.json() == {}

    async def test_set_requires_target_category(self, client, admin_token):
        token, _ = admin_token
        resp = await client.patch(
            "/api/v1/admin/config/field-mappings",
            json={"source_field": "vendor_name", "action": "set"},
            headers=_auth(token),
        )
        assert resp.status_code == 400

    async def test_unknown_target_category_rejected(self, client, admin_token):
        token, _ = admin_token
        resp = await client.patch(
            "/api/v1/admin/config/field-mappings",
            json={
                "source_field": "vendor_name",
                "action": "set",
                "target_category": "not_a_real_category",
            },
            headers=_auth(token),
        )
        assert resp.status_code == 400

    async def test_non_admin_forbidden(self, client, viewer_token):
        resp = await client.get(
            "/api/v1/admin/config/field-mappings", headers=_auth(viewer_token)
        )
        assert resp.status_code == 403


class TestOrgIsolation:
    async def test_rule_config_scoped_per_org(self, client, db_session, admin_token):
        """org A disables a rule; a second org (B) must still see the default."""
        token_a, _ = admin_token

        await client.patch(
            "/api/v1/admin/config/rules",
            json={"rule_id": "SOW-002", "enabled": False},
            headers=_auth(token_a),
        )

        org_b, _ = await _seed_org_and_user(
            db_session, email="admin-b@example.com", role="admin", org_name="Org B"
        )
        token_b = await _login(client, "admin-b@example.com")

        resp = await client.get("/api/v1/admin/config/rules", headers=_auth(token_b))
        assert resp.status_code == 200
        assert resp.json()["SOW-002"] is True  # org B unaffected by org A's override

        # org A's own override is still there
        resp = await client.get("/api/v1/admin/config/rules", headers=_auth(token_a))
        assert resp.json()["SOW-002"] is False

    async def test_document_types_scoped_per_org(self, client, db_session, admin_token):
        token_a, _ = admin_token

        await client.patch(
            "/api/v1/admin/config/document-types",
            json={"type_name": "MSA", "action": "add"},
            headers=_auth(token_a),
        )

        org_b, _ = await _seed_org_and_user(
            db_session, email="admin-c@example.com", role="admin", org_name="Org C"
        )
        token_b = await _login(client, "admin-c@example.com")

        resp = await client.get("/api/v1/admin/config/document-types", headers=_auth(token_b))
        assert resp.json() == []  # org B doesn't see org A's custom type
