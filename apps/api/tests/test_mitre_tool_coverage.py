"""Tool-native detection credit (MITRE_TOOL_COVERAGE_PLAN.md, 2026-08-19).
Pure-function tests: curated-data validity, synonym matching, overlay math,
and the two-numbers invariant (overlay never touches the stored figures)."""

from app.mitre import attack_data
from app.mitre.report_common import compute_tool_overlay


def _results(states: dict) -> list:
    return [
        {"technique_id": tid, "domain": "enterprise", "tactics": ["TA0002"],
         "state": state}
        for tid, state in states.items()
    ]


def test_tool_coverage_file_is_sourced_and_valid():
    cfg = attack_data.load_tool_coverage()
    assert cfg.get("caveat")
    core = cfg.get("core_evaluated_techniques") or []
    assert len(core) >= 20
    for tid in core:
        canonical, status = attack_data.DEFAULT.resolve(tid)
        assert status in ("ok", "remapped"), (tid, status)
    for key, tool in (cfg.get("tools") or {}).items():
        assert tool.get("label"), key
        assert tool.get("synonyms"), key
        # every entry must cite a published evaluation round
        assert "MITRE ATT&CK Evaluations" in (tool.get("source") or ""), key
        assert tool.get("url"), key


def test_overlay_matches_synonyms_and_computes_second_number():
    results = _results({
        "T1003.001": "not_covered",   # in the core evaluated set -> credit
        "T1059.001": "covered",       # already covered -> no credit needed
        "T1027": "partial",           # credited for display, not for the pct
        "T1112": "not_covered",       # in core set -> credit
        "T1200": "not_applicable",    # outside the applicable denominator
    })
    overlay = compute_tool_overlay(
        ["CrowdStrike Falcon EDR (all endpoints)", "Some Unknown Product"],
        results,
    )
    assert overlay is not None
    assert [t["label"] for t in overlay["matched_tools"]] == ["CrowdStrike Falcon"]
    assert overlay["unmatched"] == ["Some Unknown Product"]
    assert set(overlay["by_technique"]) == {"T1003.001", "T1027", "T1112"}
    assert overlay["extra_open_covered"] == 2
    # applicable = 4 (covered 1 + partial 1 + open 2); adjusted = (1+2)/4
    assert overlay["adjusted_pct"] == 75.0
    assert "MITRE ATT&CK Evaluations" in overlay["caveat"]


def test_overlay_none_without_a_matched_tool():
    assert compute_tool_overlay(["HomeGrown SIEM"], _results({"T1112": "not_covered"})) is None
    assert compute_tool_overlay([], _results({"T1112": "not_covered"})) is None


def test_overlay_never_touches_the_rule_based_numbers():
    # the overlay is read-only over its inputs — mutation would corrupt the
    # stored JSONB when called at read time from the router
    results = _results({"T1003.001": "not_covered"})
    before = [dict(r) for r in results]
    compute_tool_overlay(["sentinelone"], results)
    assert results == before
