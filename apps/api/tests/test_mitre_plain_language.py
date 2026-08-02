"""Phase 14a: curated plain-language files + deterministic why-phrases.

File validation follows the threat_profiles.json pattern (every curated ID
must resolve 'ok' against the pinned dataset); derive_why is golden-tested
per state; the explain endpoint is exercised against a seeded assessment.
"""

import uuid
from datetime import datetime, timezone

import pytest
from httpx import ASGITransport, AsyncClient

from app.auth import create_access_token
from app.mitre import attack_data, plain_language
from app.models.mitre_assessment import MitreAssessment
from app.models.mitre_use_case import MitreUseCase
from app.models.organization import Organization
from app.models.user import User
from main import app


# ---------------------------------------------------------------- data files


def test_curated_ids_all_resolve_ok():
    """Every curated technique ID must be canonical in the pinned dataset."""
    bad = {
        tid: status
        for tid in plain_language.load_plain_language()["techniques"]
        for _, status in [attack_data.DEFAULT.resolve(tid)]
        if status != "ok"
    }
    assert not bad, f"non-canonical IDs in technique_plain_language.json: {bad}"


def test_curated_set_covers_priorities_and_threat_profiles():
    """The curated rule: priorities file ∪ threat profiles — no ID missing."""
    expected = {
        t["technique_id"]
        for t in attack_data.load_technique_priorities()["techniques"]
    }
    profiles = attack_data.load_threat_profiles()
    for section in ("industries", "actors"):
        for entry in profiles.get(section, {}).values():
            expected.update(entry.get("techniques", []))
    curated = set(plain_language.load_plain_language()["techniques"])
    missing = expected - curated
    assert not missing, f"curated file missing top-gap techniques: {missing}"


def test_curated_entries_complete():
    for tid, entry in plain_language.load_plain_language()["techniques"].items():
        for field in ("definition", "attacker_use", "detection_hint"):
            assert entry.get(field), f"{tid} missing {field}"


def test_tactic_lines_cover_every_dataset_shortname():
    lines = plain_language.load_tactic_lines()["tactics"]
    shortnames = {
        tactic["shortname"]
        for domain in attack_data.DOMAINS
        for tactic in attack_data.DEFAULT.tactics(domain)
    }
    missing = shortnames - set(lines)
    assert not missing, f"tactic_lines.json missing shortnames: {missing}"
    assert all(lines.values()), "empty tactic line"


def test_fallback_uses_attack_summary_first_sentence():
    described = plain_language.describe_technique("T1566")  # parent, uncurated
    assert described["curated"] is False
    assert described["definition"].endswith(".")
    assert "phishing" in described["definition"].lower()
    assert described["detection_hint"] is None


def test_curated_lookup_and_sketch():
    described = plain_language.describe_technique("T1027")
    assert described["curated"] is True
    sketch = plain_language.detection_sketch("T1027", "Sysmon")
    assert sketch.startswith("Using Sysmon, alert on:")
    assert plain_language.detection_sketch("T1566", "Sysmon") is None  # uncurated


# --------------------------------------------------- telemetry fields (14h)


_TOP_35_TELEMETRY_COMPONENTS = {
    "Process Creation", "Command Execution", "Network Traffic Content",
    "File Creation", "Network Connection Creation", "Application Log Content",
    "OS API Execution", "Network Traffic Flow", "File Modification",
    "Module Load", "File Access", "Windows Registry Key Modification",
    "Process Access", "File Metadata", "Logon Session Creation",
    "Application Permission", "User Account Authentication",
    "Process Metadata", "Script Execution", "Logon Session Metadata",
    "Service Creation", "Application State", "Response Content",
    "Host Status", "Process Modification", "User Account Metadata",
    "User Account Modification", "Cloud Service Modification",
    "System Settings", "Scheduled Job Creation",
    "Active Directory Object Modification", "Device Alarm", "API Calls",
    "File Deletion", "Driver Load",
}


def test_telemetry_fields_keys_are_real_components():
    """Every telemetry_fields.json key must be a real ATT&CK data-component
    name that appears in some technique's data_sources in the pinned
    dataset (same validation pattern as the curated-ID tests above)."""
    all_components = {
        component
        for tech in attack_data.DEFAULT.techniques()
        for component in tech.get("data_sources") or []
    }
    curated = set(plain_language.load_telemetry_fields()["components"])
    bad = curated - all_components
    assert not bad, f"telemetry_fields.json has keys not in attack.json data_sources: {bad}"


def test_telemetry_fields_entries_complete():
    for component, entry in plain_language.load_telemetry_fields()["components"].items():
        for field in ("fields", "where", "gotcha"):
            assert entry.get(field), f"{component} missing {field}"
        assert isinstance(entry["fields"], list) and entry["fields"]


def test_telemetry_fields_covers_all_35_curated_components():
    """Guards against a partial file: the plan's top-35-by-frequency list
    must all be present."""
    curated = set(plain_language.load_telemetry_fields()["components"])
    missing = _TOP_35_TELEMETRY_COMPONENTS - curated
    assert not missing, f"telemetry_fields.json missing required components: {missing}"
    assert len(curated) == 35, f"expected exactly 35 curated components, got {len(curated)}"


def test_telemetry_requirements_curated_for_t1059_001():
    results = plain_language.telemetry_requirements("T1059.001")
    by_component = {r["component"]: r for r in results}
    assert set(by_component) == {
        "Command Execution", "Module Load", "Process Creation", "Process Metadata",
    }
    for name in ("Process Creation", "Command Execution"):
        entry = by_component[name]
        assert entry["fields"] and entry["where"] and entry["gotcha"]


def test_telemetry_requirements_degrades_for_uncurated_component():
    """T1219.003's only ATT&CK data source ('Drive Creation') is long-tail
    (not in the curated top 35) — degrades to the bare component name."""
    results = plain_language.telemetry_requirements("T1219.003")
    assert results == [
        {"component": "Drive Creation", "fields": [], "where": None, "gotcha": None}
    ]


def test_telemetry_lines_skip_uncurated_and_format_curated():
    assert plain_language.telemetry_lines("T1219.003") == []
    lines = plain_language.telemetry_lines("T1059.001")
    assert any(line.startswith("Process Creation — your query needs:") for line in lines)


# ------------------------------------------------------------ why goldens


def _result(state, **kw):
    return {
        "technique_id": "T1547.001",
        "domain": "enterprise",
        "tactics": ["TA0003"],
        "state": state,
        "na_reason": kw.pop("na_reason", None),
        "use_case_refs": [],
        **kw,
    }


def test_why_not_covered_counts_rules():
    why = plain_language.derive_why(_result("not_covered"), [], total_rules=30)
    assert why == "None of your 30 rules maps to this technique."
    assert (
        plain_language.derive_why(_result("not_covered"), [], total_rules=1)
        == "None of your 1 rule maps to this technique."
    )


def test_why_covered_shows_mapping_proof():
    why = plain_language.derive_why(
        _result("covered", strength=85),
        [{"name": "Run key persistence", "enabled": True, "source": "customer",
          "confidence": 1.0}],
        total_rules=30,
    )
    assert why == (
        "Covered by your rule 'Run key persistence' (tagged by you). "
        "Detection strength 85/100."
    )


def test_why_partial_disabled_rule():
    why = plain_language.derive_why(
        _result("partial"),
        [{"name": "RDP watcher", "enabled": False, "source": "customer",
          "confidence": 1.0}],
        total_rules=30,
    )
    assert why == (
        "Your rule 'RDP watcher' covers this but is disabled in your SIEM — "
        "enable it to close this gap."
    )


def test_why_partial_low_confidence():
    why = plain_language.derive_why(
        _result("partial"),
        [{"name": "Odd script alert", "enabled": True, "source": "ai",
          "confidence": 0.55}],
        total_rules=30,
    )
    assert why == (
        "Rule 'Odd script alert' probably covers this (AI-tagged at 55% "
        "confidence) — confirm the mapping to count it as covered."
    )


def test_why_partial_subtechnique_rollup():
    why = plain_language.derive_why(
        _result("partial"),
        [],
        total_rules=30,
        sub_states=[
            {"technique_id": "T1059.001", "name": "PowerShell", "state": "covered"},
            {"technique_id": "T1059.003", "name": "Windows Command Shell",
             "state": "not_covered"},
            {"technique_id": "T1059.007", "name": "JavaScript",
             "state": "not_covered"},
        ],
    )
    assert why == (
        "No rule maps to this technique directly — only 1 of its 3 "
        "sub-techniques is covered (T1059.001 PowerShell)."
    )


def test_why_not_applicable_verbatim():
    why = plain_language.derive_why(
        _result("not_applicable", na_reason="targets macOS; macOS not in asset inventory"),
        [],
    )
    assert why == "targets macOS; macOS not in asset inventory"


def test_sample_kit_states_produce_visibly_different_why_text():
    """Acceptance: kit rows 4/5 (covered) vs row 15 (disabled) read differently."""
    covered = plain_language.derive_why(
        _result("covered"),
        [{"name": "Autorun watch", "enabled": True, "source": "customer",
          "confidence": 1.0}],
    )
    disabled = plain_language.derive_why(
        _result("partial"),
        [{"name": "RDP session alert", "enabled": False, "source": "customer",
          "confidence": 1.0}],
    )
    assert "Covered by" in covered and "disabled" not in covered
    assert "disabled in your SIEM" in disabled


# ------------------------------------------------------------ explain endpoint


@pytest.fixture
async def client():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as c:
        yield c


async def _make_user(db_session, *, role="viewer"):
    org = Organization(org_id=uuid.uuid4(), name=f"org-{uuid.uuid4()}")
    user = User(user_id=uuid.uuid4(), org_id=org.org_id, email=f"{uuid.uuid4()}@x.com")
    db_session.add_all([org, user])
    await db_session.commit()
    token, _ = create_access_token(
        user_id=user.user_id, email=user.email, org_id=org.org_id, role=role
    )
    return org, user, {"Authorization": f"Bearer {token}"}


async def _seed(db_session, org, user, *, status="completed"):
    assessment = MitreAssessment(
        assessment_id=uuid.uuid4(),
        org_id=org.org_id,
        name="Explain seed",
        status=status,
        attack_version="19.1",
        summary={
            "counts": {"use_cases": 2},
            "gaps": [
                {"technique_id": "T1021.001", "state": "partial",
                 "feasibility": "short", "via": "Sysmon", "category": "endpoint",
                 "hint": "build the detection now"},
            ],
        } if status == "completed" else None,
        technique_results=[
            {"technique_id": "T1021.002", "domain": "enterprise",
             "tactics": ["TA0008"], "state": "covered", "na_reason": None,
             "use_case_refs": ["s:1"]},
            {"technique_id": "T1021.001", "domain": "enterprise",
             "tactics": ["TA0008"], "state": "partial", "na_reason": None,
             "use_case_refs": ["s:2"]},
        ],
        completed_at=datetime.now(timezone.utc) if status == "completed" else None,
        created_by=user.user_id,
        params={"thresholds": {"confidence_covered": 0.7},
                "environment_lists": {"log_sources": ["Sysmon"], "tooling": []}},
    )
    db_session.add(assessment)
    rows = [
        ("s:1", "SMB admin share alert", True, "T1021.002"),
        ("s:2", "RDP session alert", False, "T1021.001"),
    ]
    for ref, name, enabled, tid in rows:
        db_session.add(
            MitreUseCase(
                assessment_id=assessment.assessment_id,
                org_id=org.org_id,
                row_ref=ref,
                name=name,
                enabled=enabled,
                mappings=[{"technique_id": tid, "source": "customer",
                           "confidence": 1.0}],
                mapping_status="customer_tagged",
            )
        )
    await db_session.commit()
    return assessment


async def test_explain_partial_disabled(client, db_session):
    org, user, headers = await _make_user(db_session)
    assessment = await _seed(db_session, org, user)
    res = await client.get(
        f"/api/v1/mitre/assessments/{assessment.assessment_id}/techniques/T1021.001/explain",
        headers=headers,
    )
    assert res.status_code == 200
    body = res.json()
    assert body["name"] == "Remote Desktop Protocol"
    assert body["what"]["curated"] is True and body["what"]["definition"]
    assert body["where"]["via"] == "Sysmon"
    assert body["where"]["tactics"][0]["line"]  # lateral-movement story line
    assert "disabled in your SIEM" in body["why"]
    assert body["good"]["sketch"].startswith("Using Sysmon, alert on:")
    # closest starting point: the covered sibling sub-technique's rule
    assert body["good"]["closest_rule"] == {
        "technique_id": "T1021.002",
        "technique_name": "SMB/Windows Admin Shares",
        "rule_name": "SMB admin share alert",
    }
    # Phase 14h: per-data-source-component query field guidance
    telemetry_by_component = {t["component"]: t for t in body["good"]["telemetry"]}
    assert "Logon Session Creation" in telemetry_by_component
    assert telemetry_by_component["Logon Session Creation"]["fields"]
    assert telemetry_by_component["Logon Session Creation"]["gotcha"]


async def test_explain_covered_proof(client, db_session):
    org, user, headers = await _make_user(db_session)
    assessment = await _seed(db_session, org, user)
    res = await client.get(
        f"/api/v1/mitre/assessments/{assessment.assessment_id}/techniques/T1021.002/explain",
        headers=headers,
    )
    assert res.status_code == 200
    body = res.json()
    assert "Covered by your rule 'SMB admin share alert' (tagged by you)" in body["why"]
    assert body["good"]["closest_rule"] is None


async def test_explain_unknown_technique_404_and_pending_409(client, db_session):
    org, user, headers = await _make_user(db_session)
    completed = await _seed(db_session, org, user)
    res = await client.get(
        f"/api/v1/mitre/assessments/{completed.assessment_id}/techniques/T1112/explain",
        headers=headers,
    )
    assert res.status_code == 404
    pending = await _seed(db_session, org, user, status="pending")
    res = await client.get(
        f"/api/v1/mitre/assessments/{pending.assessment_id}/techniques/T1021.001/explain",
        headers=headers,
    )
    assert res.status_code == 409
