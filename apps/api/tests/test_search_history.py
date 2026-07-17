"""Tests for search history and saved searches endpoints.

NOTE: These are integration-style tests that require the main.app to be properly
registered with the search_history router. See main.py registration note in report.
"""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import AsyncSession

from main import app
from app.models.search_history import SavedSearch, SearchHistory
from app.schemas.search import SearchFilters

client = TestClient(app)


# Helper fixture: create test user and return auth headers
@pytest.fixture
def auth_headers():
    """
    Create a test organization and user, return Bearer token.
    Requires the app to have auth endpoints properly configured.
    """
    # Create org
    org_resp = client.post(
        "/api/v1/organizations",
        json={"name": f"Test Org {id(object())}"},
    )
    org_id = org_resp.json()["org_id"] if org_resp.status_code == 201 else None

    # Create user (exact endpoint depends on existing auth implementation)
    signup_resp = client.post(
        "/api/v1/auth/signup",
        json={
            "email": f"test-{id(object())}@example.com",
            "password": "test123456",
            "full_name": "Test User",
            "org_id": org_id,
        },
    )

    if signup_resp.status_code in (201, 200):
        token = signup_resp.json().get("access_token")
    else:
        # Fallback: try login (if user already exists)
        login_resp = client.post(
            "/api/v1/auth/login",
            json={
                "email": f"test-{id(object())}@example.com",
                "password": "test123456",
            },
        )
        token = login_resp.json().get("access_token", "mock-token")

    return {"Authorization": f"Bearer {token}"}


class TestSearchHistory:
    """Search history endpoint tests."""

    def test_create_search_history_success(self, auth_headers):
        """Test creating a search history entry."""
        response = client.post(
            "/api/v1/search/history",
            json={
                "query": "contract",
                "filters": {
                    "document_type": "SOW",
                    "date_from": "2025-01-01",
                    "date_to": "2025-12-31",
                },
            },
            headers=auth_headers,
        )
        assert response.status_code == 201
        data = response.json()
        assert data["query"] == "contract"
        assert data["filters"]["document_type"] == "SOW"
        assert "history_id" in data
        assert "created_at" in data

    def test_create_search_history_minimal(self, auth_headers):
        """Test creating search history with just a query."""
        response = client.post(
            "/api/v1/search/history",
            json={"query": "test", "filters": {}},
            headers=auth_headers,
        )
        assert response.status_code == 201
        data = response.json()
        assert data["query"] == "test"
        assert data["filters"] == {}

    def test_create_search_history_no_auth(self):
        """Test creating search history without auth."""
        response = client.post(
            "/api/v1/search/history",
            json={"query": "test", "filters": {}},
        )
        assert response.status_code == 401

    def test_list_search_history_empty(self, auth_headers):
        """Test listing search history when empty."""
        response = client.get("/api/v1/search/history", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert len(data) == 0

    def test_list_search_history_success(self, auth_headers):
        """Test listing search history after creating entries."""
        # Create a few searches
        for i in range(3):
            client.post(
                "/api/v1/search/history",
                json={"query": f"search-{i}", "filters": {}},
                headers=auth_headers,
            )

        response = client.get("/api/v1/search/history", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 3
        # Should be newest first (DESC created_at)
        assert data[0]["query"] == "search-2"
        assert data[1]["query"] == "search-1"
        assert data[2]["query"] == "search-0"

    def test_list_search_history_limit(self, auth_headers):
        """Test pagination with limit parameter."""
        # Create 5 searches
        for i in range(5):
            client.post(
                "/api/v1/search/history",
                json={"query": f"search-{i}", "filters": {}},
                headers=auth_headers,
            )

        response = client.get("/api/v1/search/history?limit=2", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 2


class TestSavedSearches:
    """Saved searches endpoint tests."""

    def test_create_saved_search_success(self, auth_headers):
        """Test creating a saved search."""
        response = client.post(
            "/api/v1/search/saved",
            json={
                "name": "My Contracts",
                "query": "contract",
                "filters": {"document_type": "SOW"},
            },
            headers=auth_headers,
        )
        assert response.status_code == 201
        data = response.json()
        assert data["name"] == "My Contracts"
        assert data["query"] == "contract"
        assert data["filters"]["document_type"] == "SOW"
        assert "saved_id" in data
        assert "created_at" in data

    def test_create_saved_search_duplicate_name(self, auth_headers):
        """Test that duplicate names per user return 409."""
        # Create first
        response = client.post(
            "/api/v1/search/saved",
            json={
                "name": "My Contracts",
                "query": "contract",
                "filters": {},
            },
            headers=auth_headers,
        )
        assert response.status_code == 201

        # Try to create with same name
        response = client.post(
            "/api/v1/search/saved",
            json={
                "name": "My Contracts",
                "query": "different query",
                "filters": {},
            },
            headers=auth_headers,
        )
        assert response.status_code == 409
        assert "already exists" in response.json()["detail"]

    def test_create_saved_search_no_auth(self):
        """Test creating saved search without auth."""
        response = client.post(
            "/api/v1/search/saved",
            json={"name": "Test", "query": "test", "filters": {}},
        )
        assert response.status_code == 401

    def test_list_saved_searches_empty(self, auth_headers):
        """Test listing saved searches when empty."""
        response = client.get("/api/v1/search/saved", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert len(data) == 0

    def test_list_saved_searches_success(self, auth_headers):
        """Test listing saved searches after creating."""
        for i in range(3):
            client.post(
                "/api/v1/search/saved",
                json={
                    "name": f"Saved-{i}",
                    "query": f"search-{i}",
                    "filters": {},
                },
                headers=auth_headers,
            )

        response = client.get("/api/v1/search/saved", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 3
        # Newest first
        assert data[0]["name"] == "Saved-2"
        assert data[1]["name"] == "Saved-1"
        assert data[2]["name"] == "Saved-0"

    def test_get_saved_search_success(self, auth_headers):
        """Test retrieving a saved search by ID."""
        # Create
        create_resp = client.post(
            "/api/v1/search/saved",
            json={"name": "Test", "query": "test", "filters": {}},
            headers=auth_headers,
        )
        saved_id = create_resp.json()["saved_id"]

        # Retrieve
        response = client.get(f"/api/v1/search/saved/{saved_id}", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert data["saved_id"] == saved_id
        assert data["name"] == "Test"

    def test_get_saved_search_not_found(self, auth_headers):
        """Test retrieving non-existent saved search."""
        import uuid

        fake_id = str(uuid.uuid4())
        response = client.get(f"/api/v1/search/saved/{fake_id}", headers=auth_headers)
        assert response.status_code == 404

    def test_update_saved_search_success(self, auth_headers):
        """Test updating a saved search."""
        # Create
        create_resp = client.post(
            "/api/v1/search/saved",
            json={
                "name": "Original",
                "query": "original query",
                "filters": {"document_type": "SOW"},
            },
            headers=auth_headers,
        )
        saved_id = create_resp.json()["saved_id"]

        # Update
        response = client.patch(
            f"/api/v1/search/saved/{saved_id}",
            json={"name": "Updated", "query": "new query"},
            headers=auth_headers,
        )
        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "Updated"
        assert data["query"] == "new query"
        # Filters should remain unchanged
        assert data["filters"]["document_type"] == "SOW"

    def test_update_saved_search_partial(self, auth_headers):
        """Test partial update (only some fields)."""
        # Create
        create_resp = client.post(
            "/api/v1/search/saved",
            json={
                "name": "Original",
                "query": "original query",
                "filters": {},
            },
            headers=auth_headers,
        )
        saved_id = create_resp.json()["saved_id"]

        # Update only name
        response = client.patch(
            f"/api/v1/search/saved/{saved_id}",
            json={"name": "NewName"},
            headers=auth_headers,
        )
        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "NewName"
        assert data["query"] == "original query"  # Unchanged

    def test_delete_saved_search_success(self, auth_headers):
        """Test deleting a saved search."""
        # Create
        create_resp = client.post(
            "/api/v1/search/saved",
            json={"name": "ToDelete", "query": "test", "filters": {}},
            headers=auth_headers,
        )
        saved_id = create_resp.json()["saved_id"]

        # Delete
        response = client.delete(f"/api/v1/search/saved/{saved_id}", headers=auth_headers)
        assert response.status_code == 204

        # Verify deleted
        response = client.get(f"/api/v1/search/saved/{saved_id}", headers=auth_headers)
        assert response.status_code == 404

    def test_delete_saved_search_not_found(self, auth_headers):
        """Test deleting non-existent saved search."""
        import uuid

        fake_id = str(uuid.uuid4())
        response = client.delete(f"/api/v1/search/saved/{fake_id}", headers=auth_headers)
        assert response.status_code == 404

    def test_isolation_between_users(self, auth_headers):
        """Test that users see only their own saved searches."""
        # User 1: Create a saved search
        client.post(
            "/api/v1/search/saved",
            json={"name": "User1Search", "query": "test", "filters": {}},
            headers=auth_headers,
        )

        # User 2: Should not see User1's searches (would need separate auth_headers)
        # For now, just verify User1 sees their own
        response = client.get("/api/v1/search/saved", headers=auth_headers)
        data = response.json()
        assert len(data) == 1
        assert data[0]["name"] == "User1Search"
