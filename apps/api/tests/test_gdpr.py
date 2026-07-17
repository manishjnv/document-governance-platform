"""Tests for GDPR export/delete, document retention, and encryption utility.

T-2046: document/review data retention
T-2047: GDPR data export
T-2048: GDPR right-to-be-forgotten
T-2050: encryption-at-rest utility
"""

import uuid
from datetime import datetime, timedelta

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.compliance.data_retention import (
    get_data_retention_days,
    purge_expired_documents,
    set_data_retention_days,
)
from app.compliance.encryption import decrypt_value, encrypt_value
from app.compliance.gdpr import delete_user_data, export_user_data
from app.models.document import Document
from app.models.organization import Organization
from app.models.review import Review
from app.models.user import User

# Organization.kb_articles (a concurrent parallel-agent change this wave,
# app/models/organization.py) references KBArticle only under
# TYPE_CHECKING, so nothing registers the class with the SQLAlchemy
# declarative registry at runtime unless something imports it first --
# instantiating Organization() anywhere then fails mapper configuration
# with "failed to locate a name ('KBArticle')". Importing it here (a file
# this task owns) keeps this test file self-sufficient regardless of the
# other wave's landing order.
import app.models.kb_article  # noqa: F401


async def _seed_org_user(db_session: AsyncSession):
    org = Organization(name=f"test_org_{uuid.uuid4().hex[:8]}", subscription_tier="pro")
    db_session.add(org)
    await db_session.flush()

    user = User(
        org_id=org.org_id,
        email=f"user_{uuid.uuid4().hex[:8]}@example.com",
        full_name="Test User",
        role="reviewer",
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(org)
    await db_session.refresh(user)
    return org, user


def _make_document(org_id, user_id, *, filename="doc.pdf", created_at=None):
    return Document(
        org_id=org_id,
        uploaded_by_user_id=user_id,
        filename=filename,
        original_filename=filename,
        file_size_bytes=1024,
        file_type="pdf",
        s3_path=f"orgs/{org_id}/{filename}-{uuid.uuid4().hex[:6]}",
        version=1,
        **({"created_at": created_at} if created_at else {}),
    )


async def test_export_user_data_returns_expected_structure(db_session: AsyncSession):
    org, user = await _seed_org_user(db_session)

    doc = _make_document(org.org_id, user.user_id, filename="a.pdf")
    db_session.add(doc)
    await db_session.flush()

    review = Review(
        org_id=org.org_id,
        doc_id=doc.doc_id,
        document_version=1,
        triggered_by_user_id=user.user_id,
        status="pending",
    )
    db_session.add(review)
    await db_session.commit()

    data = await export_user_data(db_session, org.org_id, user.user_id)

    assert data["user_id"] == str(user.user_id)
    assert data["org_id"] == str(org.org_id)
    assert len(data["documents"]) == 1
    assert data["documents"][0]["filename"] == "a.pdf"
    assert len(data["reviews"]) == 1
    assert data["reviews"][0]["status"] == "pending"
    assert data["findings"] == []
    assert data["comments"] == []


async def test_delete_user_data_anonymizes_without_deleting_documents(db_session: AsyncSession):
    org, user = await _seed_org_user(db_session)
    original_email = user.email

    doc = _make_document(org.org_id, user.user_id, filename="b.pdf")
    db_session.add(doc)
    await db_session.commit()
    await db_session.refresh(doc)

    summary = await delete_user_data(db_session, org.org_id, user.user_id)

    assert summary["anonymized"] is True
    assert summary["documents_retained"] == 1

    await db_session.refresh(user)
    assert user.is_active is False
    assert user.deleted_at is not None
    assert user.email != original_email
    assert user.email == summary["redacted_email"]

    # The document itself must survive untouched -- right-to-be-forgotten
    # covers the user's personal data, not org-owned content they created.
    result = await db_session.execute(select(Document).where(Document.doc_id == doc.doc_id))
    still_there = result.scalar_one()
    assert still_there.deleted_at is None
    assert still_there.uploaded_by_user_id == user.user_id


async def test_delete_user_data_missing_user_raises(db_session: AsyncSession):
    org, _ = await _seed_org_user(db_session)
    try:
        await delete_user_data(db_session, org.org_id, uuid.uuid4())
        assert False, "expected ValueError"
    except ValueError:
        pass


async def test_get_set_data_retention_days(db_session: AsyncSession):
    org, _ = await _seed_org_user(db_session)

    days = await get_data_retention_days(db_session, org.org_id)
    assert days == 365  # column default

    await set_data_retention_days(db_session, org.org_id, 180)
    days = await get_data_retention_days(db_session, org.org_id)
    assert days == 180


async def test_set_data_retention_days_rejects_invalid(db_session: AsyncSession):
    org, _ = await _seed_org_user(db_session)
    for bad in (0, -5):
        try:
            await set_data_retention_days(db_session, org.org_id, bad)
            assert False, f"expected ValueError for {bad}"
        except ValueError:
            pass


async def test_purge_expired_documents_soft_deletes_old_rows(db_session: AsyncSession):
    org, user = await _seed_org_user(db_session)
    await set_data_retention_days(db_session, org.org_id, 30)

    now = datetime.utcnow()
    old_doc = _make_document(
        org.org_id, user.user_id, filename="old.pdf", created_at=now - timedelta(days=40)
    )
    new_doc = _make_document(
        org.org_id, user.user_id, filename="new.pdf", created_at=now - timedelta(days=5)
    )
    db_session.add_all([old_doc, new_doc])
    await db_session.commit()

    purged = await purge_expired_documents(db_session, org.org_id)
    assert purged == 1

    result = await db_session.execute(select(Document).where(Document.org_id == org.org_id))
    by_name = {d.filename: d for d in result.scalars().all()}
    assert by_name["old.pdf"].deleted_at is not None
    assert by_name["new.pdf"].deleted_at is None


def test_encrypt_decrypt_roundtrip():
    plaintext = "sensitive-value-123"
    ciphertext = encrypt_value(plaintext)
    assert ciphertext != plaintext
    assert decrypt_value(ciphertext) == plaintext


def test_encrypt_value_nondeterministic_ciphertext():
    plaintext = "same-plaintext"
    c1 = encrypt_value(plaintext)
    c2 = encrypt_value(plaintext)
    assert c1 != c2, "Fernet includes a random IV/timestamp per call"
    assert decrypt_value(c1) == plaintext
    assert decrypt_value(c2) == plaintext
