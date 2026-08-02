"""Phase 10 per-mapping override tests: PATCH .../use-cases/{id}/mappings
against real edgp_test Postgres. No LLM (nothing runs — assessments are
completed by hand so only the pure recompute path executes)."""

import io
import uuid
from datetime import datetime, timezone

import pytest
from httpx import ASGITransport, AsyncClient
from openpyxl import Workbook
from sqlalchemy import select

from app.auth import create_access_token
from app.models.audit_log import AuditLog
from app.models.mitre_assessment import MitreAssessment
from app.models.organization import Organization
from app.models.user import User
from main import app

_XLSX_MIME = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"


@pytest.fixture
async def client():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as c:
        yield c


async def _make_user(db_session, *, role="admin"):
    org = Organization(org_id=uuid.uuid4(), name=f"org-{uuid.uuid4()}")
    user = User(user_id=uuid.uuid4(), org_id=org.org_id, email=f"{uuid.uuid4()}@x.com")
    db_session.add_all([org, user])
    await db_session.commit()
    token, _ = create_access_token(
        user_id=user.user_id, email=user.email, org_id=org.org_id, role=role
    )
    return org, user, {"Authorization": f"Bearer {token}"}


def _dump() -> bytes:
    wb = Workbook()
    ws = wb.active
    ws.title = "Rules"
    ws.append(["Rule Name", "MITRE ATT&CK", "Query"])
    ws.append(["Encoded PowerShell", "T1059.001", "proc = powershell -enc"])
    ws.append(["RDP brute force", "T1110", "logon failures > 20"])
    buf = io.BytesIO()
    wb.save(buf)
    return buf.getvalue()


async def _completed_assessment(client, db_session, headers) -> str:
    """Create via the API (customer-tagged rows), then hand-complete it so
    the PATCH's recompute path is exercised without running the pipeline."""
    res = await client.post(
        "/api/v1/mitre/assessments",
        headers=headers,
        files={"use_cases": ("rules.xlsx", _dump(), _XLSX_MIME)},
    )
    assert res.status_code == 201, res.text
    aid = res.json()["assessment_id"]
    assessment = await db_session.get(MitreAssessment, uuid.UUID(aid))
    assessment.status = "completed"
    assessment.completed_at = datetime.now(timezone.utc)
    await db_session.commit()
    return aid


async def _use_cases_by_name(client, aid, headers) -> dict:
    res = await client.get(f"/api/v1/mitre/assessments/{aid}/use-cases", headers=headers)
    return {uc["name"]: uc for uc in res.json()["items"]}


@pytest.mark.asyncio
async def test_edit_sets_manual_provenance_and_recomputes(client, db_session):
    _, _, headers = await _make_user(db_session)
    aid = await _completed_assessment(client, db_session, headers)
    ucs = await _use_cases_by_name(client, aid, headers)
    target = ucs["Encoded PowerShell"]

    res = await client.patch(
        f"/api/v1/mitre/assessments/{aid}/use-cases/{target['use_case_id']}/mappings",
        headers=headers,
        json={"technique_ids": ["t1566"]},  # lowercase on purpose — normalized
    )
    assert res.status_code == 200, res.text
    body = res.json()
    assert body["use_case"]["mapping_status"] == "manual"
    assert body["use_case"]["mappings"] == [
        {"technique_id": "T1566", "source": "manual", "confidence": 1.0}
    ]
    assert body["overall"]["covered"] >= 1

    got = (await client.get(f"/api/v1/mitre/assessments/{aid}", headers=headers)).json()
    states = {r["technique_id"]: r["state"] for r in got["technique_results"]}
    # the edit moved this rule off T1059.001 and onto T1566
    assert states["T1566"] == "covered"
    assert states["T1059.001"] == "not_covered"
    assert states["T1110"] == "covered"  # untouched rule still counts
    counts = got["summary"]["counts"]
    assert counts["manual"] == 1 and counts["customer_tagged"] == 1
    assert any("manually edited" in a for a in got["summary"]["assumptions"])

    # audit row written
    log = (
        await db_session.execute(
            select(AuditLog).where(AuditLog.action == "mitre.mappings_edited")
        )
    ).scalars().first()
    assert log is not None
    assert str(log.resource_id) == aid and log.resource_type == "mitre_assessment"


@pytest.mark.asyncio
async def test_empty_list_unmaps_the_rule(client, db_session):
    _, _, headers = await _make_user(db_session)
    aid = await _completed_assessment(client, db_session, headers)
    ucs = await _use_cases_by_name(client, aid, headers)

    res = await client.patch(
        f"/api/v1/mitre/assessments/{aid}/use-cases/{ucs['RDP brute force']['use_case_id']}/mappings",
        headers=headers,
        json={"technique_ids": []},
    )
    assert res.status_code == 200, res.text
    assert res.json()["use_case"]["mappings"] == []

    got = (await client.get(f"/api/v1/mitre/assessments/{aid}", headers=headers)).json()
    states = {r["technique_id"]: r["state"] for r in got["technique_results"]}
    assert states["T1110"] == "not_covered"


@pytest.mark.asyncio
async def test_invalid_ids_rejected(client, db_session):
    _, _, headers = await _make_user(db_session)
    aid = await _completed_assessment(client, db_session, headers)
    ucs = await _use_cases_by_name(client, aid, headers)
    url = f"/api/v1/mitre/assessments/{aid}/use-cases/{ucs['RDP brute force']['use_case_id']}/mappings"

    for payload, needle in [
        ({"technique_ids": ["T9999"]}, "Not valid"),
        ({"technique_ids": ["not-an-id"]}, "Not valid"),
        ({"technique_ids": "T1110"}, "must be a list"),
        ({"technique_ids": ["T1110"] * 21}, "at most"),
    ]:
        res = await client.patch(url, headers=headers, json=payload)
        assert res.status_code == 422, (payload, res.text)
        assert needle in res.json()["detail"], (payload, res.json())

    # nothing changed
    ucs = await _use_cases_by_name(client, aid, headers)
    assert ucs["RDP brute force"]["mapping_status"] == "customer_tagged"


@pytest.mark.asyncio
async def test_blocked_unless_completed(client, db_session):
    _, _, headers = await _make_user(db_session)
    res = await client.post(
        "/api/v1/mitre/assessments",
        headers=headers,
        files={"use_cases": ("rules.xlsx", _dump(), _XLSX_MIME)},
    )
    aid = res.json()["assessment_id"]  # still pending
    ucs = await _use_cases_by_name(client, aid, headers)

    res = await client.patch(
        f"/api/v1/mitre/assessments/{aid}/use-cases/{ucs['RDP brute force']['use_case_id']}/mappings",
        headers=headers,
        json={"technique_ids": ["T1110"]},
    )
    assert res.status_code == 409
    assert "completed" in res.json()["detail"]


@pytest.mark.asyncio
async def test_authz(client, db_session):
    _, _, headers_a = await _make_user(db_session)
    _, _, headers_b = await _make_user(db_session)
    _, _, viewer = await _make_user(db_session, role="viewer")
    aid = await _completed_assessment(client, db_session, headers_a)
    ucs = await _use_cases_by_name(client, aid, headers_a)
    url = f"/api/v1/mitre/assessments/{aid}/use-cases/{ucs['RDP brute force']['use_case_id']}/mappings"
    body = {"technique_ids": ["T1110"]}

    cross = await client.patch(url, headers=headers_b, json=body)
    assert cross.status_code == 404
    forbidden = await client.patch(url, headers=viewer, json=body)
    assert forbidden.status_code == 403

    # cross-org use_case_id under the attacker's OWN completed assessment
    # must also 404 (the use-case query is assessment- AND org-scoped)
    aid_b = await _completed_assessment(client, db_session, headers_b)
    spoof = await client.patch(
        f"/api/v1/mitre/assessments/{aid_b}/use-cases/{ucs['RDP brute force']['use_case_id']}/mappings",
        headers=headers_b,
        json=body,
    )
    assert spoof.status_code == 404
