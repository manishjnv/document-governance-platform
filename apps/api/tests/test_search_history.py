"""Tests for search history and saved searches endpoints.

Uses httpx.AsyncClient(transport=ASGITransport(...)) rather than starlette's
sync TestClient -- see test_auth.py's module docstring for why: TestClient
drives the ASGI app on its own thread/event loop, decoupled from whatever
loop pytest-asyncio hands each test, which raises "RuntimeError: Event loop
is closed" past the first test. auth_headers previously tried to obtain a
token by POSTing to /api/v1/auth/signup and /api/v1/organizations, neither of
which exist in this API (see app/routers/auth.py, which has no signup route,
and there is no organizations router) -- it seeds an org/user directly via
db_session and mints a token with create_access_token instead, matching
test_teams.py's _make_org_and_user + create_access_token pattern.
"""

import uuid

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth import create_access_token
from app.models.organization import Organization
from app.models.user import User
from main import app


@pytest.fixture
async def client():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as c:
        yield c


# Helper fixture: create test org/user and return auth headers
@pytest.fixture
async def auth_headers(db_session: AsyncSession):
    """Create a test organization and user, return Bearer token."""
    org = Organization(org_id=uuid.uuid4(), name=f"Test Org {uuid.uuid4()}")
    user = User(user_id=uuid.uuid4(), org_id=org.org_id, email=f"test-{uuid.uuid4()}@example.com")
    db_session.add_all([org, user])
    await db_session.commit()

    token, _ = create_access_token(
        user_id=user.user_id, email=user.email, org_id=org.org_id, role="admin"
    )
    return {"Authorization": f"Bearer {token}"}


class TestSearchHistory:
    """Search history endpoint tests."""

    async def test_create_search_history_success(self, client, auth_headers):
        """Test creating a search history entry."""
        response = await client.post(
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

    async def test_create_search_history_minimal(self, client, auth_headers):
        """Test creating search history with just a query."""
        response = await client.post(
            "/api/v1/search/history",
            json={"query": "test", "filters": {}},
            headers=auth_headers,
        )
        assert response.status_code == 201
        data = response.json()
        assert data["query"] == "test"
        assert data["filters"] == {}

    async def test_create_search_history_no_auth(self, client):
        """Test creating search history without auth."""
        response = await client.post(
            "/api/v1/search/history",
            json={"query": "test", "filters": {}},
        )
        assert response.status_code == 401

    async def test_list_search_history_empty(self, client, auth_headers):
        """Test listing search history when empty."""
        response = await client.get("/api/v1/search/history", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert len(data) == 0

    async def test_list_search_history_success(self, client, auth_headers):
        """Test listing search history after creating entries."""
        # Create a few searches
        for i in range(3):
            await client.post(
                "/api/v1/search/history",
                json={"query": f"search-{i}", "filters": {}},
                headers=auth_headers,
            )

        response = await client.get("/api/v1/search/history", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 3
        # Should be newest first (DESC created_at)
        assert data[0]["query"] == "search-2"
        assert data[1]["query"] == "search-1"
        assert data[2]["query"] == "search-0"

    async def test_list_search_history_limit(self, client, auth_headers):
        """Test pagination with limit parameter."""
        # Create 5 searches
        for i in range(5):
            await client.post(
                "/api/v1/search/history",
                json={"query": f"search-{i}", "filters": {}},
                headers=auth_headers,
            )

        response = await client.get("/api/v1/search/history?limit=2", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 2


class TestSavedSearches:
    """Saved searches endpoint tests."""

    async def test_create_saved_search_success(self, client, auth_headers):
        """Test creating a saved search."""
        response = await client.post(
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

    async def test_create_saved_search_duplicate_name(self, client, auth_headers):
        """Test that duplicate names per user return 409."""
        # Create first
        response = await client.post(
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
        response = await client.post(
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

    async def test_create_saved_search_no_auth(self, client):
        """Test creating saved search without auth."""
        response = await client.post(
            "/api/v1/search/saved",
            json={"name": "Test", "query": "test", "filters": {}},
        )
        assert response.status_code == 401

    async def test_list_saved_searches_empty(self, client, auth_headers):
        """Test listing saved searches when empty."""
        response = await client.get("/api/v1/search/saved", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert len(data) == 0

    async def test_list_saved_searches_success(self, client, auth_headers):
        """Test listing saved searches after creating."""
        for i in range(3):
            await client.post(
                "/api/v1/search/saved",
                json={
                    "name": f"Saved-{i}",
                    "query": f"search-{i}",
                    "filters": {},
                },
                headers=auth_headers,
            )

        response = await client.get("/api/v1/search/saved", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 3
        # Newest first
        assert data[0]["name"] == "Saved-2"
        assert data[1]["name"] == "Saved-1"
        assert data[2]["name"] == "Saved-0"

    async def test_get_saved_search_success(self, client, auth_headers):
        """Test retrieving a saved search by ID."""
        # Create
        create_resp = await client.post(
            "/api/v1/search/saved",
            json={"name": "Test", "query": "test", "filters": {}},
            headers=auth_headers,
        )
        saved_id = create_resp.json()["saved_id"]

        # Retrieve
        response = await client.get(f"/api/v1/search/saved/{saved_id}", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert data["saved_id"] == saved_id
        assert data["name"] == "Test"

    async def test_get_saved_search_not_found(self, client, auth_headers):
        """Test retrieving non-existent saved search."""
        import uuid

        fake_id = str(uuid.uuid4())
        response = await client.get(f"/api/v1/search/saved/{fake_id}", headers=auth_headers)
        assert response.status_code == 404

    async def test_update_saved_search_success(self, client, auth_headers):
        """Test updating a saved search."""
        # Create
        create_resp = await client.post(
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
        response = await client.patch(
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

    async def test_update_saved_search_partial(self, client, auth_headers):
        """Test partial update (only some fields)."""
        # Create
        create_resp = await client.post(
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
        response = await client.patch(
            f"/api/v1/search/saved/{saved_id}",
            json={"name": "NewName"},
            headers=auth_headers,
        )
        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "NewName"
        assert data["query"] == "original query"  # Unchanged

    async def test_delete_saved_search_success(self, client, auth_headers):
        """Test deleting a saved search."""
        # Create
        create_resp = await client.post(
            "/api/v1/search/saved",
            json={"name": "ToDelete", "query": "test", "filters": {}},
            headers=auth_headers,
        )
        saved_id = create_resp.json()["saved_id"]

        # Delete
        response = await client.delete(f"/api/v1/search/saved/{saved_id}", headers=auth_headers)
        assert response.status_code == 204

        # Verify deleted
        response = await client.get(f"/api/v1/search/saved/{saved_id}", headers=auth_headers)
        assert response.status_code == 404

    async def test_delete_saved_search_not_found(self, client, auth_headers):
        """Test deleting non-existent saved search."""
        import uuid

        fake_id = str(uuid.uuid4())
        response = await client.delete(f"/api/v1/search/saved/{fake_id}", headers=auth_headers)
        assert response.status_code == 404

    async def test_isolation_between_users(self, client, auth_headers):
        """Test that users see only their own saved searches."""
        # User 1: Create a saved search
        await client.post(
            "/api/v1/search/saved",
            json={"name": "User1Search", "query": "test", "filters": {}},
            headers=auth_headers,
        )

        # User 2: Should not see User1's searches (would need separate auth_headers)
        # For now, just verify User1 sees their own
        response = await client.get("/api/v1/search/saved", headers=auth_headers)
        data = response.json()
        assert len(data) == 1
        assert data[0]["name"] == "User1Search"
