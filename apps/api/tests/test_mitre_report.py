"""Report/export/compare tests (MITRE Phase 4). Assessments are seeded
directly with stored summary/technique_results — no pipeline, no LLM."""

import io
import uuid
from datetime import datetime, timezone

import pytest
from httpx import ASGITransport, AsyncClient
from openpyxl import load_workbook

from app.auth import create_access_token
from app.mitre.report import _guard, build_html_report, build_xlsx_export
from app.mitre.service import compare_assessments
from app.models.mitre_assessment import MitreAssessment
from app.models.mitre_use_case import MitreUseCase
from app.models.organization import Organization
from app.models.user import User
from main import app

XSS = "<script>alert(1)</script>"
FORMULA = "=2+2"


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


def _gap(tid, name, rank=1, state="not_covered"):
    return {
        "technique_id": tid, "name": name, "domain": "enterprise", "state": state,
        "tier": 2, "tactics": ["TA0002"], "feasibility": "short", "via": "Sysmon",
        "category": "registry", "hint": "build the detection now", "rank": rank,
    }


def _tactic(strict_pct):
    return {
        "id": "TA0002", "shortname": "execution", "name": "Execution",
        "covered": 1, "partial": 1, "not_covered": 1, "not_applicable": 1,
        "applicable": 3, "strict_pct": strict_pct, "weighted_pct": strict_pct + 10,
    }


def _summary(strict_pct=33.3):
    gap = _gap("T1112", "Modify Registry")
    return {
        "overall": {"covered": 1, "partial": 1, "not_covered": 1, "not_applicable": 1,
                    "applicable": 3, "strict_pct": strict_pct, "weighted_pct": 50.0},
        "domains": {"enterprise": {"covered": 1, "partial": 1, "not_covered": 1,
                                   "not_applicable": 1, "applicable": 3,
                                   "strict_pct": strict_pct, "weighted_pct": 50.0,
                                   "tactics": [_tactic(strict_pct)]}},
        "assumptions": [f"seeded assumption {XSS}"],
        "gaps": [gap],
        "roadmap": {"short": [gap], "mid": [], "long": []},
        "narrative": {"executive_summary": "Coverage is low.",
                      "gap_recommendations": {"T1112": "Build a Sysmon registry detection."},
                      "roadmap_prose": {"short": "s", "mid": "m", "long": "l"},
                      "generated_by": "template", "model_used": None},
        "not_applicable": [{"technique_id": "T1200", "domain": "enterprise",
                            "reason": "accepted risk, physical controls"}],
        "counts": {"use_cases": 2, "customer_tagged": 2, "ai_tagged": 0,
                   "unmapped": 0, "invalid": 0},
        "applicable_domains": ["enterprise"],
    }


def _results(states: dict):
    return [
        {"technique_id": tid, "domain": "enterprise", "tactics": ["TA0002"],
         "state": state, "na_reason": "reason" if state == "not_applicable" else None,
         "use_case_refs": []}
        for tid, state in states.items()
    ]


async def _seed(db_session, org, user, *, status="completed", strict_pct=33.3,
                results=None, uc_names=()):
    assessment = MitreAssessment(
        assessment_id=uuid.uuid4(),
        org_id=org.org_id,
        name="Seeded assessment",
        status=status,
        attack_version="19.1",
        summary=_summary(strict_pct) if status == "completed" else None,
        technique_results=results
        if results is not None
        else _results({"T1059.001": "covered", "T1003.001": "partial",
                       "T1112": "not_covered", "T1200": "not_applicable"}),
        completed_at=datetime.now(timezone.utc) if status == "completed" else None,
        error_message="boom" if status == "failed" else None,
        created_by=user.user_id,
        params={"thresholds": {"confidence_covered": 0.7}, "models_used": {}},
    )
    db_session.add(assessment)
    for i, name in enumerate(uc_names, start=1):
        db_session.add(
            MitreUseCase(
                assessment_id=assessment.assessment_id,
                org_id=org.org_id,
                row_ref=f"s:{i}",
                name=name,
                description=f"desc {name}",
                enabled=True,
                mappings=[{"technique_id": "T1059.001", "source": "customer", "confidence": 1.0}],
                mapping_status="customer_tagged",
            )
        )
    await db_session.commit()
    return assessment


# ---------------------------------------------------------------------------
# pure-function tests
# ---------------------------------------------------------------------------


def test_formula_guard():
    assert _guard("=2+2") == "'=2+2"
    assert _guard("+SUM(A1)") == "'+SUM(A1)"
    assert _guard("-1") == "'-1"
    assert _guard("@cmd") == "'@cmd"
    assert _guard("normal") == "normal"
    assert _guard(5) == 5
    assert _guard(None) is None


@pytest.mark.asyncio
async def test_html_report_escapes_untrusted_strings(db_session):
    org, user, _ = await _make_user(db_session)
    assessment = await _seed(db_session, org, user, uc_names=[f"Rule {XSS}"])
    use_cases = [{"row_ref": "s:1", "name": f"Rule {XSS}", "description": None,
                  "log_source": None, "enabled": True, "mappings": [],
                  "mapping_status": "customer_tagged"}]
    html = build_html_report(assessment, use_cases)
    assert XSS not in html                       # raw payload never present
    assert "&lt;script&gt;" in html              # escaped twice: rule + assumption
    assert "33.3%" in html                       # numbers from stored summary
    assert "Build a Sysmon registry detection." in html
    assert "accepted risk, physical controls" in html
    # Phase 14e structure: TOC with real page numbers + per-gap why line
    assert "target-counter(attr(href), page)" in html
    assert "Why it's a gap:" in html
    assert "Top 5 things to fix first" in html


@pytest.mark.asyncio
async def test_xlsx_formula_injection_guard(db_session):
    org, user, _ = await _make_user(db_session)
    assessment = await _seed(db_session, org, user)
    use_cases = [{"row_ref": "s:1", "name": FORMULA, "description": "=HYPERLINK(evil)",
                  "logic": "=cmd|'/C calc'!A0", "log_source": None, "enabled": True,
                  "mappings": [], "mapping_status": "customer_tagged"}]
    wb = load_workbook(io.BytesIO(build_xlsx_export(assessment, use_cases)))
    assert set(wb.sheetnames) == {
        "Read Me", "Summary", "Coverage by Tactic", "Technique Register",
        "Use-Case Mappings", "Gaps & Recommendations", "Roadmap",
        "Not Applicable", "Assumptions",
    }
    assert wb.sheetnames[0] == "Read Me"                # Phase 14c guide sheet
    ws = wb["Use-Case Mappings"]
    assert ws["B2"].value == "'" + FORMULA
    assert ws["I2"].value == "'=HYPERLINK(evil)"
    assert ws["J1"].value == "Logic"                    # Phase 7 column
    assert ws["J2"].value == "'=cmd|'/C calc'!A0"       # logic cell guarded


@pytest.mark.asyncio
async def test_xlsx_phase14c_structure(db_session):
    """Phase 14c structure goldens (not pixel styling): Read Me content,
    register Name/plain-words/Why columns with tactic names, plain-words
    mapping status, numeric row sort, feasibility-grouped gaps, renamed
    Summary metric."""
    org, user, _ = await _make_user(db_session)
    assessment = await _seed(db_session, org, user)
    use_cases = [
        {"row_ref": "s:10", "name": "Rule ten", "description": None, "logic": None,
         "log_source": None, "enabled": True, "mappings": [],
         "mapping_status": "unmapped"},
        {"row_ref": "s:2", "name": "PS rule", "description": None, "logic": None,
         "log_source": None, "enabled": True,
         "mappings": [{"technique_id": "T1059.001", "source": "customer",
                       "confidence": 1.0}],
         "mapping_status": "customer_tagged"},
    ]
    wb = load_workbook(io.BytesIO(build_xlsx_export(assessment, use_cases)))

    readme = wb["Read Me"]
    texts = [str(c.value) for row in readme.iter_rows() for c in row if c.value]
    assert any("Is 33.3% bad?" in t for t in texts)
    assert any("What each sheet contains" in t for t in texts)

    reg = wb["Technique Register"]
    headers = [c.value for c in reg[1]]
    assert headers[:7] == ["Technique", "Name", "Matrix", "Tactics", "State",
                           "In plain words", "Why"]
    rows = {r[0].value: r for r in reg.iter_rows(min_row=2)}
    covered = rows["T1059.001"]
    assert covered[1].value == "PowerShell"             # name from the pinned index
    assert covered[3].value == "Execution"              # tactic name, not TA0002
    assert "Covered by your rule 'PS rule'" in covered[6].value
    not_covered = rows["T1112"]
    assert not_covered[5].value == "No rule detects this"
    assert "maps to this technique" in not_covered[6].value

    ucs = wb["Use-Case Mappings"]
    assert ucs["A2"].value == "s:2"                     # numeric sort: 2 before 10
    assert ucs["A3"].value == "s:10"
    assert ucs["D2"].value == "You tagged this"         # plain-words status
    assert ucs["D3"].value == "Could not be mapped"

    gaps = wb["Gaps & Recommendations"]
    a_col = [c[0].value for c in gaps.iter_rows(min_col=1, max_col=1) if c[0].value]
    assert any(str(v).startswith("Short term") for v in a_col)  # section header

    summary_metrics = [r[0].value for r in wb["Summary"].iter_rows(min_row=2)]
    assert "Coverage %" in summary_metrics
    assert "Strict coverage %" not in summary_metrics


def test_compare_golden():
    class A:  # minimal stand-in with the attributes compare reads
        pass

    baseline, current = A(), A()
    for a, strict, states in (
        (baseline, 40.0, {"T1059.001": "covered", "T1112": "not_covered",
                          "T1003.001": "covered", "T1200": "not_applicable",
                          "T1547.001": "covered"}),
        (current, 60.0, {"T1059.001": "covered", "T1112": "covered",
                         "T1003.001": "partial", "T1200": "covered",
                         "T1547.001": "not_applicable"}),
    ):
        a.assessment_id = uuid.uuid4()
        a.name = "x"
        a.completed_at = datetime.now(timezone.utc)
        a.attack_version = "19.1"
        a.summary = _summary(strict)
        a.technique_results = _results(states)

    diff = compare_assessments(current, baseline)
    assert [e["technique_id"] for e in diff["newly_covered"]] == ["T1112", "T1200"]
    assert [e["technique_id"] for e in diff["regressed"]] == ["T1003.001"]
    assert [e["technique_id"] for e in diff["na_changed"]] == ["T1200", "T1547.001"]
    assert diff["overall_delta"]["strict_pct"] == 20.0
    assert diff["attack_version_mismatch"] is False
    assert diff["tactic_deltas"] == [{
        "domain": "enterprise", "id": "TA0002", "name": "Execution",
        "current_strict_pct": 60.0, "baseline_strict_pct": 40.0, "delta": 20.0,
    }]
    # real technique names resolved from the pinned dataset
    assert diff["newly_covered"][0]["name"] == "Modify Registry"


def test_compare_degrades_on_malformed_jsonb():
    """technique_results/summary are unenforced JSONB — a row missing 'state'
    or a tactic missing 'id' (schema drift) must degrade, not 500
    (2026-08-02 adversarial review, non-blocking finding #1)."""
    class A:
        pass

    baseline, current = A(), A()
    for a in (baseline, current):
        a.assessment_id = uuid.uuid4()
        a.name = "x"
        a.completed_at = datetime.now(timezone.utc)
        a.attack_version = "19.1"
        a.summary = {"overall": {}, "domains": {"enterprise": {
            "tactics": [{"name": "no id here", "strict_pct": 10.0}]}}}
        a.technique_results = [
            {"technique_id": "T1059.001"},          # no 'state'
            {"technique_id": "T1112", "state": "covered"},
        ]
    # must not raise
    diff = compare_assessments(current, baseline)
    assert diff["tactic_deltas"] == []  # the id-less tactic is skipped, not crashed


# ---------------------------------------------------------------------------
# endpoint tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_report_endpoint_html_and_409(client, db_session):
    org, user, headers = await _make_user(db_session, role="viewer")  # viewers may read
    done = await _seed(db_session, org, user, uc_names=["Rule A"])
    pending = await _seed(db_session, org, user, status="pending")

    res = await client.get(
        f"/api/v1/mitre/assessments/{done.assessment_id}/report", headers=headers
    )
    assert res.status_code == 200
    assert res.json()["format"] == "html"
    assert "MITRE ATT&amp;CK Coverage Assessment" in res.json()["data"]

    res = await client.get(
        f"/api/v1/mitre/assessments/{pending.assessment_id}/report", headers=headers
    )
    assert res.status_code == 409


@pytest.mark.asyncio
async def test_pdf_endpoint(client, db_session, require_weasyprint):
    import base64

    org, user, headers = await _make_user(db_session)
    done = await _seed(db_session, org, user, uc_names=["Rule A"])
    res = await client.get(
        f"/api/v1/mitre/assessments/{done.assessment_id}/report",
        headers=headers, params={"format": "pdf"},
    )
    assert res.status_code == 200
    assert base64.b64decode(res.json()["data"]).startswith(b"%PDF")


@pytest.mark.asyncio
async def test_xlsx_endpoint_streams_with_content_type(client, db_session):
    org, user, headers = await _make_user(db_session, role="viewer")
    done = await _seed(db_session, org, user, uc_names=[FORMULA])
    res = await client.get(
        f"/api/v1/mitre/assessments/{done.assessment_id}/export.xlsx", headers=headers
    )
    assert res.status_code == 200
    assert res.headers["content-type"].startswith(
        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )
    assert "attachment" in res.headers["content-disposition"]
    ws = load_workbook(io.BytesIO(res.content))["Use-Case Mappings"]
    assert ws["B2"].value == "'" + FORMULA


@pytest.mark.asyncio
async def test_executive_scope_report(client, db_session):
    """scope=executive returns the 1-3 page leadership cut: cover + executive
    section only — no detailed section, appendices, TOC, or cross-refs."""
    org, user, headers = await _make_user(db_session, role="viewer")
    done = await _seed(db_session, org, user)
    res = await client.get(
        f"/api/v1/mitre/assessments/{done.assessment_id}/report",
        params={"format": "html", "scope": "executive"},
        headers=headers,
    )
    assert res.status_code == 200
    html = res.json()["data"]
    assert "Top 5 things to fix first" in html
    assert "Executive summary" in html
    assert "Appendix: technique register" not in html
    assert "Gap register" not in html
    assert "<h3>Contents</h3>" not in html
    assert "class='xref'" not in html
    res = await client.get(
        f"/api/v1/mitre/assessments/{done.assessment_id}/report",
        params={"scope": "bogus"},
        headers=headers,
    )
    assert res.status_code == 422


@pytest.mark.asyncio
async def test_rename_archive_and_list_filter(client, db_session):
    """Phase 14f: PATCH rename + soft-archive flag; archived rows leave the
    default list but return with include_archived=true. No delete exists."""
    org, user, headers = await _make_user(db_session, role="admin")
    a = await _seed(db_session, org, user)
    aid = str(a.assessment_id)

    res = await client.patch(
        f"/api/v1/mitre/assessments/{aid}", json={"name": "Renamed run"}, headers=headers
    )
    assert res.status_code == 200 and res.json()["name"] == "Renamed run"

    res = await client.patch(
        f"/api/v1/mitre/assessments/{aid}", json={"archived": True}, headers=headers
    )
    assert res.status_code == 200 and res.json()["archived"] is True

    res = await client.get("/api/v1/mitre/assessments", headers=headers)
    assert all(i["assessment_id"] != aid for i in res.json())

    res = await client.get(
        "/api/v1/mitre/assessments", params={"include_archived": True}, headers=headers
    )
    row = next(i for i in res.json() if i["assessment_id"] == aid)
    assert row["archived"] is True and row["name"] == "Renamed run"

    res = await client.patch(
        f"/api/v1/mitre/assessments/{aid}", json={}, headers=headers
    )
    assert res.status_code == 422


@pytest.mark.asyncio
async def test_compare_endpoint_and_authz(client, db_session):
    org, user, headers = await _make_user(db_session)
    baseline = await _seed(
        db_session, org, user,
        strict_pct=40.0,
        results=_results({"T1112": "not_covered", "T1059.001": "covered"}),
    )
    current = await _seed(
        db_session, org, user,
        strict_pct=60.0,
        results=_results({"T1112": "covered", "T1059.001": "covered"}),
    )
    pending = await _seed(db_session, org, user, status="pending")

    res = await client.get(
        f"/api/v1/mitre/assessments/{current.assessment_id}/compare/{baseline.assessment_id}",
        headers=headers,
    )
    assert res.status_code == 200
    body = res.json()
    assert [e["technique_id"] for e in body["newly_covered"]] == ["T1112"]
    assert body["regressed"] == [] and body["na_changed"] == []
    assert body["overall_delta"]["strict_pct"] == 20.0

    # baseline not completed -> 409
    res = await client.get(
        f"/api/v1/mitre/assessments/{current.assessment_id}/compare/{pending.assessment_id}",
        headers=headers,
    )
    assert res.status_code == 409

    # cross-org -> 404 on either side
    _, _, headers_b = await _make_user(db_session)
    res = await client.get(
        f"/api/v1/mitre/assessments/{current.assessment_id}/compare/{baseline.assessment_id}",
        headers=headers_b,
    )
    assert res.status_code == 404


@pytest.mark.asyncio
async def test_list_includes_domains_brief(client, db_session):
    org, user, headers = await _make_user(db_session)
    await _seed(db_session, org, user)
    res = await client.get("/api/v1/mitre/assessments", headers=headers)
    assert res.status_code == 200
    brief = res.json()[0]["domains_brief"]
    assert brief["enterprise"]["strict_pct"] == 33.3
    assert brief["enterprise"]["applicable"] == 3
