"""Tests for compliance module: retention, reporting, PII detection.

T-2043: Audit retention policies
T-2045: Compliance export
T-2049: PII detection & masking
"""

import csv
import io
import pytest
import uuid
from datetime import datetime, timedelta
from sqlalchemy.ext.asyncio import AsyncSession

from app.compliance.pii import detect_pii, mask_pii
from app.compliance.reports import export_audit_logs_csv
from app.compliance.retention import (
    get_retention_days,
    purge_expired_audit_logs,
    set_retention_days,
)
from app.models.audit_log import AuditLog
from app.models.organization import Organization
from app.models.user import User


@pytest.mark.asyncio
async def test_purge_expired_audit_logs_deletes_old_rows(db_session: AsyncSession):
    """Test that purge_expired_audit_logs only deletes rows past cutoff."""
    # Create org with 30-day retention
    org_id = uuid.uuid4()
    org = Organization(
        org_id=org_id,
        name=f"test_org_{uuid.uuid4().hex[:8]}",
        subscription_tier="pro",
        audit_retention_days=30,
    )
    db_session.add(org)
    # AuditLog.org_id is a bare FK column (no ORM relationship() to
    # Organization), so the unit-of-work can't infer insert order between
    # them -- flush the org first or the audit_logs insert can run before it.
    await db_session.flush()

    # Create audit logs: 1 within retention window, 1 past it
    now = datetime.utcnow()
    cutoff = now - timedelta(days=30)

    log_recent = AuditLog(
        org_id=org_id,
        user_id=None,
        action="test_action",
        resource_type="document",
        resource_id=None,
        details={},
        created_at=now - timedelta(days=15),  # 15 days old (within 30-day window)
    )

    log_expired = AuditLog(
        org_id=org_id,
        user_id=None,
        action="test_action",
        resource_type="document",
        resource_id=None,
        details={},
        created_at=cutoff - timedelta(days=1),  # 31 days old (past cutoff)
    )

    db_session.add(log_recent)
    db_session.add(log_expired)
    await db_session.commit()

    # Purge and verify
    deleted_count = await purge_expired_audit_logs(db_session, org_id)

    assert deleted_count == 1, "Should delete exactly 1 expired log"

    # Verify recent log still exists
    from sqlalchemy import select, and_

    query = select(AuditLog).where(
        and_(AuditLog.org_id == org_id, AuditLog.created_at >= cutoff - timedelta(days=1))
    )
    result = await db_session.execute(query)
    remaining = result.scalars().all()

    assert len(remaining) == 1, "Recent log should still exist"
    assert remaining[0].created_at == log_recent.created_at


@pytest.mark.asyncio
async def test_purge_expired_audit_logs_respects_org_isolation(db_session: AsyncSession):
    """Test that purge only deletes logs for the specified org."""
    # Create two orgs
    org_id_1 = uuid.uuid4()
    org_id_2 = uuid.uuid4()

    org1 = Organization(
        org_id=org_id_1,
        name=f"test_org_1_{uuid.uuid4().hex[:8]}",
        subscription_tier="pro",
        audit_retention_days=30,
    )
    org2 = Organization(
        org_id=org_id_2,
        name=f"test_org_2_{uuid.uuid4().hex[:8]}",
        subscription_tier="pro",
        audit_retention_days=30,
    )
    db_session.add(org1)
    db_session.add(org2)
    await db_session.flush()  # see note above: no relationship() to order on

    # Create expired logs in both orgs
    cutoff = datetime.utcnow() - timedelta(days=30)
    expired_date = cutoff - timedelta(days=1)

    log_org1 = AuditLog(
        org_id=org_id_1,
        action="test",
        resource_type="document",
        details={},
        created_at=expired_date,
    )
    log_org2 = AuditLog(
        org_id=org_id_2,
        action="test",
        resource_type="document",
        details={},
        created_at=expired_date,
    )

    db_session.add(log_org1)
    db_session.add(log_org2)
    await db_session.commit()

    # Purge org1 only
    deleted_count = await purge_expired_audit_logs(db_session, org_id_1)
    assert deleted_count == 1

    # Verify org2's log still exists
    from sqlalchemy import select

    result = await db_session.execute(
        select(AuditLog).where(AuditLog.org_id == org_id_2)
    )
    remaining = result.scalars().all()
    assert len(remaining) == 1


@pytest.mark.asyncio
async def test_get_set_retention_days(db_session: AsyncSession):
    """Test getting and setting retention policy."""
    org_id = uuid.uuid4()
    org = Organization(
        org_id=org_id,
        name=f"test_org_{uuid.uuid4().hex[:8]}",
        subscription_tier="pro",
        audit_retention_days=90,  # default
    )
    db_session.add(org)
    await db_session.commit()

    # Get default
    days = await get_retention_days(db_session, org_id)
    assert days == 90

    # Update to 30
    await set_retention_days(db_session, org_id, 30)
    days = await get_retention_days(db_session, org_id)
    assert days == 30

    # Update to 365
    await set_retention_days(db_session, org_id, 365)
    days = await get_retention_days(db_session, org_id)
    assert days == 365


@pytest.mark.asyncio
async def test_set_retention_days_rejects_invalid_values(db_session: AsyncSession):
    """Test that set_retention_days rejects invalid values."""
    org_id = uuid.uuid4()
    org = Organization(
        org_id=org_id,
        name=f"test_org_{uuid.uuid4().hex[:8]}",
        subscription_tier="pro",
    )
    db_session.add(org)
    await db_session.commit()

    with pytest.raises(ValueError, match="Invalid retention days"):
        await set_retention_days(db_session, org_id, 60)

    with pytest.raises(ValueError, match="Invalid retention days"):
        await set_retention_days(db_session, org_id, 1000)


@pytest.mark.asyncio
async def test_export_audit_logs_csv(db_session: AsyncSession):
    """Test CSV export contains expected columns and rows."""
    org_id = uuid.uuid4()
    org = Organization(
        org_id=org_id,
        name=f"test_org_{uuid.uuid4().hex[:8]}",
        subscription_tier="pro",
    )
    db_session.add(org)
    await db_session.flush()  # see note above: no relationship() to order on

    # Create audit logs
    now = datetime.utcnow()
    log1 = AuditLog(
        org_id=org_id,
        user_id=None,
        action="document_uploaded",
        resource_type="document",
        resource_id=uuid.uuid4(),
        details={"filename": "test.pdf"},
        created_at=now - timedelta(hours=1),
    )
    log2 = AuditLog(
        org_id=org_id,
        user_id=None,
        action="review_started",
        resource_type="review",
        resource_id=uuid.uuid4(),
        details={"status": "pending"},
        created_at=now,
    )

    db_session.add(log1)
    db_session.add(log2)
    await db_session.commit()

    # Export
    csv_content = await export_audit_logs_csv(db_session, org_id)

    # Parse and verify
    csv_reader = csv.DictReader(io.StringIO(csv_content))
    rows = list(csv_reader)

    assert len(rows) == 2, "Should export 2 logs"
    assert set(csv_reader.fieldnames) >= {
        "log_id",
        "created_at",
        "user_id",
        "action",
        "resource_type",
        "resource_id",
        "details",
    }, "Should have required columns"

    # Verify content
    actions = {row["action"] for row in rows}
    assert "document_uploaded" in actions
    assert "review_started" in actions


@pytest.mark.asyncio
async def test_export_audit_logs_csv_with_date_filter(db_session: AsyncSession):
    """Test CSV export respects date filters."""
    org_id = uuid.uuid4()
    org = Organization(
        org_id=org_id,
        name=f"test_org_{uuid.uuid4().hex[:8]}",
        subscription_tier="pro",
    )
    db_session.add(org)
    await db_session.flush()  # see note above: no relationship() to order on

    now = datetime.utcnow()

    # Logs at different times
    for i in range(5):
        log = AuditLog(
            org_id=org_id,
            action="test",
            resource_type="document",
            details={},
            created_at=now - timedelta(days=i),
        )
        db_session.add(log)

    await db_session.commit()

    # Export with date filter (last 2 days)
    date_from = now - timedelta(days=2)
    csv_content = await export_audit_logs_csv(db_session, org_id, date_from=date_from)

    rows = list(csv.DictReader(io.StringIO(csv_content)))
    assert len(rows) == 3, "Should export 3 logs within 2-day window"


def test_detect_pii_emails():
    """Test email detection."""
    text = "Contact john.doe@example.com for details"
    findings = detect_pii(text)

    assert len(findings) == 1
    assert findings[0]["type"] == "email"
    assert findings[0]["match"] == "john.doe@example.com"


def test_detect_pii_phone_numbers():
    """Test US phone number detection."""
    text = "Call 555-123-4567 or (555) 123-4567"
    findings = detect_pii(text)

    assert len(findings) == 2
    assert all(f["type"] == "phone" for f in findings)


def test_detect_pii_ssn():
    """Test SSN pattern detection."""
    text = "SSN is 123-45-6789"
    findings = detect_pii(text)

    assert len(findings) == 1
    assert findings[0]["type"] == "ssn"
    assert findings[0]["match"] == "123-45-6789"


def test_detect_pii_credit_card():
    """Test credit card pattern detection."""
    text = "Card number 4532-1234-5678-9010"
    findings = detect_pii(text)

    assert len(findings) == 1
    assert findings[0]["type"] == "credit_card"


def test_detect_pii_empty_text():
    """Test detection on empty text returns empty list."""
    findings = detect_pii("")
    assert findings == []

    findings = detect_pii("No sensitive data here")
    assert findings == []


def test_mask_pii_replaces_detected_patterns():
    """Test that mask_pii replaces patterns with markers."""
    text = "Email john@example.com and phone 555-123-4567"
    masked = mask_pii(text)

    assert "[EMAIL REDACTED]" in masked
    assert "[PHONE REDACTED]" in masked
    assert "john@example.com" not in masked
    assert "555-123-4567" not in masked


def test_mask_pii_no_changes_if_no_pii():
    """Test that mask_pii returns original text if no PII found."""
    text = "This is clean text with no sensitive info"
    masked = mask_pii(text)

    assert masked == text


def test_mask_pii_multiple_occurrences():
    """Test masking multiple occurrences of same PII type."""
    text = "Contact user1@example.com or user2@example.com"
    masked = mask_pii(text)

    count = masked.count("[EMAIL REDACTED]")
    assert count == 2, "Should mask both email addresses"
