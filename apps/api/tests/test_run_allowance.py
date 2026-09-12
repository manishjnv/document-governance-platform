"""Free-tier run allowance: platform admin grants a fixed number of runs;
each interactive run consumes one; at zero the org is gated again."""

import uuid

import pytest

from app.auth import create_access_token
from app.config import settings
from app.entitlements import RUNS_DISABLED_DETAIL
from app.models.document import Document
from app.models.organization import Organization
from app.models.user import User
from tests.test_admin import _make_client, _seed_org, _seed_user
from tests.test_run_entitlement import _seed_pending_assessment, client  # noqa: F401


async def _make_org_user(db_session, *, tier="free", run_allowance=0, email=None):
    org = Organization(
        org_id=uuid.uuid4(),
        name=f"org-{uuid.uuid4()}",
        subscription_tier=tier,
        run_allowance=run_allowance,
    )
    user = User(user_id=uuid.uuid4(), org_id=org.org_id, email=email or f"{uuid.uuid4()}@example.com")
    db_session.add_all([org, user])
    await db_session.commit()
    token, _ = create_access_token(
        user_id=user.user_id, email=user.email, org_id=org.org_id, role="admin"
    )
    return org, user, {"Authorization": f"Bearer {token}"}


@pytest.mark.asyncio
async def test_free_org_allowance_consumed_then_exhausted(client, db_session, monkeypatch):
    monkeypatch.setattr(settings, "require_paid_tier_for_runs", True)
    org, user, headers = await _make_org_user(db_session, tier="free", run_allowance=2)

    assessment_1 = await _seed_pending_assessment(db_session, org, user)
    resp = await client.post(f"/api/v1/mitre/assessments/{assessment_1.assessment_id}/run", headers=headers)
    assert resp.status_code == 202, resp.text
    await db_session.refresh(org)
    assert org.run_allowance == 1

    assessment_2 = await _seed_pending_assessment(db_session, org, user)
    resp = await client.post(f"/api/v1/mitre/assessments/{assessment_2.assessment_id}/run", headers=headers)
    assert resp.status_code == 202, resp.text
    await db_session.refresh(org)
    assert org.run_allowance == 0

    assessment_3 = await _seed_pending_assessment(db_session, org, user)
    resp = await client.post(f"/api/v1/mitre/assessments/{assessment_3.assessment_id}/run", headers=headers)
    assert resp.status_code == 403, resp.text
    assert resp.json()["detail"] == RUNS_DISABLED_DETAIL


@pytest.mark.asyncio
async def test_free_org_allowance_consumed_by_review_trigger(client, db_session, monkeypatch):
    monkeypatch.setattr(settings, "require_paid_tier_for_runs", True)
    org, user, headers = await _make_org_user(db_session, tier="free", run_allowance=1)
    doc = Document(
        doc_id=uuid.uuid4(),
        org_id=org.org_id,
        filename="sow.pdf",
        original_filename="sow.pdf",
        file_size_bytes=100,
        file_type="pdf",
        s3_path="org/x/doc/y/v1/sow.pdf",
        parsed_text="a" * 500,
    )
    db_session.add(doc)
    await db_session.commit()

    resp = await client.post(f"/api/v1/reviews/{doc.doc_id}/trigger", headers=headers)
    assert resp.status_code == 202, resp.text
    await db_session.refresh(org)
    assert org.run_allowance == 0


@pytest.mark.asyncio
async def test_me_shows_runs_remaining(client, db_session, monkeypatch):
    monkeypatch.setattr(settings, "require_paid_tier_for_runs", True)
    monkeypatch.setattr(settings, "platform_admin_emails", "boss@example.com")
    _, _, free_headers = await _make_org_user(db_session, tier="free", run_allowance=2)
    _, _, pro_headers = await _make_org_user(db_session, tier="pro")
    _, _, admin_headers = await _make_org_user(db_session, tier="free", email="boss@example.com")

    free_resp = await client.get("/api/v1/auth/me", headers=free_headers)
    pro_resp = await client.get("/api/v1/auth/me", headers=pro_headers)
    admin_resp = await client.get("/api/v1/auth/me", headers=admin_headers)

    assert free_resp.json()["runs_remaining"] == 2
    assert pro_resp.json()["runs_remaining"] is None
    assert admin_resp.json()["runs_remaining"] is None


@pytest.mark.asyncio
async def test_admin_patch_run_allowance(db_session, monkeypatch):
    monkeypatch.setattr(settings, "platform_admin_emails", "boss@example.com")
    org_a = await _seed_org(db_session)
    boss = await _seed_user(db_session, org_a.org_id, "admin", "boss@example.com")
    org_b = Organization(org_id=uuid.uuid4(), name="Other Org 2")
    db_session.add(org_b)
    await db_session.commit()

    admin_client = _make_client(
        db_session, org_a.org_id, role="admin", user_id=boss.user_id, email="boss@example.com"
    )

    resp = await admin_client.patch(
        f"/api/v1/admin/orgs/{org_b.org_id}/run-allowance", json={"run_allowance": 5}
    )
    assert resp.status_code == 200, resp.text
    assert resp.json()["run_allowance"] == 5

    resp = await admin_client.get("/api/v1/admin/orgs")
    body = {row["org_id"]: row for row in resp.json()}
    assert body[str(org_b.org_id)]["run_allowance"] == 5

    # Org admin (non-platform-admin) is forbidden.
    org_client = _make_client(db_session, org_a.org_id, role="admin", email="a@example.com")
    resp = await org_client.patch(
        f"/api/v1/admin/orgs/{org_b.org_id}/run-allowance", json={"run_allowance": 5}
    )
    assert resp.status_code == 403

    # Out-of-range value rejected.
    resp = await admin_client.patch(
        f"/api/v1/admin/orgs/{org_b.org_id}/run-allowance", json={"run_allowance": 1001}
    )
    assert resp.status_code == 422

    # Self-org rejected.
    resp = await admin_client.patch(
        f"/api/v1/admin/orgs/{org_a.org_id}/run-allowance", json={"run_allowance": 5}
    )
    assert resp.status_code == 400


@pytest.mark.asyncio
async def test_bulk_trigger_ignores_allowance_tier_only(client, db_session, monkeypatch):
    monkeypatch.setattr(settings, "require_paid_tier_for_runs", True)
    org, user, headers = await _make_org_user(db_session, tier="free", run_allowance=5)
    doc = Document(
        doc_id=uuid.uuid4(),
        org_id=org.org_id,
        filename="sow.pdf",
        original_filename="sow.pdf",
        file_size_bytes=100,
        file_type="pdf",
        s3_path="org/x/doc/y/v1/sow.pdf",
        parsed_text="a" * 500,
    )
    db_session.add(doc)
    await db_session.commit()

    resp = await client.post(
        "/api/v1/documents/bulk-review", json={"doc_ids": [str(doc.doc_id)]}, headers=headers
    )
    assert resp.status_code == 403, resp.text
