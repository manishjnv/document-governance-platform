"""Tests for T-3006 pagination, T-3007 gzip, T-3008 timing header, T-3010 batch endpoint."""

import pytest
from uuid import uuid4

from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth import create_access_token
from app.core.pagination import PaginationParams, paginate
from app.models.document import Document
from app.models.enums import SubscriptionTier, UserRole
from app.models.organization import Organization
from app.models.user import User
from sqlalchemy import select


# ---------------------------------------------------------------------------
# T-3006: pagination helper
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_paginate_helper_total_and_page_size(db_session: AsyncSession):
    org = Organization(org_id=uuid4(), name="Perf Org", subscription_tier=SubscriptionTier.PRO.value)
    db_session.add(org)
    await db_session.flush()
    user = User(
        user_id=uuid4(), org_id=org.org_id, email="perf@test.example.com",
        full_name="Perf User", role=UserRole.ADMIN.value, is_active=True,
    )
    db_session.add(user)
    await db_session.flush()

    for i in range(5):
        db_session.add(Document(
            org_id=org.org_id, uploaded_by_user_id=user.user_id,
            filename=f"doc{i}.pdf", original_filename=f"doc{i}.pdf",
            file_size_bytes=100, file_type="pdf", s3_path=f"s3://bucket/doc{i}.pdf",
        ))
    await db_session.commit()

    query = select(Document).where(Document.org_id == org.org_id)
    page = await paginate(query, db_session, PaginationParams(page=1, page_size=2))

    assert page["total"] == 5
    assert page["page"] == 1
    assert page["page_size"] == 2
    assert len(page["items"]) == 2
    assert page["total_pages"] == 3


# ---------------------------------------------------------------------------
# T-3007 / T-3008: middleware (via full app)
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_response_time_header_present():
    from main import app

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://testserver") as client:
        response = await client.get("/health")

    assert response.status_code == 200
    assert "x-response-time-ms" in response.headers
    assert float(response.headers["x-response-time-ms"]) >= 0


@pytest.mark.asyncio
async def test_gzip_middleware_registered():
    from main import app
    from fastapi.middleware.gzip import GZipMiddleware

    assert any(m.cls is GZipMiddleware for m in app.user_middleware)


# ---------------------------------------------------------------------------
# T-3010: batch document endpoint
# ---------------------------------------------------------------------------

@pytest.fixture
async def batch_org_docs(db_session: AsyncSession):
    org = Organization(org_id=uuid4(), name="Batch Org", subscription_tier=SubscriptionTier.PRO.value)
    db_session.add(org)
    await db_session.flush()
    user = User(
        user_id=uuid4(), org_id=org.org_id, email="batch@test.example.com",
        full_name="Batch User", role=UserRole.ADMIN.value, is_active=True,
    )
    db_session.add(user)
    await db_session.flush()

    docs = [
        Document(
            org_id=org.org_id, uploaded_by_user_id=user.user_id,
            filename=f"batch{i}.pdf", original_filename=f"batch{i}.pdf",
            file_size_bytes=100, file_type="pdf", s3_path=f"s3://bucket/batch{i}.pdf",
        )
        for i in range(3)
    ]
    db_session.add_all(docs)
    await db_session.commit()
    for d in docs:
        await db_session.refresh(d)

    return {"org_id": org.org_id, "user_id": user.user_id, "email": user.email, "docs": docs}


@pytest.mark.asyncio
async def test_batch_endpoint_returns_matching_and_skips_invalid(batch_org_docs):
    from main import app

    access_token, _ = create_access_token(
        user_id=batch_org_docs["user_id"],
        email=batch_org_docs["email"],
        org_id=batch_org_docs["org_id"],
        role="admin",
    )
    doc_ids = [str(d.doc_id) for d in batch_org_docs["docs"][:2]]
    ids_param = ",".join(doc_ids + ["not-a-uuid", ""])

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://testserver") as client:
        response = await client.get(
            f"/api/v1/documents/batch?ids={ids_param}",
            headers={"Authorization": f"Bearer {access_token}"},
        )

    assert response.status_code == 200
    data = response.json()
    assert len(data) == 2
    assert {d["doc_id"] for d in data} == set(doc_ids)
