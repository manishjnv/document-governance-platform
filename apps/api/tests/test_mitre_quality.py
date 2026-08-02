"""Phase 12 detection-strength tests: pure heuristic goldens (synthetic
index), rollup, and the OPTIONAL AI pass (faked LLM, degrade discipline)."""

import json

import pytest

from app.mitre import agents
from app.mitre.quality import (
    apply_ai_ratings,
    compute_quality,
    quality_rollup,
    strength_bucket,
    telemetry_shelfware_check,
)

from tests.test_mitre_agents import _agent
from tests.test_mitre_ranking import _index, _result


def _uc(row_ref, tid, *, source="customer", confidence=1.0, enabled=True,
        logic=None, log_source=None, name=None, severity=None, last_triggered=None):
    return {
        "row_ref": row_ref,
        "name": name or f"rule-{row_ref}",
        "enabled": enabled,
        "logic": logic,
        "log_source": log_source,
        "severity": severity,
        "last_triggered": last_triggered,
        "mappings": [
            {"technique_id": tid, "source": source, "confidence": confidence}
        ],
    }


def _score(use_cases, tid="T1059.001", state="covered"):
    results = [_result(tid, state)]
    inconclusive = compute_quality(results, use_cases, index=_index())
    return results[0], inconclusive


# --- heuristic goldens ---


def test_full_signal_customer_rule_scores_100():
    # customer(30) + enabled(30) + logic(10) + telemetry match(30):
    # T1059.001 expects endpoint telemetry; Sysmon log source provides it.
    entry, inconclusive = _score(
        [_uc("r1", "T1059.001", logic="proc where cmdline like '-enc'",
             log_source="Sysmon")]
    )
    assert entry["strength"] == 100
    assert strength_bucket(entry["strength"]) == "strong"
    assert "customer-tagged" in entry["strength_rationale"]
    assert "matches the telemetry" in entry["strength_rationale"]
    assert inconclusive == []  # matched -> nothing for the AI pass


def test_disabled_rule_can_never_be_strong():
    entry, _ = _score(
        [_uc("r1", "T1059.001", enabled=False,
             logic="proc where cmdline like '-enc'", log_source="Sysmon")]
    )
    assert entry["strength"] == 70  # no enabled bonus
    assert strength_bucket(entry["strength"]) == "moderate"
    assert "DISABLED" in entry["strength_rationale"]


def test_telemetry_match_raises_score():
    without = _score([_uc("r1", "T1059.001")])[0]  # no logic, no log source
    with_match = _score([_uc("r1", "T1059.001", log_source="Sysmon")])[0]
    assert without["strength"] == 60   # 30 + 30, telemetry unconfirmed
    assert with_match["strength"] == 90
    assert "could not confirm" in without["strength_rationale"]


# --- Phase A6: optional severity/last-triggered health columns ---

def test_severity_delta_applied_when_present():
    baseline = _score([_uc("r1", "T1059.001")])[0]["strength"]  # 60
    critical, _ = _score([_uc("r1", "T1059.001", severity="Critical")])
    low, _ = _score([_uc("r1", "T1059.001", severity="low")])
    unknown, _ = _score([_uc("r1", "T1059.001", severity="banana")])
    assert critical["strength"] == baseline + 10
    assert "severity 'critical'" in critical["strength_rationale"]
    assert low["strength"] == baseline - 5
    assert unknown["strength"] == baseline  # unrecognized text -> no-op


def test_severity_absent_is_a_noop():
    with_none = _score([_uc("r1", "T1059.001", severity=None)])[0]
    without_field = _score([{k: v for k, v in _uc("r1", "T1059.001").items() if k != "severity"}])[0]
    assert with_none["strength"] == without_field["strength"] == 60


def test_never_triggered_caps_strength_below_strong():
    entry, _ = _score(
        [_uc("r1", "T1059.001", logic="proc where cmdline like '-enc'",
             log_source="Sysmon", last_triggered="never")]
    )
    assert entry["strength"] == 70  # would be 100 uncapped
    assert strength_bucket(entry["strength"]) == "moderate"
    assert "has never triggered" in entry["strength_rationale"]


def test_stale_last_triggered_applies_penalty():
    from datetime import date, timedelta

    stale_date = (date.today() - timedelta(days=200)).isoformat()
    fresh_date = (date.today() - timedelta(days=10)).isoformat()
    stale, _ = _score(
        [_uc("r1", "T1059.001", logic="x", log_source="Sysmon", last_triggered=stale_date)]
    )
    fresh, _ = _score(
        [_uc("r1", "T1059.001", logic="x", log_source="Sysmon", last_triggered=fresh_date)]
    )
    assert stale["strength"] == 90       # 100 - 10 stale penalty
    assert "over 180 days ago" in stale["strength_rationale"]
    assert fresh["strength"] == 100      # within the freshness window -> no penalty


def test_last_triggered_absent_or_unparseable_is_a_noop():
    absent = _score([_uc("r1", "T1059.001", logic="x", log_source="Sysmon")])[0]
    unparseable, _ = _score(
        [_uc("r1", "T1059.001", logic="x", log_source="Sysmon", last_triggered="sometime last quarter")]
    )
    assert absent["strength"] == unparseable["strength"] == 100


def test_low_confidence_ai_mapping_scores_weak():
    entry, _ = _score(
        [_uc("r1", "T1059.001", source="ai", confidence=0.5)]
    )
    assert entry["strength"] == 40  # ai-mid(10) + enabled(30)
    assert strength_bucket(entry["strength"]) == "weak"
    assert "low confidence" in entry["strength_rationale"]


def test_redundancy_bonus_and_cap():
    rules = [
        _uc(f"r{i}", "T1059.001", log_source="Sysmon",
            logic="proc where true") for i in range(4)
    ]
    entry, _ = _score(rules)
    assert entry["strength"] == 100  # capped, base already 100
    assert "+3 more mapped rules" in entry["strength_rationale"]

    # cap visible when base is lower: 3 disabled rules = 70 + min(10, 2*5)
    entry, _ = _score(
        [_uc(f"r{i}", "T1059.001", enabled=False, log_source="Sysmon",
             logic="x") for i in range(3)]
    )
    assert entry["strength"] == 80


def test_no_standard_telemetry_noted_not_penalized_to_ai():
    # T1200 lists no data sources -> match unknowable; capped at 70; NOT
    # inconclusive (there is no expected telemetry to confirm).
    entry, inconclusive = _score(
        [_uc("r1", "T1200", logic="something bespoke")], tid="T1200"
    )
    assert entry["strength"] == 70
    assert "no standard telemetry" in entry["strength_rationale"]
    assert inconclusive == []


def test_only_covered_partial_with_direct_rules_are_scored():
    results = [
        _result("T1059.001", "covered"),
        _result("T1112", "partial"),      # partial via sub rollup — no direct rule
        _result("T1046", "not_covered"),
        _result("T1530", "not_applicable"),
    ]
    compute_quality(results, [_uc("r1", "T1059.001", log_source="Sysmon")],
                    index=_index())
    by_id = {r["technique_id"]: r for r in results}
    assert by_id["T1059.001"]["strength"] == 90
    for tid in ("T1112", "T1046", "T1530"):
        assert "strength" not in by_id[tid]


def test_inconclusive_selection_and_rollup():
    # logic present, expected telemetry known, no match -> inconclusive
    results = [_result("T1059.001", "covered"), _result("T1046", "covered")]
    use_cases = [
        _uc("r1", "T1059.001", logic="index=custom_thing weird=1"),
        _uc("r2", "T1046", log_source="Zeek", logic="conn scan"),
    ]
    inconclusive = compute_quality(results, use_cases, index=_index())
    assert [i["technique_id"] for i in inconclusive] == ["T1059.001"]
    assert inconclusive[0]["row_ref"] == "r1"

    rollup = quality_rollup(results)
    assert rollup["scored"] == 2
    assert rollup["strong"] == 1 and rollup["moderate"] == 1 and rollup["weak"] == 0
    assert rollup["avg_strength"] == (70 + 100) / 2

    assert quality_rollup([_result("T1046", "not_covered")]) == {
        "scored": 0, "avg_strength": None, "strong": 0, "moderate": 0, "weak": 0,
    }


# --- optional AI pass (faked LLM) ---


@pytest.mark.asyncio
async def test_ai_ratings_validated_clamped_and_merged():
    responses = [json.dumps({
        "ratings": [
            {"technique_id": "T1059.001", "strength": 150, "rationale": "broad -enc catch"},
            {"technique_id": "T9999", "strength": 90, "rationale": "not asked"},
        ],
        "overall_confidence": 0.8,
    })]
    rated = await agents.rate_detection_quality(
        [{"technique_id": "T1059.001", "row_ref": "r1", "name": "n", "logic": "l"}],
        agent=_agent(responses, cls=agents.MitreQualityAgent),
    )
    assert rated["ratings"] == {
        "T1059.001": {"strength": 100, "rationale": "broad -enc catch"}  # clamped
    }
    assert rated["models_used"] == ["fake-primary"]

    results = [_result("T1059.001", "covered")]
    compute_quality(results, [_uc("r1", "T1059.001", logic="x")], index=_index())
    applied = apply_ai_ratings(results, rated["ratings"])
    assert applied == 1
    assert results[0]["strength"] == 100
    assert results[0]["strength_rationale"].startswith("AI-assessed: ")


@pytest.mark.asyncio
async def test_ai_failure_degrades_to_heuristic():
    rated = await agents.rate_detection_quality(
        [{"technique_id": "T1059.001", "row_ref": "r1", "name": "n", "logic": "l"}],
        agent=_agent(["complete garbage not json {{{"] * 8,
                     cls=agents.MitreQualityAgent),
    )
    assert rated["ratings"] == {}  # nothing merged -> heuristic stands

    results = [_result("T1059.001", "covered")]
    compute_quality(results, [_uc("r1", "T1059.001", logic="x")], index=_index())
    before = results[0]["strength"]
    assert apply_ai_ratings(results, rated["ratings"]) == 0
    assert results[0]["strength"] == before


# --- Phase A3: rule-vs-inventory telemetry cross-check (shelfware detector) ---
# T1059.001 in the shared synthetic _index() expects endpoint telemetry
# (data_sources=["Process Creation", "Command Execution"]).


def test_shelfware_flagged_when_declared_source_absent_from_inventory():
    results = [_result("T1059.001", "covered")]
    use_cases = [_uc("r1", "T1059.001", log_source="Sysmon")]
    flagged = telemetry_shelfware_check(
        results, use_cases, log_sources=["Okta"], tooling=[], index=_index()
    )
    assert len(flagged) == 1
    assert flagged[0]["technique_id"] == "T1059.001"
    assert flagged[0]["rules"][0]["name"] == "rule-r1"
    assert flagged[0]["missing_categories"] == ["endpoint", "network", "registry"]


def test_not_flagged_when_log_source_sheet_confirms_category():
    results = [_result("T1059.001", "covered")]
    use_cases = [_uc("r1", "T1059.001", log_source="Sysmon")]
    flagged = telemetry_shelfware_check(
        results, use_cases, log_sources=["Sysmon"], tooling=[], index=_index()
    )
    assert flagged == []


def test_tooling_sheet_also_counts_as_provided():
    results = [_result("T1059.001", "covered")]
    use_cases = [_uc("r1", "T1059.001", log_source="Sysmon")]
    flagged = telemetry_shelfware_check(
        results, use_cases, log_sources=[], tooling=["CrowdStrike Falcon"], index=_index()
    )
    assert flagged == []


def test_no_workbook_at_all_still_flags_pure_function_level():
    # The pure function itself doesn't know "no workbook" -- that's the
    # caller's job (service.py only calls this when a Log Sources sheet was
    # actually uploaded). With empty lists, nothing is "provided" so a
    # category-recognizable rule is flagged.
    results = [_result("T1059.001", "covered")]
    use_cases = [_uc("r1", "T1059.001", log_source="Sysmon")]
    flagged = telemetry_shelfware_check(
        results, use_cases, log_sources=[], tooling=[], index=_index()
    )
    assert len(flagged) == 1


def test_one_matching_rule_clears_the_flag():
    results = [_result("T1059.001", "covered")]
    use_cases = [
        _uc("r1", "T1059.001", log_source="Sysmon"),
        _uc("r2", "T1059.001", log_source="CrowdStrike Falcon"),
    ]
    flagged = telemetry_shelfware_check(
        results, use_cases, log_sources=["CrowdStrike Falcon"], tooling=[], index=_index()
    )
    assert flagged == []


def test_rule_with_no_categorizable_source_is_ignored_not_flagged():
    results = [_result("T1059.001", "covered")]
    use_cases = [_uc("r1", "T1059.001", log_source=None, logic=None)]
    flagged = telemetry_shelfware_check(
        results, use_cases, log_sources=["Okta"], tooling=[], index=_index()
    )
    assert flagged == []


def test_only_covered_and_partial_states_are_considered():
    results = [
        _result("T1059.001", "not_covered"),
        _result("T1046", "not_applicable"),
    ]
    use_cases = [_uc("r1", "T1059.001", log_source="Sysmon")]
    flagged = telemetry_shelfware_check(
        results, use_cases, log_sources=["Okta"], tooling=[], index=_index()
    )
    assert flagged == []
