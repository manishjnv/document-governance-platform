"""Coverage computation unit tests (MITRE assessment Phase 0).

Runs against a small synthetic dataset via the injectable AttackIndex.
"""

from app.mitre.attack_data import AttackIndex
from app.mitre.coverage import compute_coverage


def _t(tid, platforms=("Windows",), tactics=("TA0002",), deprecated=False,
       revoked=False, superseded_by=None):
    return {
        "id": tid,
        "name": tid,
        "tactics": list(tactics),
        "platforms": list(platforms),
        "data_sources": [],
        "is_subtechnique": "." in tid,
        "parent_id": tid.split(".")[0] if "." in tid else None,
        "deprecated": deprecated,
        "revoked": revoked,
        "superseded_by": superseded_by,
        "summary": "",
    }


def _index():
    return AttackIndex({
        "version": "19.1",
        "domains": {
            "enterprise": {
                "tactics": [
                    {"id": "TA0002", "shortname": "execution", "name": "Execution"},
                    {"id": "TA0005", "shortname": "defense-evasion", "name": "Defense Evasion"},
                ],
                "techniques": [
                    _t("T1059"),
                    _t("T1059.001"),
                    _t("T1059.002"),
                    _t("T1112", tactics=["TA0002", "TA0005"]),
                    _t("T1999", deprecated=True),
                    _t("T1998", revoked=True, superseded_by="T1112"),
                ],
            },
        },
    })


_EMPTY_APPL = {"na": {}, "assumptions": []}


def _uc(row_ref, technique_id, enabled=True, confidence=1.0, source="customer",
        name=None):
    return {
        "row_ref": row_ref,
        "name": name or f"rule {row_ref}",
        "enabled": enabled,
        "mappings": [{"technique_id": technique_id, "source": source,
                      "confidence": confidence}],
    }


def _state(result, tid):
    return next(r for r in result["techniques"] if r["technique_id"] == tid)


def test_enabled_high_confidence_is_covered():
    result = compute_coverage([_uc("s1:1", "T1059.001")], _EMPTY_APPL, index=_index())
    entry = _state(result, "T1059.001")
    assert entry["state"] == "covered"
    assert entry["use_case_refs"] == ["s1:1"]


def test_disabled_only_is_partial_unless_policy_says_covered():
    use_cases = [_uc("s1:1", "T1112", enabled=False)]
    result = compute_coverage(use_cases, _EMPTY_APPL, index=_index())
    assert _state(result, "T1112")["state"] == "partial"

    result = compute_coverage(use_cases, _EMPTY_APPL,
                              disabled_counts_as_coverage=True, index=_index())
    assert _state(result, "T1112")["state"] == "covered"


def test_confidence_thresholds():
    idx = _index()
    # exactly 0.7 counts as covered
    result = compute_coverage([_uc("s1:1", "T1112", confidence=0.7, source="ai")],
                              _EMPTY_APPL, index=idx)
    assert _state(result, "T1112")["state"] == "covered"
    # mid-band is partial
    result = compute_coverage([_uc("s1:1", "T1112", confidence=0.5, source="ai")],
                              _EMPTY_APPL, index=idx)
    assert _state(result, "T1112")["state"] == "partial"
    # below 0.4 doesn't count at all
    result = compute_coverage([_uc("s1:1", "T1112", confidence=0.39, source="ai")],
                              _EMPTY_APPL, index=idx)
    assert _state(result, "T1112")["state"] == "not_covered"


def test_unknown_enabled_treated_as_enabled_with_assumption():
    result = compute_coverage([_uc("s1:1", "T1112", enabled=None)],
                              _EMPTY_APPL, index=_index())
    assert _state(result, "T1112")["state"] == "covered"
    assert any("treated as enabled" in a for a in result["assumptions"])


def test_revoked_mapping_remaps_to_successor():
    result = compute_coverage([_uc("s1:1", "T1998")], _EMPTY_APPL, index=_index())
    assert _state(result, "T1112")["state"] == "covered"
    assert any(
        "now represented under T1112" in a and "framework update" in a
        for a in result["assumptions"]
    )
    # revoked technique itself is not in the register
    assert not any(r["technique_id"] == "T1998" for r in result["techniques"])


def test_invalid_mapping_ids_ignored_with_assumption():
    use_cases = [_uc("s1:1", "T99"), _uc("s1:2", "T4321")]
    result = compute_coverage(use_cases, _EMPTY_APPL, index=_index())
    assert result["overall"]["covered"] == 0
    assert any("'T99'" in a for a in result["assumptions"])
    assert any("'T4321'" in a for a in result["assumptions"])


def test_subtechnique_rollup_parent_partial():
    result = compute_coverage([_uc("s1:1", "T1059.001")], _EMPTY_APPL, index=_index())
    assert _state(result, "T1059.001")["state"] == "covered"
    assert _state(result, "T1059")["state"] == "partial"
    assert _state(result, "T1059.002")["state"] == "not_covered"


def test_multi_tactic_technique_counts_in_every_tactic():
    result = compute_coverage([_uc("s1:1", "T1112")], _EMPTY_APPL, index=_index())
    tactics = {t["id"]: t for t in result["domains"]["enterprise"]["tactics"]}
    assert tactics["TA0002"]["covered"] == 1
    assert tactics["TA0005"]["covered"] == 1


def test_na_technique_stays_na_even_when_mapped():
    appl = {"na": {"T1112": {"reason": "customer-declared: out of scope",
                             "kind": "excluded_technique",
                             "source": "customer-declared"}},
            "assumptions": []}
    result = compute_coverage([_uc("s1:1", "T1112")], appl, index=_index())
    entry = _state(result, "T1112")
    assert entry["state"] == "not_applicable"
    assert entry["na_reason"] == "customer-declared: out of scope"


def test_golden_percentages_strict_and_weighted():
    # Register (non-revoked): T1059, T1059.001, T1059.002, T1112, T1999.
    # T1999 N/A (deprecated) -> applicable = 4.
    # T1059.001 covered; T1112 partial (0.5 conf); T1059 partial via rollup;
    # T1059.002 not covered.
    appl = {"na": {"T1999": {"reason": "deprecated in ATT&CK v19.1",
                             "kind": "deprecated", "source": "derived"}},
            "assumptions": []}
    use_cases = [
        _uc("s1:1", "T1059.001"),
        _uc("s1:2", "T1112", confidence=0.5, source="ai"),
    ]
    result = compute_coverage(use_cases, appl, index=_index())
    overall = result["overall"]
    assert overall == {
        "covered": 1, "partial": 2, "not_covered": 1, "not_applicable": 1,
        "applicable": 4, "strict_pct": 25.0, "weighted_pct": 50.0,
    }
    assert result["attack_version"] == "19.1"
    assert result["params"]["disabled_counts_as_coverage"] is False
