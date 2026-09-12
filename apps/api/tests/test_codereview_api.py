"""API tests for the Code Security Review module (isolated, no LLM).

Real edgp_test Postgres (apply migrations/039_code_review.sql first).
Same fixture pattern as test_mitre_api.py.
"""

import importlib.util
import io
import uuid
import zipfile
from pathlib import Path

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth import create_access_token
from app.codereview import ingest
from app.models.organization import Organization
from app.models.user import User
from main import app

SAMPLE_DIR = Path(__file__).resolve().parents[3] / "docs/sample/CodeReview_Sample"
REPORTS_PRESENT = (
    importlib.util.find_spec("app.codereview.report_xlsx") is not None
    and importlib.util.find_spec("app.codereview.report_pptx") is not None
)


def _sample(name: str) -> bytes:
    return (SAMPLE_DIR / name).read_bytes()


@pytest.fixture
async def client():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as c:
        yield c


async def _make_user(db_session: AsyncSession, *, role="admin", email=None):
    org = Organization(org_id=uuid.uuid4(), name=f"org-{uuid.uuid4()}")
    user = User(user_id=uuid.uuid4(), org_id=org.org_id, email=email or f"{uuid.uuid4()}@example.com")
    db_session.add_all([org, user])
    await db_session.commit()
    token, _ = create_access_token(
        user_id=user.user_id, email=user.email, org_id=org.org_id, role=role
    )
    return org, user, {"Authorization": f"Bearer {token}"}


async def _create(client, headers, *, with_manifest=True):
    files = {"report": ("acme_findings.json", _sample("acme_findings.json"), "application/json")}
    if with_manifest:
        files["manifest"] = (
            "acme_run_manifest.json",
            _sample("acme_run_manifest.json"),
            "application/json",
        )
    response = await client.post(
        "/api/v1/codereview/reviews",
        headers=headers,
        files=files,
        data={"name": "Acme payments API scan"},
    )
    assert response.status_code == 201, response.text
    return response.json()


@pytest.mark.asyncio
async def test_create_and_get_review(client, db_session):
    _, _, headers = await _make_user(db_session)
    body = await _create(client, headers)
    assert body["name"] == "Acme payments API scan"
    assert body["source_format"] == "findings"
    assert body["git_sha"] == "3f9c2a1"
    assert body["report"]["counts"]["total"] == 12

    detail = await client.get(f"/api/v1/codereview/reviews/{body['review_id']}", headers=headers)
    assert detail.status_code == 200
    assert detail.json()["report"]["counts"]["total"] == 12


@pytest.mark.asyncio
async def test_list_shows_created_review(client, db_session):
    _, _, headers = await _make_user(db_session)
    created = await _create(client, headers)

    listed = await client.get("/api/v1/codereview/reviews", headers=headers)
    assert listed.status_code == 200
    ids = [row["review_id"] for row in listed.json()]
    assert created["review_id"] in ids


@pytest.mark.asyncio
async def test_org_isolation_get_and_delete(client, db_session):
    _, _, headers_a = await _make_user(db_session)
    created = await _create(client, headers_a)

    _, _, headers_b = await _make_user(db_session)
    other_get = await client.get(f"/api/v1/codereview/reviews/{created['review_id']}", headers=headers_b)
    assert other_get.status_code == 404

    other_delete = await client.delete(
        f"/api/v1/codereview/reviews/{created['review_id']}", headers=headers_b
    )
    assert other_delete.status_code == 404


@pytest.mark.asyncio
async def test_viewer_role_forbidden_on_create(client, db_session):
    _, _, headers = await _make_user(db_session, role="viewer")
    files = {"report": ("acme_findings.json", _sample("acme_findings.json"), "application/json")}
    response = await client.post(
        "/api/v1/codereview/reviews", headers=headers, files=files, data={"name": "x"}
    )
    assert response.status_code == 403


@pytest.mark.asyncio
async def test_oversize_report_rejected(client, db_session, monkeypatch):
    _, _, headers = await _make_user(db_session)
    monkeypatch.setattr(ingest, "MAX_REPORT_BYTES", 10)
    files = {"report": ("acme_findings.json", _sample("acme_findings.json"), "application/json")}
    response = await client.post(
        "/api/v1/codereview/reviews", headers=headers, files=files, data={"name": "x"}
    )
    assert response.status_code == 413


@pytest.mark.asyncio
async def test_garbage_report_rejected(client, db_session):
    _, _, headers = await _make_user(db_session)
    files = {"report": ("bad.json", b"not json at all", "application/json")}
    response = await client.post(
        "/api/v1/codereview/reviews", headers=headers, files=files, data={"name": "x"}
    )
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_delete_then_404(client, db_session):
    _, _, headers = await _make_user(db_session)
    created = await _create(client, headers)

    deleted = await client.delete(f"/api/v1/codereview/reviews/{created['review_id']}", headers=headers)
    assert deleted.status_code == 204

    after = await client.get(f"/api/v1/codereview/reviews/{created['review_id']}", headers=headers)
    assert after.status_code == 404


@pytest.mark.skipif(not REPORTS_PRESENT, reason="report_xlsx/report_pptx not implemented yet")
@pytest.mark.asyncio
async def test_export_xlsx(client, db_session):
    _, _, headers = await _make_user(db_session)
    created = await _create(client, headers)
    response = await client.get(
        f"/api/v1/codereview/reviews/{created['review_id']}/export.xlsx", headers=headers
    )
    assert response.status_code == 200
    assert response.headers["content-type"] == (
        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )


def _zip_bytes(entries: dict) -> bytes:
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        for name, data in entries.items():
            zf.writestr(name, data)
    return buf.getvalue()


async def _post_zip(client, headers, raw_zip: bytes, filename="scopewise-scan-acme-20260911.zip"):
    files = {"report": (filename, raw_zip, "application/zip")}
    return await client.post(
        "/api/v1/codereview/reviews", headers=headers, files=files, data={"name": "zip scan"}
    )


@pytest.mark.asyncio
async def test_scan_kit_zip_round_trip(client, db_session):
    _, _, headers = await _make_user(db_session)
    raw_zip = _zip_bytes(
        {
            "findings.json": _sample("acme_findings.json"),
            "run_manifest_20260911T000000Z.json": _sample("acme_run_manifest.json"),
        }
    )
    response = await _post_zip(client, headers, raw_zip)
    assert response.status_code == 201, response.text
    body = response.json()
    assert body["source_format"] == "findings"
    assert body["report"]["manifest"] is not None
    assert body["report"]["counts"]["total"] == 12


@pytest.mark.asyncio
async def test_scan_kit_zip_too_many_entries_rejected(client, db_session):
    _, _, headers = await _make_user(db_session)
    raw_zip = _zip_bytes({f"f{i}.txt": b"x" for i in range(51)})
    response = await _post_zip(client, headers, raw_zip)
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_scan_kit_zip_path_traversal_rejected(client, db_session):
    _, _, headers = await _make_user(db_session)
    raw_zip = _zip_bytes(
        {
            "findings.json": _sample("acme_findings.json"),
            "../evil.json": b"{}",
        }
    )
    response = await _post_zip(client, headers, raw_zip)
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_scan_kit_zip_oversize_member_rejected(client, db_session):
    _, _, headers = await _make_user(db_session)
    raw_zip = _zip_bytes(
        {
            "findings.json": _sample("acme_findings.json"),
            "big.bin": b"\x00" * (11 * 1024 * 1024),
        }
    )
    response = await _post_zip(client, headers, raw_zip)
    assert response.status_code in (422, 413)


@pytest.mark.asyncio
async def test_scan_kit_zip_no_report_rejected(client, db_session):
    _, _, headers = await _make_user(db_session)
    raw_zip = _zip_bytes({"README.txt": b"nothing useful here"})
    response = await _post_zip(client, headers, raw_zip)
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_scan_kit_zip_sarif_fallback(client, db_session):
    _, _, headers = await _make_user(db_session)
    raw_zip = _zip_bytes({"acme_findings.sarif": _sample("acme_findings.sarif")})
    response = await _post_zip(client, headers, raw_zip)
    assert response.status_code == 201, response.text
    assert response.json()["source_format"] == "sarif"


@pytest.mark.skipif(not REPORTS_PRESENT, reason="report_xlsx/report_pptx not implemented yet")
@pytest.mark.asyncio
async def test_export_pptx(client, db_session):
    _, _, headers = await _make_user(db_session)
    created = await _create(client, headers)
    response = await client.get(
        f"/api/v1/codereview/reviews/{created['review_id']}/export.pptx", headers=headers
    )
    assert response.status_code == 200
    assert response.headers["content-type"] == (
        "application/vnd.openxmlformats-officedocument.presentationml.presentation"
    )


async def test_kit_zip_endpoint(client, db_session):
    """GET /kit.zip streams a zip with the kit files for any authenticated user."""
    import io
    import zipfile

    _, _, headers = await _make_user(db_session, role="viewer")
    response = await client.get("/api/v1/codereview/kit.zip", headers=headers)
    assert response.status_code == 200
    assert response.headers["content-type"].startswith("application/zip")
    names = zipfile.ZipFile(io.BytesIO(response.content)).namelist()
    for name in ("README.md", "config.yaml", "setup.cmd", "setup.sh", "scopewise-scan.cmd", "scopewise-scan.sh", "bin/setup.ps1", "bin/scopewise-scan.ps1"):
        assert f"scopewise-scan-kit/{name}" in names
    assert any(n.endswith(".whl") for n in names)


async def test_demo_review_visible_read_only_to_other_org(client, db_session, monkeypatch):
    """A review id listed in CODEREVIEW_DEMO_REVIEW_IDS is listed, viewable and
    exportable by a user from another org, but not renamable or deletable."""
    _, _, owner = await _make_user(db_session)
    created = await _create(client, owner, with_manifest=False)
    rid = created["review_id"]
    _, _, other = await _make_user(db_session, role="viewer")

    # not visible before the flag
    assert (await client.get(f"/api/v1/codereview/reviews/{rid}", headers=other)).status_code == 404

    monkeypatch.setenv("CODEREVIEW_DEMO_REVIEW_IDS", f" {rid} ,not-a-uuid")
    listed = (await client.get("/api/v1/codereview/reviews", headers=other)).json()
    match = [r for r in listed if r["review_id"] == rid]
    assert match and match[0]["demo"] is True and match[0]["editable"] is False
    detail = await client.get(f"/api/v1/codereview/reviews/{rid}", headers=other)
    assert detail.status_code == 200 and detail.json()["editable"] is False
    assert (await client.get(f"/api/v1/codereview/reviews/{rid}/export.xlsx", headers=other)).status_code == 200
    # owner still sees it as editable; other org cannot change it
    assert (await client.get(f"/api/v1/codereview/reviews/{rid}", headers=owner)).json()["editable"] is True
    _, _, other_admin = await _make_user(db_session, role="admin")
    assert (await client.patch(f"/api/v1/codereview/reviews/{rid}", json={"name": "x"}, headers=other_admin)).status_code == 404
    assert (await client.delete(f"/api/v1/codereview/reviews/{rid}", headers=other_admin)).status_code == 404
