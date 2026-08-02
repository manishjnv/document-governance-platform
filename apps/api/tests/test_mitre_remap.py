"""Phase 9 column-remap tests: preview headers/samples + the remap
endpoint against real edgp_test Postgres. No LLM (nothing runs)."""

import io
import uuid

import pytest
from httpx import ASGITransport, AsyncClient
from openpyxl import Workbook

from app.auth import create_access_token
from app.models.mitre_file import MitreFile
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
    """Tags live under 'Ref Codes' — not a recognized synonym, so detection
    misses them (the exact case the wizard exists for)."""
    wb = Workbook()
    ws = wb.active
    ws.title = "Rules"
    ws.append(["Rule Name", "Ref Codes", "Query"])
    ws.append(["Encoded PowerShell", "T1059.001", "proc = powershell -enc"])
    ws.append(["RDP brute force", "T1110", "logon failures > 20"])
    buf = io.BytesIO()
    wb.save(buf)
    return buf.getvalue()


async def _create(client, headers):
    res = await client.post(
        "/api/v1/mitre/assessments",
        headers=headers,
        files={"use_cases": ("rules.xlsx", _dump(), _XLSX_MIME)},
    )
    assert res.status_code == 201, res.text
    return res.json()


@pytest.mark.asyncio
async def test_preview_carries_headers_and_samples(client, db_session):
    _, _, headers = await _make_user(db_session)
    preview = await _create(client, headers)
    assert preview["headers"] == ["Rule Name", "Ref Codes", "Query"]
    assert len(preview["sample_rows"]) == 2
    assert preview["sample_rows"][0][0] == "Encoded PowerShell"
    # detection found name+logic but NOT the tags column
    assert "tags" not in preview["columns"]
    assert preview["tagged"] == 0 and preview["untagged"] == 2


@pytest.mark.asyncio
async def test_remap_reparses_and_replaces_rows(client, db_session):
    _, _, headers = await _make_user(db_session)
    preview = await _create(client, headers)
    aid = preview["assessment_id"]

    res = await client.post(
        f"/api/v1/mitre/assessments/{aid}/remap",
        headers=headers,
        json={"columns": {"name": 0, "tags": 1, "logic": 2}},
    )
    assert res.status_code == 200, res.text
    remapped = res.json()
    assert remapped["columns"] == {"name": 0, "tags": 1, "logic": 2}
    assert remapped["tagged"] == 2 and remapped["untagged"] == 0
    assert remapped["row_count"] == 2
    assert remapped["headers"] == preview["headers"]

    # rows were replaced with customer-tagged ones
    use_cases = await client.get(
        f"/api/v1/mitre/assessments/{aid}/use-cases", headers=headers
    )
    items = use_cases.json()["items"]
    assert use_cases.json()["total"] == 2
    assert {uc["mapping_status"] for uc in items} == {"customer_tagged"}
    assert sorted(m["technique_id"] for uc in items for m in uc["mappings"]) == [
        "T1059.001", "T1110",
    ]
    # persisted map updated
    got = await client.get(f"/api/v1/mitre/assessments/{aid}", headers=headers)
    assert got.json()["params"]["columns"] == {"name": 0, "tags": 1, "logic": 2}


@pytest.mark.asyncio
async def test_remap_validation_rejections(client, db_session):
    _, _, headers = await _make_user(db_session)
    aid = (await _create(client, headers))["assessment_id"]
    url = f"/api/v1/mitre/assessments/{aid}/remap"

    for payload, needle in [
        ({"columns": {"name": 0, "tags": 9}}, "out of range"),
        ({"columns": {"name": 0, "bogus": 1}}, "Unknown field"),
        ({"columns": {"tags": 1}}, "name column is required"),
        ({"columns": "nope"}, "non-empty object"),
        ({"columns": {"name": 0, "tags": 0}}, "one field"),
    ]:
        res = await client.post(url, headers=headers, json=payload)
        assert res.status_code == 422, (payload, res.text)
        assert needle in res.json()["detail"], (payload, res.json())


@pytest.mark.asyncio
async def test_remap_blocked_after_pending(client, db_session):
    from app.models.mitre_assessment import MitreAssessment

    _, _, headers = await _make_user(db_session)
    aid = (await _create(client, headers))["assessment_id"]
    assessment = await db_session.get(MitreAssessment, uuid.UUID(aid))
    assessment.status = "running"
    await db_session.commit()

    res = await client.post(
        f"/api/v1/mitre/assessments/{aid}/remap",
        headers=headers,
        json={"columns": {"name": 0}},
    )
    assert res.status_code == 409
    assert "before the assessment runs" in res.json()["detail"]


@pytest.mark.asyncio
async def test_remap_authz(client, db_session):
    _, _, headers_a = await _make_user(db_session)
    _, _, headers_b = await _make_user(db_session)
    _, _, viewer = await _make_user(db_session, role="viewer")
    aid = (await _create(client, headers_a))["assessment_id"]
    body = {"columns": {"name": 0}}

    cross = await client.post(
        f"/api/v1/mitre/assessments/{aid}/remap", headers=headers_b, json=body
    )
    assert cross.status_code == 404
    forbidden = await client.post(
        f"/api/v1/mitre/assessments/{aid}/remap", headers=viewer, json=body
    )
    assert forbidden.status_code == 403


@pytest.mark.asyncio
async def test_remap_rejected_for_extraction_dumps(client, db_session):
    _, _, headers = await _make_user(db_session)
    aid = (await _create(client, headers))["assessment_id"]
    # flip the stored file type to simulate a pdf/docx extraction assessment
    file_row = (
        await db_session.execute(
            MitreFile.__table__.select().where(MitreFile.assessment_id == uuid.UUID(aid))
        )
    ).first()
    await db_session.execute(
        MitreFile.__table__.update()
        .where(MitreFile.file_id == file_row.file_id)
        .values(file_type="pdf")
    )
    await db_session.commit()

    res = await client.post(
        f"/api/v1/mitre/assessments/{aid}/remap",
        headers=headers,
        json={"columns": {"name": 0}},
    )
    assert res.status_code == 422
    assert "spreadsheet" in res.json()["detail"]
