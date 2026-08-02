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


# --- Phase A8: region weighting ---


def test_region_profiles_actor_references_exist():
    """Alias-integrity check for the new region_profiles section: every
    actor name a region references must be a real curated actor."""
    profiles = attack_data.load_threat_profiles()
    actor_names = set(profiles["actors"])
    bad = [
        (region["label"], actor)
        for region in profiles.get("region_profiles", [])
        for actor in region["actors"]
        if actor not in actor_names
    ]
    assert not bad, f"region_profiles references unknown actors: {bad}"


def test_region_lookup_golden_real_file():
    profile = build_threat_profile(None, [], region="We operate across North America")
    assert "North America" in profile["labels"]
    assert "Scattered Spider" in profile["labels"]
    assert any("Scattered Spider" in labels for labels in profile["techniques"].values())


def test_region_short_codes_use_word_boundaries_not_substrings():
    # "us" must not fire inside "Australia"; "India" (APAC keyword) should
    # match on its own.
    australia = build_threat_profile(None, [], region="Australia")
    assert "North America" not in australia["labels"]
    assert "Asia-Pacific" in australia["labels"]


def test_unknown_region_is_a_clean_noop():
    empty = build_threat_profile(None, [], region="Antarctica Research Station")
    assert empty == {"techniques": {}, "labels": []}
    # blank region behaves identically to omitted
    assert build_threat_profile(None, [], region="") == {"techniques": {}, "labels": []}
    assert build_threat_profile(None, []) == {"techniques": {}, "labels": []}


def test_region_and_industry_and_actor_combine_without_duplicate_labels():
    profile = build_threat_profile("Banking", ["FIN7"], region="Europe (EU)")
    assert profile["labels"].count("FIN7") == 1  # no accidental double-add
    assert "Europe" in profile["labels"]
    assert "Financial Services" in profile["labels"]
    assert "Sandworm Team" in profile["labels"]  # from the Europe region profile


def test_region_lift_within_tier_same_pattern_as_industry():
    # Real region-derived profile (North America -> Scattered Spider et al,
    # who share T1486) feeds the SAME within-tier lift as a synthetic
    # profile -- proves region is a genuine third input, not just a label.
    from app.mitre.attack_data import AttackIndex

    na_index = AttackIndex({
        "version": "19.1",
        "domains": {"enterprise": {
            "tactics": [{"id": "TA0002", "shortname": "execution", "name": "Execution"}],
            "techniques": [
                {"id": "T1486", "name": "Data Encrypted for Impact", "tactics": ["TA0002"],
                 "platforms": ["Windows"], "data_sources": [], "is_subtechnique": False,
                 "parent_id": None, "deprecated": False, "revoked": False,
                 "superseded_by": None, "summary": ""},
                {"id": "T1046", "name": "name-T1046", "tactics": ["TA0002"],
                 "platforms": ["Windows"], "data_sources": [], "is_subtechnique": False,
                 "parent_id": None, "deprecated": False, "revoked": False,
                 "superseded_by": None, "summary": ""},
            ],
        }},
    })
    region_profile = build_threat_profile(None, [], region="North America")
    ranked = rank_gaps(
        [_result("T1486", "not_covered"), _result("T1046", "not_covered")],
        [], [], index=na_index,
        priorities={"techniques": [
            {"technique_id": "T1486", "tier": 2}, {"technique_id": "T1046", "tier": 2},
        ]},
        profile=region_profile,
    )
    order = [g["technique_id"] for g in ranked["gaps"]]
    assert order == ["T1486", "T1046"]  # region-linked technique lifted first
    by_id = {g["technique_id"]: g for g in ranked["gaps"]}
    assert by_id["T1486"]["threat_relevance"]  # tagged with an actor name
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
