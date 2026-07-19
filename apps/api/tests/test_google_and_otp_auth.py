"""Tests for Google Sign-In and email-OTP login (both alternative login
paths for an EXISTING user matched by email -- neither self-provisions a
new org/user, same design constraint as signup())."""

from datetime import datetime, timedelta
from unittest.mock import patch

import pytest
from httpx import ASGITransport, AsyncClient

from app.auth import hash_password
from app.models.organization import Organization
from app.models.otp_code import OtpCode
from app.models.user import User
from main import app


@pytest.fixture
async def client():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as c:
        yield c


@pytest.fixture
async def seeded_user(db_session):
    org = Organization(name="SSO Test Org", subscription_tier="enterprise")
    db_session.add(org)
    await db_session.flush()

    user = User(
        org_id=org.org_id,
        email="sso@example.com",
        password_hash=hash_password("password123"),
        full_name="SSO User",
        role="admin",
        is_active=True,
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    return user


class TestOtpLogin:
    async def test_request_otp_for_unknown_email_still_returns_generic_success(self, client):
        response = await client.post(
            "/api/v1/auth/otp/request", json={"email": "nobody@example.com"}
        )
        assert response.status_code == 200
        assert "registered" in response.json()["message"].lower()

    async def test_request_and_verify_otp_success(self, client, seeded_user, db_session):
        # /otp/request doesn't return the plaintext code (it's emailed, or
        # logged when SMTP isn't configured) -- pin the RNG so the test
        # knows what code was generated instead of racing a second row
        # against it (both would get the identical transaction-scoped
        # `now()` from Postgres, making ORDER BY created_at nondeterministic).
        with patch("secrets.randbelow", return_value=654321):
            response = await client.post(
                "/api/v1/auth/otp/request", json={"email": seeded_user.email}
            )
        assert response.status_code == 200

        verify_response = await client.post(
            "/api/v1/auth/otp/verify", json={"email": seeded_user.email, "code": "654321"}
        )
        assert verify_response.status_code == 200
        body = verify_response.json()
        assert body["email"] == seeded_user.email
        assert "access_token" in body

    async def test_verify_wrong_code_rejected(self, client, seeded_user, db_session):
        otp = OtpCode(
            email=seeded_user.email.lower(),
            code_hash=hash_password("111111"),
            expires_at=datetime.utcnow() + timedelta(minutes=10),
        )
        db_session.add(otp)
        await db_session.commit()

        response = await client.post(
            "/api/v1/auth/otp/verify", json={"email": seeded_user.email, "code": "222222"}
        )
        assert response.status_code == 401

    async def test_verify_expired_code_rejected(self, client, seeded_user, db_session):
        otp = OtpCode(
            email=seeded_user.email.lower(),
            code_hash=hash_password("333333"),
            expires_at=datetime.utcnow() - timedelta(minutes=1),
        )
        db_session.add(otp)
        await db_session.commit()

        response = await client.post(
            "/api/v1/auth/otp/verify", json={"email": seeded_user.email, "code": "333333"}
        )
        assert response.status_code == 401

    async def test_verify_code_cannot_be_reused(self, client, seeded_user, db_session):
        code = "444444"
        otp = OtpCode(
            email=seeded_user.email.lower(),
            code_hash=hash_password(code),
            expires_at=datetime.utcnow() + timedelta(minutes=10),
        )
        db_session.add(otp)
        await db_session.commit()

        first = await client.post(
            "/api/v1/auth/otp/verify", json={"email": seeded_user.email, "code": code}
        )
        assert first.status_code == 200

        second = await client.post(
            "/api/v1/auth/otp/verify", json={"email": seeded_user.email, "code": code}
        )
        assert second.status_code == 401


class TestGoogleLogin:
    async def test_google_login_not_configured_returns_503(self, client):
        response = await client.post("/api/v1/auth/google", json={"id_token": "fake"})
        assert response.status_code == 503

    async def test_google_login_links_existing_user_by_email(self, client, seeded_user, db_session):
        fake_payload = {
            "sub": "google-sub-123",
            "email": seeded_user.email,
            "email_verified": True,
        }
        with patch("app.config.settings.google_client_id", "fake-client-id"), patch(
            "google.oauth2.id_token.verify_oauth2_token", return_value=fake_payload
        ):
            response = await client.post("/api/v1/auth/google", json={"id_token": "fake"})

        assert response.status_code == 200
        body = response.json()
        assert body["email"] == seeded_user.email

        await db_session.refresh(seeded_user)
        assert seeded_user.google_sub == "google-sub-123"

    async def test_google_login_unknown_email_returns_404(self, client):
        fake_payload = {
            "sub": "google-sub-999",
            "email": "unknown@example.com",
            "email_verified": True,
        }
        with patch("app.config.settings.google_client_id", "fake-client-id"), patch(
            "google.oauth2.id_token.verify_oauth2_token", return_value=fake_payload
        ):
            response = await client.post("/api/v1/auth/google", json={"id_token": "fake"})

        assert response.status_code == 404

    async def test_google_login_unverified_email_rejected(self, client, seeded_user):
        fake_payload = {
            "sub": "google-sub-123",
            "email": seeded_user.email,
            "email_verified": False,
        }
        with patch("app.config.settings.google_client_id", "fake-client-id"), patch(
            "google.oauth2.id_token.verify_oauth2_token", return_value=fake_payload
        ):
            response = await client.post("/api/v1/auth/google", json={"id_token": "fake"})

        assert response.status_code == 401

    async def test_google_login_second_time_uses_google_sub(self, client, seeded_user, db_session):
        """Once linked, a login can be identified by google_sub alone even
        if the account's email were to later diverge from the Google one."""
        seeded_user.google_sub = "google-sub-123"
        await db_session.commit()

        fake_payload = {
            "sub": "google-sub-123",
            "email": seeded_user.email,
            "email_verified": True,
        }
        with patch("app.config.settings.google_client_id", "fake-client-id"), patch(
            "google.oauth2.id_token.verify_oauth2_token", return_value=fake_payload
        ):
            response = await client.post("/api/v1/auth/google", json={"id_token": "fake"})

        assert response.status_code == 200
