"""Trigger-review guard: an unreadable document (empty/failed parse) must be
rejected with 422, not reviewed into a page of bogus findings (observed live
2026-07-23 on an image-only PDF)."""

import uuid
from datetime import datetime, timedelta

import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient

from app.db.session import get_db
from app.dependencies import get_current_user
from app.models.document import Document
from app.models.organization import Organization
from app.routers.reviews import router as reviews_router
from app.schemas.auth import TokenData


def _client(db_session, org_id):
    app = FastAPI()
    app.include_router(reviews_router)

    async def _override_get_db():
        yield db_session

    token = TokenData.model_construct(
        user_id=uuid.uuid4(),
        email="user@example.com",
        org_id=org_id,
        role="admin",
        exp=datetime.utcnow() + timedelta(hours=1),
        iat=datetime.utcnow(),
        type="access",
    )
    app.dependency_overrides[get_db] = _override_get_db
    app.dependency_overrides[get_current_user] = lambda: token
    return AsyncClient(transport=ASGITransport(app=app), base_url="http://testserver")


async def _seed_doc(db_session, parsed_text):
    org = Organization(org_id=uuid.uuid4(), name="Guard Co")
    db_session.add(org)
    await db_session.commit()
    doc = Document(
        doc_id=uuid.uuid4(),
        org_id=org.org_id,
        filename="scan.pdf",
        original_filename="scan.pdf",
        file_size_bytes=100,
        file_type="pdf",
        s3_path="org/x/doc/y/v1/scan.pdf",
        parsed_text=parsed_text,
    )
    db_session.add(doc)
    await db_session.commit()
    return org, doc


@pytest.mark.asyncio
@pytest.mark.parametrize("parsed_text", [None, "", "   ", "too short to review"])
async def test_unreadable_document_rejected_with_422(db_session, parsed_text):
    org, doc = await _seed_doc(db_session, parsed_text)
    client = _client(db_session, org.org_id)

    resp = await client.post(f"/api/v1/reviews/{doc.doc_id}/trigger")

    assert resp.status_code == 422
    assert "could not be read" in resp.json()["detail"]
