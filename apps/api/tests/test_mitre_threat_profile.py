"""Phase 11 threat-informed weighting tests. Mostly pure (synthetic index +
injected profiles); the data-file test validates the real curated JSON, and
the intake tests call the router's parser directly (no DB)."""

import json

import pytest
from fastapi import HTTPException

from app.mitre import attack_data
from app.mitre.ranking import build_threat_profile, rank_gaps
from app.mitre.router import _parse_intake

from tests.test_mitre_ranking import _PRIORITIES, _index, _result


# --- curated data file ---


def test_threat_profile_ids_all_resolve_ok():
    """Every curated technique ID must resolve 'ok' (not remapped/deprecated/
    unknown) against the pinned attack.json — catches ATT&CK-version drift."""
    profiles = attack_data.load_threat_profiles()
    entries = list(profiles["industries"].values()) + list(profiles["actors"].values())
    assert entries, "profiles file is empty"
    bad = [
        (tid, status)
        for entry in entries
        for tid in entry["techniques"]
        for _, status in [attack_data.DEFAULT.resolve(tid)]
        if status != "ok"
    ]
    assert not bad, f"non-canonical IDs in threat_profiles.json: {bad}"
    # aliases must point at real profiles
    for alias, target in profiles["industry_aliases"].items():
        assert target in profiles["industries"], (alias, target)


def test_build_threat_profile_real_file_lookup():
    # alias folds Banking onto the financial-services profile
    profile = build_threat_profile("Banking", ["FIN7"])
    assert "Financial Services" in profile["labels"]
    assert "FIN7" in profile["labels"]
    assert any("FIN7" in labels for labels in profile["techniques"].values())
    # unknown industry/actor -> clean no-op
    empty = build_threat_profile("Underwater Basketry", ["No Such Crew"])
    assert empty == {"techniques": {}, "labels": []}


# --- golden ordering (synthetic, injected profile) ---

# Lift the lexicographically LATER id (T1112) so the reorder is observable:
# unprofiled, equal-tier/feasibility gaps fall back to id order (T1046 first).
_PROFILE = {"techniques": {"T1112": ["Acme Sector"]}, "labels": ["Acme Sector"]}


def _gap_order(**kwargs):
    ranked = rank_gaps(
        [_result("T1112", "not_covered"), _result("T1046", "not_covered")],
        [], [],
        index=_index(),
        priorities={"techniques": [
            {"technique_id": "T1112", "tier": 2},
            {"technique_id": "T1046", "tier": 2},
        ]},
        **kwargs,
    )
    return [g["technique_id"] for g in ranked["gaps"]], ranked


def test_profile_lifts_within_tier():
    base_order, _ = _gap_order()
    assert base_order == ["T1046", "T1112"]  # both long-feasibility, id order

    with_profile, ranked = _gap_order(profile=_PROFILE)
    assert with_profile == ["T1112", "T1046"]
    by_id = {g["technique_id"]: g for g in ranked["gaps"]}
    assert by_id["T1112"]["threat_relevance"] == ["Acme Sector"]
    assert by_id["T1046"]["threat_relevance"] is None


def test_profile_never_jumps_a_tier():
    # T1059.001 is tier 1 unprofiled; profiled tier-2 T1112 must stay below.
    ranked = rank_gaps(
        [_result("T1059.001", "not_covered"), _result("T1112", "not_covered")],
        [], [],
        index=_index(), priorities=_PRIORITIES, profile=_PROFILE,
    )
    assert [g["technique_id"] for g in ranked["gaps"]] == ["T1059.001", "T1112"]


def test_weighting_toggle_off_keeps_base_order_but_annotates():
    order, ranked = _gap_order(profile=_PROFILE, threat_weighting=False)
    assert order == ["T1046", "T1112"]  # ordering untouched
    by_id = {g["technique_id"]: g for g in ranked["gaps"]}
    assert by_id["T1112"]["threat_relevance"] == ["Acme Sector"]  # provenance kept


# --- intake validation (router parser, no DB) ---


def test_intake_threat_actors_validation():
    ok = _parse_intake(json.dumps({"threat_actors": ["FIN7", "Volt Typhoon"]}))
    assert ok["threat_actors"] == ["FIN7", "Volt Typhoon"]
    deduped = _parse_intake(json.dumps({"threat_actors": ["FIN7", "FIN7"]}))
    assert deduped["threat_actors"] == ["FIN7"]
    assert _parse_intake(None).get("threat_actors") is None  # intake omitted entirely

    for payload, needle in [
        ({"threat_actors": ["Unknown Crew"]}, "Unknown threat actors"),
        ({"threat_actors": "FIN7"}, "must be a list"),
        ({"threat_actors": ["FIN7"] * 11}, "at most 10"),
    ]:
        with pytest.raises(HTTPException) as exc:
            _parse_intake(json.dumps(payload))
        assert exc.value.status_code == 422
        assert needle in exc.value.detail
