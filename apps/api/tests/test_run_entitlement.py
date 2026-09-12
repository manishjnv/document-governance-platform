"""Per-org entitlement gate for LLM-spending run actions: free-tier orgs
get 403 on review/assessment trigger endpoints; pro/enterprise and platform
admins pass through unchanged."""

import io
import uuid
from datetime import datetime, timedelta, timezone

import pytest
from httpx import ASGITransport, AsyncClient
from openpyxl import Workbook

from app.auth import create_access_token
from app.config import settings
from app.entitlements import RUNS_DISABLED_DETAIL, runs_enabled
from app.models.document import Document
from app.models.mitre_assessment import MitreAssessment
from app.models.organization import Organization
from app.models.user import User
from main import app


@pytest.fixture(autouse=True)
def _no_llm(monkeypatch):
    from app.mitre import agents

    async def fake_tag(rows, **kwargs):
        return {
            "mappings_by_ref": {},
            "assumptions": [],
            "models_used": [],
            "batches_total": 1 if rows else 0,
            "batches_failed": 0,
        }

    async def fake_narrative(computed, **kwargs):
        return {
            "narrative": agents.build_template_narrative(computed),
            "generated_by": "template",
            "model_used": None,
        }

    monkeypatch.setattr(agents, "tag_untagged_rows", fake_tag)
    monkeypatch.setattr(agents, "generate_narrative", fake_narrative)


@pytest.fixture
async def client():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as c:
        yield c


async def _make_org_user(db_session, *, tier="free", email=None):
    org = Organization(org_id=uuid.uuid4(), name=f"org-{uuid.uuid4()}", subscription_tier=tier)
    user = User(user_id=uuid.uuid4(), org_id=org.org_id, email=email or f"{uuid.uuid4()}@example.com")
    db_session.add_all([org, user])
    await db_session.commit()
    token, _ = create_access_token(
        user_id=user.user_id, email=user.email, org_id=org.org_id, role="admin"
    )
    return org, user, {"Authorization": f"Bearer {token}"}


def _xlsx_dump():
    wb = Workbook()
    ws = wb.active
    ws.title = "Rules"
    ws.append(["Use Case Name", "MITRE Technique(s)", "Detection Logic", "Description", "Log Source", "Status"])
    ws.append(["PowerShell Encoded", "T1059.001", "process where ...", "", "Sysmon", "Enabled"])
    buf = io.BytesIO()
    wb.save(buf)
    return buf.getvalue()


_XLSX_MIME = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"


async def _seed_pending_assessment(db_session, org, user):
    assessment = MitreAssessment(
        assessment_id=uuid.uuid4(),
        org_id=org.org_id,
        name="Q3 SOC coverage",
        status="pending",
        attack_version="19.1",
        params={"intake": {}},
        created_by=user.user_id,
    )
    db_session.add(assessment)
    await db_session.commit()
    return assessment


@pytest.mark.asyncio
async def test_free_org_review_trigger_403(client, db_session, monkeypatch):
    monkeypatch.setattr(settings, "require_paid_tier_for_runs", True)
    org, user, headers = await _make_org_user(db_session, tier="free")
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

    assert resp.status_code == 403, resp.text
    assert resp.json()["detail"] == RUNS_DISABLED_DETAIL


@pytest.mark.asyncio
async def test_free_org_mitre_run_403(client, db_session, monkeypatch):
    monkeypatch.setattr(settings, "require_paid_tier_for_runs", True)
    org, user, headers = await _make_org_user(db_session, tier="free")
    assessment = await _seed_pending_assessment(db_session, org, user)

    resp = await client.post(f"/api/v1/mitre/assessments/{assessment.assessment_id}/run", headers=headers)

    assert resp.status_code == 403, resp.text
    assert resp.json()["detail"] == RUNS_DISABLED_DETAIL


@pytest.mark.asyncio
async def test_pro_org_mitre_run_202(client, db_session, monkeypatch):
    monkeypatch.setattr(settings, "require_paid_tier_for_runs", True)
    org, user, headers = await _make_org_user(db_session, tier="pro")
    assessment = await _seed_pending_assessment(db_session, org, user)

    resp = await client.post(f"/api/v1/mitre/assessments/{assessment.assessment_id}/run", headers=headers)

    assert resp.status_code == 202, resp.text


@pytest.mark.asyncio
async def test_free_org_platform_admin_email_202(client, db_session, monkeypatch):
    monkeypatch.setattr(settings, "require_paid_tier_for_runs", True)
    admin_email = "runs-admin@example.com"
    monkeypatch.setattr(settings, "platform_admin_emails", admin_email)
    org, user, headers = await _make_org_user(db_session, tier="free", email=admin_email)
    assessment = await _seed_pending_assessment(db_session, org, user)

    resp = await client.post(f"/api/v1/mitre/assessments/{assessment.assessment_id}/run", headers=headers)

    assert resp.status_code == 202, resp.text


@pytest.mark.asyncio
async def test_me_reflects_assessments_enabled(client, db_session, monkeypatch):
    monkeypatch.setattr(settings, "require_paid_tier_for_runs", True)
    _, _, free_headers = await _make_org_user(db_session, tier="free")
    _, _, pro_headers = await _make_org_user(db_session, tier="pro")

    free_resp = await client.get("/api/v1/auth/me", headers=free_headers)
    pro_resp = await client.get("/api/v1/auth/me", headers=pro_headers)

    assert free_resp.status_code == 200, free_resp.text
    assert pro_resp.status_code == 200, pro_resp.text
    assert free_resp.json()["assessments_enabled"] is False
    assert pro_resp.json()["assessments_enabled"] is True


def test_runs_enabled_true_for_everyone_when_flag_off(monkeypatch):
    monkeypatch.setattr(settings, "require_paid_tier_for_runs", False)
    assert runs_enabled(subscription_tier="free", email="nobody@example.com") is True
