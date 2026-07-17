"""Tests for bulk review operations.

T-2013: Bulk review trigger with org isolation and per-doc status reporting.
"""

import pytest
from httpx import ASGITransport, AsyncClient
from uuid import uuid4

from app.auth import hash_password
from app.models.document import Document
from app.models.organization import Organization
from app.models.user import User
from main import app


@pytest.fixture
async def client():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as c:
        yield c


@pytest.fixture
async def seeded_docs(db_session):
    """Create two orgs with documents and users for isolation testing."""
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
    await db_session.flush()

    # Create documents for each org
    doc1_org1 = Document(
        org_id=org1.org_id,
        uploaded_by_user_id=user1.user_id,
        filename="doc1_org1.pdf",
        original_filename="doc1_org1.pdf",
        file_size_bytes=1024,
        file_type="pdf",
        s3_path="s3://bucket/doc1_org1.pdf",
        document_type="SOW",
    )
    doc2_org1 = Document(
        org_id=org1.org_id,
        uploaded_by_user_id=user1.user_id,
        filename="doc2_org1.pdf",
        original_filename="doc2_org1.pdf",
        file_size_bytes=2048,
        file_type="pdf",
        s3_path="s3://bucket/doc2_org1.pdf",
        document_type="Proposal",
    )
    doc1_org2 = Document(
        org_id=org2.org_id,
        uploaded_by_user_id=user2.user_id,
        filename="doc1_org2.pdf",
        original_filename="doc1_org2.pdf",
        file_size_bytes=1024,
        file_type="pdf",
        s3_path="s3://bucket/doc1_org2.pdf",
        document_type="Other",
    )

    db_session.add_all([doc1_org1, doc2_org1, doc1_org2])
    await db_session.commit()
    await db_session.refresh(user1)
    await db_session.refresh(user2)

    return {
        "user1": user1,
        "user2": user2,
        "org1": org1,
        "org2": org2,
        "doc1_org1": doc1_org1,
        "doc2_org1": doc2_org1,
        "doc1_org2": doc1_org2,
    }


async def login_user(client, email, password):
    """Helper to log in and return token."""
    response = await client.post(
        "/api/v1/auth/login",
        json={"email": email, "password": password},
    )
    return response.json()["access_token"]


class TestBulkReview:
    """Bulk review trigger tests."""

    async def test_bulk_review_valid_docs(self, client, seeded_docs):
        """Trigger review for valid same-org docs."""
        token = await login_user(client, "user1@org1.com", "password123")

        response = await client.post(
            "/api/v1/documents/bulk-review",
            json={
                "doc_ids": [
                    str(seeded_docs["doc1_org1"].doc_id),
                    str(seeded_docs["doc2_org1"].doc_id),
                ]
            },
            headers={"Authorization": f"Bearer {token}"},
        )

        assert response.status_code == 202
        data = response.json()
        assert "results" in data
        assert len(data["results"]) == 2

        # Both should be triggered (or running, not errored)
        for result in data["results"]:
            assert result["status"] in ["triggered", "error"]
            # Valid docs from same org should trigger
            if result["doc_id"] == str(seeded_docs["doc1_org1"].doc_id):
                assert result["status"] == "triggered"

    async def test_bulk_review_cross_org_rejection(self, client, seeded_docs):
        """Reject cross-org doc without erroring whole batch."""
        token = await login_user(client, "user1@org1.com", "password123")

        response = await client.post(
            "/api/v1/documents/bulk-review",
            json={
                "doc_ids": [
                    str(seeded_docs["doc1_org1"].doc_id),  # same org
                    str(seeded_docs["doc1_org2"].doc_id),  # different org
                ]
            },
            headers={"Authorization": f"Bearer {token}"},
        )

        assert response.status_code == 202
        data = response.json()
        results_by_id = {r["doc_id"]: r for r in data["results"]}

        # Same-org doc should trigger
        assert results_by_id[str(seeded_docs["doc1_org1"].doc_id)]["status"] == "triggered"

        # Cross-org doc should error
        assert results_by_id[str(seeded_docs["doc1_org2"].doc_id)]["status"] == "error"
        assert "access denied" in results_by_id[str(seeded_docs["doc1_org2"].doc_id)]["detail"].lower()

    async def test_bulk_review_invalid_uuid(self, client, seeded_docs):
        """Handle invalid UUID format gracefully."""
        token = await login_user(client, "user1@org1.com", "password123")

        response = await client.post(
            "/api/v1/documents/bulk-review",
            json={
                "doc_ids": [
                    str(seeded_docs["doc1_org1"].doc_id),
                    "not-a-uuid",
                ]
            },
            headers={"Authorization": f"Bearer {token}"},
        )

        assert response.status_code == 202
        data = response.json()
        results_by_id = {r["doc_id"]: r for r in data["results"]}

        # Valid doc should trigger
        assert results_by_id[str(seeded_docs["doc1_org1"].doc_id)]["status"] == "triggered"

        # Invalid UUID should error
        assert results_by_id["not-a-uuid"]["status"] == "error"
        assert "Invalid UUID format" in results_by_id["not-a-uuid"]["detail"]

    async def test_bulk_review_empty_list(self, client, seeded_docs):
        """Reject empty doc_ids list."""
        token = await login_user(client, "user1@org1.com", "password123")

        response = await client.post(
            "/api/v1/documents/bulk-review",
            json={"doc_ids": []},
            headers={"Authorization": f"Bearer {token}"},
        )

        assert response.status_code == 422

    async def test_bulk_review_missing_field(self, client, seeded_docs):
        """Reject request missing doc_ids field."""
        token = await login_user(client, "user1@org1.com", "password123")

        response = await client.post(
            "/api/v1/documents/bulk-review",
            json={},
            headers={"Authorization": f"Bearer {token}"},
        )

        assert response.status_code == 422

    async def test_bulk_review_nonexistent_doc(self, client, seeded_docs):
        """Handle nonexistent doc_id gracefully."""
        token = await login_user(client, "user1@org1.com", "password123")
        fake_id = str(uuid4())

        response = await client.post(
            "/api/v1/documents/bulk-review",
            json={
                "doc_ids": [
                    str(seeded_docs["doc1_org1"].doc_id),
                    fake_id,
                ]
            },
            headers={"Authorization": f"Bearer {token}"},
        )

        assert response.status_code == 202
        data = response.json()
        results_by_id = {r["doc_id"]: r for r in data["results"]}

        # Valid doc should trigger
        assert results_by_id[str(seeded_docs["doc1_org1"].doc_id)]["status"] == "triggered"

        # Nonexistent doc should error
        assert results_by_id[fake_id]["status"] == "error"
