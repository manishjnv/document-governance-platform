"""API + pipeline E2E tests for the MITRE assessment module (Phase 1).

Real edgp_test Postgres (apply migrations/029_mitre_assessment.sql first),
real ATT&CK v19.1 dataset, no LLM anywhere (Phase 1 is tagged-only).
"""

import asyncio
import io
import uuid
from datetime import datetime, timedelta, timezone

import pytest
from httpx import ASGITransport, AsyncClient
from openpyxl import Workbook
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth import create_access_token
from app.mitre import agents
from app.mitre.attack_data import DEFAULT
from app.mitre.router import STALE_RUN_MESSAGE
from app.mitre.service import build_mappings
from app.models.mitre_assessment import MitreAssessment
from app.models.mitre_use_case import MitreUseCase
from app.models.organization import Organization
from app.models.user import User
from main import app


@pytest.fixture(autouse=True)
def _no_llm(monkeypatch):
    """Phase 2 wired real LLM stages into the run pipeline — stub them so
    these API tests stay deterministic and never call OpenRouter (a local
    .env may carry a real key)."""

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


async def _make_user(db_session: AsyncSession, *, role="admin", email=None):
    org = Organization(org_id=uuid.uuid4(), name=f"org-{uuid.uuid4()}")
    user = User(user_id=uuid.uuid4(), org_id=org.org_id, email=email or f"{uuid.uuid4()}@example.com")
    db_session.add_all([org, user])
    await db_session.commit()
    token, _ = create_access_token(
        user_id=user.user_id, email=user.email, org_id=org.org_id, role=role
    )
    return org, user, {"Authorization": f"Bearer {token}"}


def _xlsx(rows, sheet_name="Sheet1", extra_sheets=()) -> bytes:
    wb = Workbook()
    ws = wb.active
    ws.title = sheet_name
    for row in rows:
        ws.append(row)
    for name, extra_rows in extra_sheets:
        extra = wb.create_sheet(name)
        for row in extra_rows:
            extra.append(row)
    buf = io.BytesIO()
    wb.save(buf)
    return buf.getvalue()


_XLSX_MIME = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"


def _dump_files(env=True):
    dump = _xlsx([
        ["Use Case Name", "MITRE Technique(s)", "Detection Logic", "Description", "Log Source", "Status"],
        ["PowerShell Encoded", "T1059.001", "process where ...", "", "Sysmon", "Enabled"],
        ["RDP Watch", "T1021.001", "logon type 10", "", "WinEventLog", "Disabled"],
        ["Untagged anomaly", "", "stats by host", "", "", "Enabled"],
        ["Old defence tamper", "T1562.001", "service stop", "", "Sysmon", "Enabled"],
    ], sheet_name="Rules")
    files = {"use_cases": ("rules.xlsx", dump, _XLSX_MIME)}
    if env:
        workbook = _xlsx(
            [["Platform"], ["Windows"]],
            sheet_name="Assets",
            extra_sheets=[("Log Sources", [["Source"], ["Sysmon"]])],
        )
        files["environment"] = ("environment.xlsx", workbook, _XLSX_MIME)
    return files


async def _create(client, headers, intake='{"industry": "Banking", "region": "EU", "exclusions": [{"target": "T1200", "reason": "accepted risk, physical controls"}]}'):
    response = await client.post(
        "/api/v1/mitre/assessments",
        headers=headers,
        files=_dump_files(),
        data={"intake": intake, "name": "Q3 SOC coverage"},
    )
    assert response.status_code == 201, response.text
    return response.json()


async def _run_and_wait(client, headers, assessment_id):
    run = await client.post(f"/api/v1/mitre/assessments/{assessment_id}/run", headers=headers)
    assert run.status_code == 202, run.text
    for _ in range(150):
        poll = await client.get(f"/api/v1/mitre/assessments/{assessment_id}", headers=headers)
        assert poll.status_code == 200
        body = poll.json()
        if body["status"] in ("completed", "failed"):
            return body
        await asyncio.sleep(0.1)
    raise AssertionError("assessment did not finish in time")


def _tech(body, technique_id):
    return next(r for r in body["technique_results"] if r["technique_id"] == technique_id)


@pytest.mark.asyncio
async def test_create_run_results_end_to_end(client, db_session):
    _, _, headers = await _make_user(db_session)
    preview = await _create(client, headers)

    assert preview["row_count"] == 4
    assert preview["tagged"] == 3 and preview["untagged"] == 1 and preview["invalid"] == 0
    assert preview["attack_version"] == "19.1"
    assert preview["environment"]["platforms"] == ["Windows"]
    # revoked customer tag surfaced at parse time
    assert any("T1562.001" in a and "T1685" in a for a in preview["assumptions"])

    body = await _run_and_wait(client, headers, preview["assessment_id"])
    assert body["status"] == "completed", body.get("error_message")

    # Hand-computed states against the pinned v19.1 dataset:
    assert _tech(body, "T1059.001")["state"] == "covered"       # enabled, conf 1.0
    assert _tech(body, "T1021.001")["state"] == "partial"       # disabled rule
    assert _tech(body, "T1685")["state"] == "covered"           # T1562.001 remapped
    assert _tech(body, "T1059")["state"] == "partial"           # covered-sub rollup
    assert _tech(body, "T1021")["state"] == "not_covered"       # partial sub doesn't roll up
    t1200 = _tech(body, "T1200")
    assert t1200["state"] == "not_applicable"
    assert t1200["na_reason"] == "accepted risk, physical controls"
    # macOS-only technique filtered by the Windows-only inventory
    assert _tech(body, "T1059.002")["na_reason"] is not None
    assert "macOS" in _tech(body, "T1059.002")["na_reason"]

    summary = body["summary"]
    assert summary["applicable_domains"] == ["enterprise"]      # ICS+mobile gated
    overall = summary["overall"]
    assert overall["covered"] == 2 and overall["partial"] == 2
    assert overall["strict_pct"] == round(100 * 2 / overall["applicable"], 1)
    assert summary["counts"] == {
        "use_cases": 4, "customer_tagged": 3, "keyword_tagged": 0,
        "ai_tagged": 0, "unmapped": 1, "invalid": 0,
    }
    # Phase 14b pluralization: exactly one unmapped rule here -> singular.
    assert any("1 rule remains unmapped to ATT&CK" in a for a in summary["assumptions"])

    # Phase 2 additions: ranked gaps, roadmap buckets, narrative (template
    # here — the LLM is stubbed out).
    assert summary["gaps"], "expected a non-empty ranked gap list"
    assert summary["gaps"][0]["rank"] == 1
    assert set(summary["roadmap"]) == {"short", "mid", "long"}
    assert summary["narrative"]["generated_by"] == "template"
    assert summary["narrative"]["executive_summary"]

    # listing shows the headline %
    listing = await client.get("/api/v1/mitre/assessments", headers=headers)
    assert listing.status_code == 200
    assert listing.json()[0]["strict_pct"] == overall["strict_pct"]

    # use-case rows with mapping filter
    use_cases = await client.get(
        f"/api/v1/mitre/assessments/{preview['assessment_id']}/use-cases",
        headers=headers,
        params={"mapping_status": "unmapped"},
    )
    assert use_cases.status_code == 200
    assert use_cases.json()["total"] == 1
    assert use_cases.json()["items"][0]["name"] == "Untagged anomaly"

    # 409 on re-running a completed assessment
    rerun = await client.post(
        f"/api/v1/mitre/assessments/{preview['assessment_id']}/run", headers=headers
    )
    assert rerun.status_code == 409


@pytest.mark.asyncio
async def test_telemetry_shelfware_assumption_surfaces_end_to_end(client, db_session):
    """Plan phase A3: a rule's declared log source ("Okta" -> identity
    category) that doesn't match anything in the uploaded Log Sources sheet
    (only "Sysmon" -> endpoint/registry/network) should surface the
    shelfware assumption once the assessment completes."""
    _, _, headers = await _make_user(db_session, email="shelfware@example.com")
    dump = _xlsx([
        ["Use Case Name", "MITRE Technique(s)", "Detection Logic", "Description", "Log Source", "Status"],
        ["Okta Impossible Travel", "T1078", "geo-velocity anomaly", "", "Okta", "Enabled"],
    ], sheet_name="Rules")
    workbook = _xlsx(
        [["Platform"], ["Windows"]],
        sheet_name="Assets",
        extra_sheets=[("Log Sources", [["Source"], ["Sysmon"]])],
    )
    response = await client.post(
        "/api/v1/mitre/assessments",
        headers=headers,
        files={
            "use_cases": ("rules.xlsx", dump, _XLSX_MIME),
            "environment": ("environment.xlsx", workbook, _XLSX_MIME),
        },
        data={"name": "Shelfware check"},
    )
    assert response.status_code == 201, response.text
    preview = response.json()

    body = await _run_and_wait(client, headers, preview["assessment_id"])
    assert body["status"] == "completed", body.get("error_message")
    assert _tech(body, "T1078")["state"] == "covered"

    assumptions = body["summary"]["assumptions"]
    assert any(
        "T1078" in a and "Okta" in a and "verify that telemetry is actually flowing" in a
        for a in assumptions
    ), assumptions


@pytest.mark.asyncio
async def test_org_isolation(client, db_session):
    _, _, headers_a = await _make_user(db_session, email="a@example.com")
    _, _, headers_b = await _make_user(db_session, email="b@example.com")
    preview = await _create(client, headers_a)
    aid = preview["assessment_id"]

    assert (await client.get(f"/api/v1/mitre/assessments/{aid}", headers=headers_b)).status_code == 404
    assert (await client.post(f"/api/v1/mitre/assessments/{aid}/run", headers=headers_b)).status_code == 404
    assert (await client.delete(f"/api/v1/mitre/assessments/{aid}", headers=headers_b)).status_code == 404
    listing = await client.get("/api/v1/mitre/assessments", headers=headers_b)
    assert listing.json() == []

    # owner can soft-delete; it disappears from GET
    assert (await client.delete(f"/api/v1/mitre/assessments/{aid}", headers=headers_a)).status_code == 204
    assert (await client.get(f"/api/v1/mitre/assessments/{aid}", headers=headers_a)).status_code == 404


@pytest.mark.asyncio
async def test_viewer_cannot_create_and_pdf_rejected(client, db_session):
    _, _, viewer = await _make_user(db_session, role="viewer")
    response = await client.post(
        "/api/v1/mitre/assessments", headers=viewer, files=_dump_files(env=False)
    )
    assert response.status_code == 403

    _, _, admin = await _make_user(db_session, email="c@example.com")
    response = await client.post(
        "/api/v1/mitre/assessments",
        headers=admin,
        files={"use_cases": ("rules.pdf", b"%PDF-1.4", "application/pdf")},
    )
    assert response.status_code == 422
    assert "XLSX template" in response.json()["detail"]


@pytest.mark.asyncio
async def test_settings_roundtrip_and_validation(client, db_session):
    _, _, admin = await _make_user(db_session)
    defaults = await client.get("/api/v1/mitre/settings", headers=admin)
    assert defaults.status_code == 200
    assert defaults.json() == {
        "confidence_covered": 0.7,
        "confidence_partial_floor": 0.4,
        "partial_credit": 0.5,
        "count_disabled_as_coverage": False,
        "threat_weighting_enabled": True,  # Phase 11
        "quality_ai_enabled": False,  # Phase 12
        "report_display_name": "ScopeWise",  # Phase 14h
        "report_accent_color": "#0057B8",  # Phase 14h
        "report_watermark_text": "",  # Phase 14h
    }

    patched = await client.patch(
        "/api/v1/mitre/settings", headers=admin,
        json={"partial_credit": 0.6, "count_disabled_as_coverage": True},
    )
    assert patched.status_code == 200
    assert patched.json()["partial_credit"] == 0.6
    assert patched.json()["count_disabled_as_coverage"] is True

    bad = await client.patch(
        "/api/v1/mitre/settings", headers=admin, json={"confidence_partial_floor": 0.9}
    )
    assert bad.status_code == 422

    _, _, reviewer = await _make_user(db_session, role="reviewer", email="r@example.com")
    assert (
        await client.patch("/api/v1/mitre/settings", headers=reviewer, json={"partial_credit": 0.5})
    ).status_code == 403


@pytest.mark.asyncio
async def test_stale_running_assessment_flips_to_failed(client, db_session):
    org, user, headers = await _make_user(db_session)
    stale = MitreAssessment(
        assessment_id=uuid.uuid4(),
        org_id=org.org_id,
        name="stale run",
        status="running",
        attack_version="19.1",
        created_by=user.user_id,
        updated_at=datetime.now(timezone.utc) - timedelta(minutes=31),
    )
    db_session.add(stale)
    await db_session.commit()

    response = await client.get(
        f"/api/v1/mitre/assessments/{stale.assessment_id}", headers=headers
    )
    assert response.status_code == 200
    assert response.json()["status"] == "failed"
    assert response.json()["error_message"] == STALE_RUN_MESSAGE


@pytest.mark.asyncio
async def test_invalid_intake_rejected(client, db_session):
    _, _, headers = await _make_user(db_session)
    response = await client.post(
        "/api/v1/mitre/assessments",
        headers=headers,
        files=_dump_files(env=False),
        data={"intake": '{"exclusions": [{"target": "T1200"}]}'},  # missing reason
    )
    assert response.status_code == 422
    assert "reason" in response.json()["detail"]


def test_build_mappings_valid_revoked_invalid_in_one_row():
    """Task D regression: the explicit-MITRE-ID path stays pure code —
    valid tag kept, revoked tag remapped, invalid tag noted, all in one row."""
    remapped_id, status = DEFAULT.resolve("T1562.001")
    assert status == "remapped"  # pinned v19.1 revokes T1562.001

    mappings, mapping_status, notes = build_mappings(
        ["T1059.001", "T1562.001", "T4242", "T1059.001"]
    )
    assert mapping_status == "customer_tagged"
    by_id = {m["technique_id"]: m for m in mappings}
    assert set(by_id) == {"T1059.001", remapped_id}  # deduped, remapped
    assert all(m["source"] == "customer" and m["confidence"] == 1.0 for m in mappings)
    assert any("T4242" in n and "not a valid" in n for n in notes)
    assert any("T1562.001" in n and "revoked" in n for n in notes)

    # tags present but none usable -> invalid; no tags at all -> unmapped
    assert build_mappings(["T4242"])[1] == "invalid"
    assert build_mappings([])[1] == "unmapped"


def _keyword_dump() -> bytes:
    """Untagged mix: one row the keyword pre-pass maps (mimikatz), one it
    must leave for the AI, one customer-tagged row."""
    return _xlsx([
        ["Use Case Name", "MITRE Technique(s)", "Detection Logic", "Status"],
        ["Mimikatz credential theft", "", "process_name = mimikatz.exe", "Enabled"],
        ["Volume anomaly", "", "stats by host", "Enabled"],
        ["RDP brute force", "T1110", "logon failures > 20", "Enabled"],
    ], sheet_name="Rules")


@pytest.mark.asyncio
async def test_keyword_prepass_tags_rows_and_ai_gets_only_residue(
    client, db_session, monkeypatch
):
    captured = []

    async def capture_tag(rows, **kwargs):
        captured.append([r["row_ref"] for r in rows])
        return {
            "mappings_by_ref": {}, "assumptions": [], "models_used": [],
            "batches_total": 1, "batches_failed": 0,
        }

    monkeypatch.setattr(agents, "tag_untagged_rows", capture_tag)

    _, _, headers = await _make_user(db_session)
    created = await client.post(
        "/api/v1/mitre/assessments",
        headers=headers,
        files={"use_cases": ("rules.xlsx", _keyword_dump(), _XLSX_MIME)},
    )
    assert created.status_code == 201, created.text
    aid = created.json()["assessment_id"]

    body = await _run_and_wait(client, headers, aid)
    assert body["status"] == "completed", body.get("error_message")

    # AI saw ONLY the residue row — the keyword-matched one skipped the LLM.
    assert captured == [[ "Rules:3" ]]

    use_cases = await client.get(
        f"/api/v1/mitre/assessments/{aid}/use-cases",
        headers=headers,
        params={"mapping_status": "keyword_tagged"},
    )
    items = use_cases.json()["items"]
    assert [uc["name"] for uc in items] == ["Mimikatz credential theft"]
    (mapping,) = items[0]["mappings"]
    assert mapping["technique_id"] == "T1003.001"
    assert mapping["source"] == "keyword"
    assert mapping["confidence"] == 0.9
    assert "mimikatz" in mapping["rationale"]

    summary = body["summary"]
    assert summary["counts"]["keyword_tagged"] == 1
    assert summary["counts"]["customer_tagged"] == 1
    assert summary["counts"]["unmapped"] == 1
    assert any("matched deterministically" in a for a in summary["assumptions"])
    # keyword mapping counts as coverage (0.9 >= the 0.7 default threshold)
    assert _tech(body, "T1003.001")["state"] == "covered"


@pytest.mark.asyncio
async def test_logic_persisted_and_fed_to_both_taggers(client, db_session, monkeypatch):
    """Phase 7 regression: a dump with BOTH description and logic keeps both
    (logic used to be dropped), the keyword pre-pass fires on a tool string
    that lives ONLY in the logic column, and the AI tagger receives the
    real logic text for the residue."""
    captured = []

    async def capture_tag(rows, **kwargs):
        captured.extend(rows)
        return {
            "mappings_by_ref": {}, "assumptions": [], "models_used": [],
            "batches_total": 1, "batches_failed": 0,
        }

    monkeypatch.setattr(agents, "tag_untagged_rows", capture_tag)

    _, _, headers = await _make_user(db_session)
    dump = _xlsx([
        ["Use Case Name", "MITRE Technique(s)", "Detection Logic", "Description", "Status"],
        # tool string ONLY in logic; description present (the dropped case)
        ["Suspicious task watcher", "", "schtasks /create /tn maint", "Detects suspicious scheduled activity", "Enabled"],
        ["Threshold breach", "", "stats count by host", "Volume anomaly per host", "Enabled"],
    ], sheet_name="Rules")
    created = await client.post(
        "/api/v1/mitre/assessments",
        headers=headers,
        files={"use_cases": ("rules.xlsx", dump, _XLSX_MIME)},
    )
    assert created.status_code == 201, created.text
    aid = created.json()["assessment_id"]

    # both fields stored distinctly (regression for the dropped-logic bug)
    rows = (
        await db_session.execute(
            select(MitreUseCase)
            .where(MitreUseCase.assessment_id == uuid.UUID(aid))
            .order_by(MitreUseCase.row_ref)
        )
    ).scalars().all()
    assert [(r.description, r.logic) for r in rows] == [
        ("Detects suspicious scheduled activity", "schtasks /create /tn maint"),
        ("Volume anomaly per host", "stats count by host"),
    ]

    body = await _run_and_wait(client, headers, aid)
    assert body["status"] == "completed", body.get("error_message")

    # keyword pre-pass matched via the logic column (would miss pre-032)
    assert body["summary"]["counts"]["keyword_tagged"] == 1
    assert _tech(body, "T1053.005")["state"] == "covered"

    # AI residue carried the real logic text
    assert [(r["row_ref"], r["logic"]) for r in captured] == [
        ("Rules:3", "stats count by host")
    ]


@pytest.mark.asyncio
async def test_keyword_matches_keep_assessment_alive_when_ai_is_down(
    client, db_session, monkeypatch
):
    async def all_fail(rows, **kwargs):
        return {
            "mappings_by_ref": {}, "assumptions": ["AI tagging unavailable (stub)"],
            "models_used": [], "batches_total": 1, "batches_failed": 1,
        }

    monkeypatch.setattr(agents, "tag_untagged_rows", all_fail)

    _, _, headers = await _make_user(db_session)
    dump = _xlsx([
        ["Use Case Name", "MITRE Technique(s)", "Status"],
        ["PsExec lateral movement", "", "Enabled"],   # keyword -> T1021.002
        ["Volume anomaly", "", "Enabled"],            # residue; AI down
    ], sheet_name="Rules")
    created = await client.post(
        "/api/v1/mitre/assessments",
        headers=headers,
        files={"use_cases": ("rules.xlsx", dump, _XLSX_MIME)},
    )
    assert created.status_code == 201, created.text

    body = await _run_and_wait(client, headers, created.json()["assessment_id"])
    # Zero customer tags + total AI failure used to fail the run; a keyword
    # match now keeps it alive with a non-empty result.
    assert body["status"] == "completed", body.get("error_message")
    assert body["summary"]["counts"]["keyword_tagged"] == 1
    assert _tech(body, "T1021.002")["state"] == "covered"
