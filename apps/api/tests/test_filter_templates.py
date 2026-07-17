"""Tests for filter templates API.

T-2015: Save, list, delete filter templates with validation and org isolation.
"""

import pytest
from httpx import ASGITransport, AsyncClient
from uuid import uuid4

from app.auth import hash_password
from app.models.organization import Organization
from app.models.user import User
from main import app


@pytest.fixture
async def client():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as c:
        yield c


@pytest.fixture
async def seeded_users(db_session):
    """Create two orgs with users for isolation testing."""
    org1 = Organization(name="Org 1", subscription_tier="enterprise")
    org2 = Organization(name="Org 2", subscription_tier="enterprise")
    db_session.add_all([org1, org2])
    await db_session.flush()

    user1 = User(
        org_id=org1.org_id,
        email="user1@org1.com",
        password_hash=hash_password("password123"),
        full_name="User 1",
        role="admin",
        is_active=True,
    )
    user2 = User(
        org_id=org2.org_id,
        email="user2@org2.com",
        password_hash=hash_password("password123"),
        full_name="User 2",
        role="admin",
        is_active=True,
    )
    db_session.add_all([user1, user2])
    await db_session.commit()
    await db_session.refresh(user1)
    await db_session.refresh(user2)

    return {"user1": user1, "user2": user2, "org1": org1, "org2": org2}


async def login_user(client, email, password):
    """Helper to log in and return token."""
    response = await client.post(
        "/api/v1/auth/login",
        json={"email": email, "password": password},
    )
    return response.json()["access_token"]


class TestFilterTemplates:
    """Filter template CRUD tests."""

    async def test_save_filter_template_success(self, client, seeded_users):
        """Save a valid filter template."""
        token = await login_user(client, "user1@org1.com", "password123")

        response = await client.post(
            "/api/v1/filter-templates",
            json={
                "name": "My Filter",
                "filters": {
                    "document_type": "SOW",
                    "date_from": "2025-01-01",
                    "date_to": "2025-12-31",
                    "score_min": 50,
                    "score_max": 100,
                },
            },
            headers={"Authorization": f"Bearer {token}"},
        )

        assert response.status_code == 201
        data = response.json()
        assert data["name"] == "My Filter"
        assert data["filters"]["document_type"] == "SOW"
        assert data["filters"]["score_min"] == 50

    async def test_save_filter_template_validation_date_order(self, client, seeded_users):
        """Reject filter with date_from > date_to."""
        token = await login_user(client, "user1@org1.com", "password123")

        response = await client.post(
            "/api/v1/filter-templates",
            json={
                "name": "Bad Filter",
                "filters": {
                    "date_from": "2025-12-31",
                    "date_to": "2025-01-01",
                },
            },
            headers={"Authorization": f"Bearer {token}"},
        )

        assert response.status_code == 422
        assert "date_from must be on or before date_to" in str(response.json()["detail"])

    async def test_save_filter_template_validation_score_order(self, client, seeded_users):
        """Reject filter with score_min > score_max."""
        token = await login_user(client, "user1@org1.com", "password123")

        response = await client.post(
            "/api/v1/filter-templates",
            json={
                "name": "Bad Filter",
                "filters": {
                    "score_min": 80,
                    "score_max": 20,
                },
            },
            headers={"Authorization": f"Bearer {token}"},
        )

        assert response.status_code == 422
        assert "score_min must be less than or equal to score_max" in str(response.json()["detail"])

    async def test_save_filter_template_validation_document_type(self, client, seeded_users):
        """Reject filter with invalid document_type."""
        token = await login_user(client, "user1@org1.com", "password123")

        response = await client.post(
            "/api/v1/filter-templates",
            json={
                "name": "Bad Filter",
                "filters": {
                    "document_type": "InvalidType",
                },
            },
            headers={"Authorization": f"Bearer {token}"},
        )

        assert response.status_code == 422
        assert "document_type must be one of" in str(response.json()["detail"])

    async def test_list_filter_templates(self, client, seeded_users):
        """List templates for current user."""
        token = await login_user(client, "user1@org1.com", "password123")

        # Save two templates
        await client.post(
            "/api/v1/filter-templates",
            json={"name": "Filter 1", "filters": {"document_type": "SOW"}},
            headers={"Authorization": f"Bearer {token}"},
        )
        await client.post(
            "/api/v1/filter-templates",
            json={"name": "Filter 2", "filters": {"document_type": "Proposal"}},
            headers={"Authorization": f"Bearer {token}"},
        )

        response = await client.get(
            "/api/v1/filter-templates",
            headers={"Authorization": f"Bearer {token}"},
        )

        assert response.status_code == 200
        data = response.json()
        assert len(data) == 2
        assert data[0]["name"] in ["Filter 1", "Filter 2"]

    async def test_list_filter_templates_org_isolation(self, client, seeded_users):
        """Verify templates are isolated by org."""
        token1 = await login_user(client, "user1@org1.com", "password123")
        token2 = await login_user(client, "user2@org2.com", "password123")

        # User 1 saves a template
        await client.post(
            "/api/v1/filter-templates",
            json={"name": "Org1 Filter", "filters": {}},
            headers={"Authorization": f"Bearer {token1}"},
        )

        # User 2 saves a template
        await client.post(
            "/api/v1/filter-templates",
            json={"name": "Org2 Filter", "filters": {}},
            headers={"Authorization": f"Bearer {token2}"},
        )

        # User 1 lists templates -- should see only their own
        response = await client.get(
            "/api/v1/filter-templates",
            headers={"Authorization": f"Bearer {token1}"},
        )
        assert len(response.json()) == 1
        assert response.json()[0]["name"] == "Org1 Filter"

        # User 2 lists templates -- should see only their own
        response = await client.get(
            "/api/v1/filter-templates",
            headers={"Authorization": f"Bearer {token2}"},
        )
        assert len(response.json()) == 1
        assert response.json()[0]["name"] == "Org2 Filter"

    async def test_delete_filter_template(self, client, seeded_users):
        """Delete a template owned by the current user."""
        token = await login_user(client, "user1@org1.com", "password123")

        # Save template
        save_response = await client.post(
            "/api/v1/filter-templates",
            json={"name": "Temp Filter", "filters": {}},
            headers={"Authorization": f"Bearer {token}"},
        )
        template_id = save_response.json()["template_id"]

        # Delete it
        delete_response = await client.delete(
            f"/api/v1/filter-templates/{template_id}",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert delete_response.status_code == 204

        # Verify it's gone
        list_response = await client.get(
            "/api/v1/filter-templates",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert len(list_response.json()) == 0

    async def test_delete_filter_template_not_found(self, client, seeded_users):
        """Delete non-existent template returns 404."""
        token = await login_user(client, "user1@org1.com", "password123")
        fake_id = str(uuid4())

        response = await client.delete(
            f"/api/v1/filter-templates/{fake_id}",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 404
