"""Tests for authentication endpoints.

Login/refresh/me/password-reset/change-password all hit the real `users`/
`organizations` tables now (see app/routers/auth.py) instead of the old
in-memory USERS_DB/ORGANIZATIONS_DB stub. `seeded_admin` seeds a real row via
`db_session` (conftest.py's TRUNCATE-isolated fixture).

Uses httpx.AsyncClient(transport=ASGITransport(...)) rather than starlette's
sync TestClient: TestClient drives the ASGI app on its own thread/event loop,
which broke here the same way it did in Wave 1's admin tests -- reusing
app/db/session.py's module-level asyncpg engine (created once at import time)
across whatever loop pytest-asyncio hands each test raised "RuntimeError:
Event loop is closed" past the first test. AsyncClient runs the app in-process
on the *same* loop as the test coroutine and its fixtures, so there's nothing
to cross.
"""

from datetime import datetime, timedelta

import pytest
from httpx import ASGITransport, AsyncClient
from jose import jwt

from app.auth import hash_password
from app.config import settings
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
async def seeded_admin(db_session):
    org = Organization(name="Test Org", subscription_tier="enterprise")
    db_session.add(org)
    await db_session.flush()

    user = User(
        org_id=org.org_id,
        email=ADMIN_EMAIL,
        password_hash=hash_password(ADMIN_PASSWORD),
        full_name="Admin User",
        role="admin",
        is_active=True,
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    return user


class TestLogin:
    """Login endpoint tests."""

    async def test_login_success(self, client, seeded_admin):
        response = await client.post(
            "/api/v1/auth/login",
            json={"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD},
        )
        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert "refresh_token" in data
        assert data["email"] == ADMIN_EMAIL
        assert data["token_type"] == "bearer"
        assert data["user_id"] == str(seeded_admin.user_id)
        assert data["org_id"] == str(seeded_admin.org_id)

    async def test_login_invalid_email(self, client, seeded_admin):
        response = await client.post(
            "/api/v1/auth/login",
            json={"email": "nonexistent@example.com", "password": ADMIN_PASSWORD},
        )
        assert response.status_code == 401
        assert "Invalid" in response.json()["detail"]

    async def test_login_invalid_password(self, client, seeded_admin):
        response = await client.post(
            "/api/v1/auth/login",
            json={"email": ADMIN_EMAIL, "password": "wrongpassword"},
        )
        assert response.status_code == 401
        assert "Invalid" in response.json()["detail"]

    async def test_login_invalid_format(self, client, seeded_admin):
        response = await client.post(
            "/api/v1/auth/login",
            json={"email": "not-an-email", "password": ADMIN_PASSWORD},
        )
        assert response.status_code == 422  # Validation error

    async def test_login_ilike_wildcards_dont_match_other_users(self, client, seeded_admin):
        """Regression: email is matched by exact case-insensitive equality,
        not ILIKE -- `%`/`_` in the submitted email must NOT act as SQL
        wildcards. seeded_admin is admin@example.com; a wildcard pattern
        that would match it under ILIKE must fail here."""
        response = await client.post(
            "/api/v1/auth/login",
            json={"email": "%@example.com", "password": ADMIN_PASSWORD},
        )
        assert response.status_code == 401

        response = await client.post(
            "/api/v1/auth/login",
            json={"email": "admin_example.com", "password": ADMIN_PASSWORD},
        )
        assert response.status_code in (401, 422)

    async def test_login_rejects_ambiguous_same_email_same_password_across_orgs(
        self, client, db_session
    ):
        """Two different orgs, same email, same password -- login must
        reject as ambiguous rather than silently picking the older org."""
        shared_email = "shared@example.com"
        shared_password = "sharedpassword1"

        org_a = Organization(name="Org A", subscription_tier="free")
        org_b = Organization(name="Org B", subscription_tier="free")
        db_session.add_all([org_a, org_b])
        await db_session.flush()

        db_session.add_all(
            [
                User(
                    org_id=org_a.org_id,
                    email=shared_email,
                    password_hash=hash_password(shared_password),
                    full_name="User A",
                    role="admin",
                    is_active=True,
                ),
                User(
                    org_id=org_b.org_id,
                    email=shared_email,
                    password_hash=hash_password(shared_password),
                    full_name="User B",
                    role="admin",
                    is_active=True,
                ),
            ]
        )
        await db_session.commit()

        response = await client.post(
            "/api/v1/auth/login",
            json={"email": shared_email, "password": shared_password},
        )
        assert response.status_code == 401

    async def test_login_rejects_inactive_user(self, client, db_session):
        org = Organization(name="Inactive Org", subscription_tier="free")
        db_session.add(org)
        await db_session.flush()
        user = User(
            org_id=org.org_id,
            email="inactive@example.com",
            password_hash=hash_password(ADMIN_PASSWORD),
            full_name="Inactive User",
            role="viewer",
            is_active=False,
        )
        db_session.add(user)
        await db_session.commit()

        response = await client.post(
            "/api/v1/auth/login",
            json={"email": "inactive@example.com", "password": ADMIN_PASSWORD},
        )
        assert response.status_code == 401


class TestRefreshToken:
    """Refresh token endpoint tests."""

    async def test_refresh_token_success(self, client, seeded_admin):
        login_response = await client.post(
            "/api/v1/auth/login",
            json={"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD},
        )
        refresh_token = login_response.json()["refresh_token"]

        response = await client.post(
            "/api/v1/auth/refresh",
            json={"refresh_token": refresh_token},
        )
        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert "refresh_token" in data

    async def test_refresh_invalid_token(self, client):
        response = await client.post(
            "/api/v1/auth/refresh",
            json={"refresh_token": "invalid.token.here"},
        )
        assert response.status_code == 401
        assert "Invalid" in response.json()["detail"]


class TestGetCurrentUser:
    """Get current user endpoint tests."""

    async def test_get_current_user_authenticated(self, client, seeded_admin):
        login_response = await client.post(
            "/api/v1/auth/login",
            json={"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD},
        )
        access_token = login_response.json()["access_token"]

        response = await client.get(
            "/api/v1/auth/me",
            headers={"Authorization": f"Bearer {access_token}"},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["email"] == ADMIN_EMAIL
        assert data["user_id"] == str(seeded_admin.user_id)
        assert data["role"] == "admin"

    async def test_get_current_user_unauthenticated(self, client):
        response = await client.get("/api/v1/auth/me")
        assert response.status_code == 401

    async def test_get_current_user_invalid_token(self, client):
        response = await client.get(
            "/api/v1/auth/me",
            headers={"Authorization": "Bearer invalid.token.here"},
        )
        assert response.status_code == 401


class TestLogout:
    """Logout endpoint tests."""

    async def test_logout_success(self, client, seeded_admin):
        login_response = await client.post(
            "/api/v1/auth/login",
            json={"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD},
        )
        access_token = login_response.json()["access_token"]

        response = await client.post(
            "/api/v1/auth/logout",
            headers={"Authorization": f"Bearer {access_token}"},
        )
        assert response.status_code == 200
        assert "successfully logged out" in response.json()["message"].lower()

    async def test_logout_unauthenticated(self, client):
        response = await client.post("/api/v1/auth/logout")
        assert response.status_code == 401


class TestPasswordReset:
    """Password reset endpoint tests."""

    async def test_request_password_reset_existing_email(self, client, seeded_admin):
        response = await client.post(
            "/api/v1/auth/password-reset",
            json={"email": ADMIN_EMAIL},
        )
        assert response.status_code == 200
        assert "If email exists" in response.json()["message"]

    async def test_request_password_reset_nonexistent_email(self, client, seeded_admin):
        response = await client.post(
            "/api/v1/auth/password-reset",
            json={"email": "nonexistent@example.com"},
        )
        # Should not leak whether email exists
        assert response.status_code == 200
        assert "If email exists" in response.json()["message"]

    async def test_password_reset_confirm_roundtrip(self, client, seeded_admin):
        """Full loop: build the token the endpoint would have emailed,
        confirm with a new password, then log in with it."""
        reset_token = jwt.encode(
            {
                "user_id": str(seeded_admin.user_id),
                "email": seeded_admin.email,
                "exp": datetime.utcnow() + timedelta(hours=1),
                "iat": datetime.utcnow(),
                "type": "reset",
            },
            settings.jwt_secret_key,
            algorithm=settings.jwt_algorithm,
        )

        response = await client.post(
            "/api/v1/auth/password-reset/confirm",
            json={"token": reset_token, "new_password": "brandnewpassword789"},
        )
        assert response.status_code == 200

        login_response = await client.post(
            "/api/v1/auth/login",
            json={"email": ADMIN_EMAIL, "password": "brandnewpassword789"},
        )
        assert login_response.status_code == 200


class TestChangePassword:
    """Change password endpoint tests."""

    async def test_change_password_success(self, client, seeded_admin):
        login_response = await client.post(
            "/api/v1/auth/login",
            json={"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD},
        )
        access_token = login_response.json()["access_token"]

        response = await client.post(
            "/api/v1/auth/change-password",
            json={
                "current_password": ADMIN_PASSWORD,
                "new_password": "newpassword456",
            },
            headers={"Authorization": f"Bearer {access_token}"},
        )
        assert response.status_code == 200
        assert "successfully changed" in response.json()["message"].lower()

    async def test_change_password_wrong_current(self, client, seeded_admin):
        login_response = await client.post(
            "/api/v1/auth/login",
            json={"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD},
        )
        access_token = login_response.json()["access_token"]

        response = await client.post(
            "/api/v1/auth/change-password",
            json={
                "current_password": "wrongpassword",
                "new_password": "newpassword456",
            },
            headers={"Authorization": f"Bearer {access_token}"},
        )
        assert response.status_code == 401
        assert "incorrect" in response.json()["detail"].lower()


class TestHealthEndpoint:
    """Health check endpoint tests."""

    async def test_health_check(self, client):
        response = await client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert data["service"] == "edgp-api"
