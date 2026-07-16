"""Tests for authentication endpoints."""

import pytest
from fastapi.testclient import TestClient

from main import app

client = TestClient(app)


class TestLogin:
    """Login endpoint tests."""

    def test_login_success(self):
        """Test successful login."""
        response = client.post(
            "/api/v1/auth/login",
            json={"email": "admin@example.com", "password": "password123"},
        )
        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert "refresh_token" in data
        assert data["email"] == "admin@example.com"
        assert data["token_type"] == "bearer"

    def test_login_invalid_email(self):
        """Test login with invalid email."""
        response = client.post(
            "/api/v1/auth/login",
            json={"email": "nonexistent@example.com", "password": "password123"},
        )
        assert response.status_code == 401
        assert "Invalid" in response.json()["detail"]

    def test_login_invalid_password(self):
        """Test login with wrong password."""
        response = client.post(
            "/api/v1/auth/login",
            json={"email": "admin@example.com", "password": "wrongpassword"},
        )
        assert response.status_code == 401
        assert "Invalid" in response.json()["detail"]

    def test_login_invalid_format(self):
        """Test login with invalid email format."""
        response = client.post(
            "/api/v1/auth/login",
            json={"email": "not-an-email", "password": "password123"},
        )
        assert response.status_code == 422  # Validation error


class TestRefreshToken:
    """Refresh token endpoint tests."""

    def test_refresh_token_success(self):
        """Test successful token refresh."""
        # First login to get refresh token
        login_response = client.post(
            "/api/v1/auth/login",
            json={"email": "admin@example.com", "password": "password123"},
        )
        refresh_token = login_response.json()["refresh_token"]

        # Now refresh
        response = client.post(
            "/api/v1/auth/refresh",
            json={"refresh_token": refresh_token},
        )
        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert "refresh_token" in data

    def test_refresh_invalid_token(self):
        """Test refresh with invalid token."""
        response = client.post(
            "/api/v1/auth/refresh",
            json={"refresh_token": "invalid.token.here"},
        )
        assert response.status_code == 401
        assert "Invalid" in response.json()["detail"]


class TestGetCurrentUser:
    """Get current user endpoint tests."""

    def test_get_current_user_authenticated(self):
        """Test getting current user when authenticated."""
        # Login first
        login_response = client.post(
            "/api/v1/auth/login",
            json={"email": "admin@example.com", "password": "password123"},
        )
        access_token = login_response.json()["access_token"]

        # Get current user
        response = client.get(
            "/api/v1/auth/me",
            headers={"Authorization": f"Bearer {access_token}"},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["email"] == "admin@example.com"
        assert data["user_id"] == 1
        assert data["role"] == "admin"

    def test_get_current_user_unauthenticated(self):
        """Test getting current user without authentication."""
        response = client.get("/api/v1/auth/me")
        assert response.status_code == 401

    def test_get_current_user_invalid_token(self):
        """Test with invalid token."""
        response = client.get(
            "/api/v1/auth/me",
            headers={"Authorization": "Bearer invalid.token.here"},
        )
        assert response.status_code == 401


class TestLogout:
    """Logout endpoint tests."""

    def test_logout_success(self):
        """Test successful logout."""
        # Login first
        login_response = client.post(
            "/api/v1/auth/login",
            json={"email": "admin@example.com", "password": "password123"},
        )
        access_token = login_response.json()["access_token"]

        # Logout
        response = client.post(
            "/api/v1/auth/logout",
            headers={"Authorization": f"Bearer {access_token}"},
        )
        assert response.status_code == 200
        assert "successfully logged out" in response.json()["message"].lower()

    def test_logout_unauthenticated(self):
        """Test logout without authentication."""
        response = client.post("/api/v1/auth/logout")
        assert response.status_code == 401


class TestPasswordReset:
    """Password reset endpoint tests."""

    def test_request_password_reset_existing_email(self):
        """Test requesting password reset for existing email."""
        response = client.post(
            "/api/v1/auth/password-reset",
            json={"email": "admin@example.com"},
        )
        assert response.status_code == 200
        assert "If email exists" in response.json()["message"]

    def test_request_password_reset_nonexistent_email(self):
        """Test requesting password reset for nonexistent email."""
        response = client.post(
            "/api/v1/auth/password-reset",
            json={"email": "nonexistent@example.com"},
        )
        # Should not leak whether email exists
        assert response.status_code == 200
        assert "If email exists" in response.json()["message"]


class TestChangePassword:
    """Change password endpoint tests."""

    def test_change_password_success(self):
        """Test successful password change."""
        # Login first
        login_response = client.post(
            "/api/v1/auth/login",
            json={"email": "admin@example.com", "password": "password123"},
        )
        access_token = login_response.json()["access_token"]

        # Change password
        response = client.post(
            "/api/v1/auth/change-password",
            json={
                "current_password": "password123",
                "new_password": "newpassword456",
            },
            headers={"Authorization": f"Bearer {access_token}"},
        )
        assert response.status_code == 200
        assert "successfully changed" in response.json()["message"].lower()

    def test_change_password_wrong_current(self):
        """Test change password with wrong current password."""
        # Login first
        login_response = client.post(
            "/api/v1/auth/login",
            json={"email": "admin@example.com", "password": "password123"},
        )
        access_token = login_response.json()["access_token"]

        # Try to change with wrong current password
        response = client.post(
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

    def test_health_check(self):
        """Test health check endpoint."""
        response = client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert data["service"] == "edgp-api"
