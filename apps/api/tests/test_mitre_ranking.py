"""Gap-ranking + roadmap-bucketing unit tests (MITRE Phase 2). Pure —
synthetic dataset, injected priorities, no DB/LLM."""

from app.mitre.attack_data import AttackIndex
from app.mitre.ranking import rank_gaps


def _t(tid, data_sources=(), tactics=("TA0002",)):
    return {
        "id": tid,
        "name": f"name-{tid}",
        "tactics": list(tactics),
        "platforms": ["Windows"],
        "data_sources": list(data_sources),
        "is_subtechnique": "." in tid,
        "parent_id": tid.split(".")[0] if "." in tid else None,
        "deprecated": False,
        "revoked": False,
        "superseded_by": None,
        "summary": "",
    }


def _index():
    return AttackIndex({
        "version": "19.1",
        "domains": {
            "enterprise": {
                "tactics": [
                    {"id": "TA0001", "shortname": "initial-access", "name": "Initial Access"},
                    {"id": "TA0002", "shortname": "execution", "name": "Execution"},
                ],
                "techniques": [
                    _t("T1059.001", data_sources=["Process Creation", "Command Execution"]),
                    _t("T1112", data_sources=["Windows Registry Key Modification"]),
                    _t("T1046", data_sources=["Network Traffic Flow"]),
                    _t("T1530", data_sources=["Cloud Storage Access"]),
                    _t("T1200", data_sources=[]),
                    _t("T1566", data_sources=["Application Log Content"], tactics=["TA0001"]),
                ],
            },
        },
    })


_PRIORITIES = {
    "techniques": [
        {"technique_id": "T1059.001", "tier": 1},
        {"technique_id": "T1112", "tier": 2},
        {"technique_id": "T1046", "tier": 3},
    ]
}


def _result(tid, state, tactics=("TA0002",)):
    return {
        "technique_id": tid,
        "domain": "enterprise",
        "tactics": list(tactics),
        "state": state,
        "na_reason": None,
        "use_case_refs": [],
    }


def _rank(techniques, log_sources=(), tooling=()):
    return rank_gaps(
        techniques, list(log_sources), list(tooling),
        index=_index(), priorities=_PRIORITIES,
    )


def test_feasibility_buckets():
    techniques = [
        _result("T1059.001", "not_covered"),  # endpoint telemetry, onboarded
        _result("T1046", "not_covered"),      # network — only NDR tooling owned
        _result("T1530", "not_covered"),      # cloud — nothing
        _result("T1200", "not_covered"),      # no ATT&CK telemetry listed
    ]
    # WinEventLog provides endpoint/identity/registry — NOT network (unlike
    # Sysmon, whose event 3 covers network connections too).
    ranked = _rank(techniques, log_sources=["WinEventLog"], tooling=["Corelight NDR"])
    by_id = {g["technique_id"]: g for g in ranked["gaps"]}

    assert by_id["T1059.001"]["feasibility"] == "short"
    assert by_id["T1059.001"]["via"] == "WinEventLog"
    assert "already onboarded" in by_id["T1059.001"]["hint"]

    assert by_id["T1046"]["feasibility"] == "mid"
    assert by_id["T1046"]["via"] == "Corelight NDR"

    assert by_id["T1530"]["feasibility"] == "long"
    assert by_id["T1200"]["feasibility"] == "long"
    assert "bespoke" in by_id["T1200"]["hint"]

    roadmap = ranked["roadmap"]
    assert [g["technique_id"] for g in roadmap["short"]] == ["T1059.001"]
    assert [g["technique_id"] for g in roadmap["mid"]] == ["T1046"]
    assert {g["technique_id"] for g in roadmap["long"]} == {"T1530", "T1200"}


def test_tier_then_feasibility_ordering():
    # T1112 (tier 2, short via Sysmon registry) must outrank T1046 (tier 3)
    # but stay below T1059.001 (tier 1); unlisted T1566 ranks last.
    techniques = [
        _result("T1566", "not_covered", tactics=["TA0001"]),
        _result("T1046", "not_covered"),
        _result("T1112", "not_covered"),
        _result("T1059.001", "not_covered"),
    ]
    ranked = _rank(techniques, log_sources=["Sysmon"], tooling=[])
    order = [g["technique_id"] for g in ranked["gaps"]]
    assert order == ["T1059.001", "T1112", "T1046", "T1566"]
    assert [g["rank"] for g in ranked["gaps"]] == [1, 2, 3, 4]
    assert ranked["gaps"][3]["tier"] == 4  # unlisted -> below tier 3


def test_not_covered_ranks_before_partial_same_tier_and_feasibility():
    # Same tier + same feasibility (both short via Sysmon): a hole beats a
    # partial.
    ranked = rank_gaps(
        [_result("T1059.001", "partial"), _result("T1112", "not_covered")],
        ["Sysmon"], [],
        index=_index(),
        priorities={"techniques": [
            {"technique_id": "T1059.001", "tier": 2},
            {"technique_id": "T1112", "tier": 2},
        ]},
    )
    assert [g["technique_id"] for g in ranked["gaps"]] == ["T1112", "T1059.001"]


def test_covered_and_na_excluded():
    techniques = [
        _result("T1059.001", "covered"),
        _result("T1112", "not_applicable"),
        _result("T1046", "not_covered"),
    ]
    ranked = _rank(techniques)
    assert [g["technique_id"] for g in ranked["gaps"]] == ["T1046"]


# --- Phase 6: mobile/OT categories, vendor names, no-AI guard ---

import inspect
import re as _re

import pytest

from app.mitre import applicability, attack_data, coverage, ingest, keyword_tag
from app.mitre import ranking as ranking_module
from app.mitre.ranking import component_category


def test_component_category_phase6_golden():
    assert component_category("Application Permission") == "mobile"
    assert component_category("System Settings") == "mobile"
    assert component_category("Device Alarm") == "ot"
    assert component_category("Asset Inventory") == "ot"
    assert component_category("Host Status") == "endpoint"
    assert component_category("Image Creation") == "cloud"
    assert component_category("Image Load") == "endpoint"  # NOT container images
    # Recon/threat-intel components stay unmatched on purpose (-> honest "long").
    assert component_category("Response Content") is None
    assert component_category("Social Media") is None
    assert component_category("Domain Registration") is None


def _single_tech_index(data_sources):
    return AttackIndex({
        "version": "19.1",
        "domains": {"enterprise": {"tactics": [], "techniques": [
            _t("T9999", data_sources=data_sources)
        ]}},
    })


def _bucket(data_sources, log_sources=(), tooling=()):
    ranked = rank_gaps(
        [_result("T9999", "not_covered")], list(log_sources), list(tooling),
        index=_single_tech_index(data_sources), priorities={"techniques": []},
    )
    gap = ranked["gaps"][0]
    return gap["feasibility"], gap["via"]


def test_mobile_technique_buckets_by_mdm():
    feasibility, via = _bucket(["Application Permission"], log_sources=["Microsoft Intune"])
    assert (feasibility, via) == ("short", "Microsoft Intune")
    feasibility, _ = _bucket(["Application Permission"], tooling=["Jamf Pro"])
    assert feasibility == "mid"
    feasibility, _ = _bucket(["Application Permission"], log_sources=["Sysmon"], tooling=["CrowdStrike"])
    assert feasibility == "long"


def test_ot_technique_buckets_by_ot_monitoring():
    feasibility, via = _bucket(["Device Alarm"], log_sources=["Claroty CTD"])
    assert (feasibility, via) == ("short", "Claroty CTD")
    feasibility, _ = _bucket(["Device Alarm"], tooling=["Nozomi Networks"])
    assert feasibility == "mid"


def test_new_vendor_names_map_to_endpoint():
    feasibility, via = _bucket(["Process Creation"], log_sources=["Tanium"])
    assert (feasibility, via) == ("short", "Tanium")


def test_substring_safety_no_fake_ot_or_identity():
    # "Azure Log Analytics" contains "ics"; "Remote access logs" contains
    # "ot" — neither may provide the OT category (keywords avoid bare
    # too-short substrings).
    feasibility, _ = _bucket(
        ["Device Alarm"], log_sources=["Azure Log Analytics", "Remote access logs"]
    )
    assert feasibility == "long"


@pytest.mark.parametrize(
    "module",
    [ranking_module, keyword_tag, ingest, coverage, applicability, attack_data],
    ids=lambda m: m.__name__.rsplit(".", 1)[-1],
)
def test_deterministic_modules_import_no_ai(module):
    """Guard against drift: the deterministic layer must never grow an
    LLM/agent import."""
    imports = _re.findall(
        r"^\s*(?:from|import)\s+([\w.]+)", inspect.getsource(module), _re.M
    )
    assert not any(
        name.startswith("app.ai") or name.endswith("agents") or "openrouter" in name
        for name in imports
    ), f"{module.__name__} imports an AI module: {imports}"


# --- Phase A4: Crown Jewels -> gap-ranking lift ---

from app.mitre.ranking import crown_jewel_hints  # noqa: E402


def test_crown_jewel_hints_bridge_goldens():
    hints, unmatched = crown_jewel_hints([
        "Primary vCenter cluster", "Customer database (Oracle DB)",
        "Payment gateway", "Domain Controllers (AD)", "some random asset",
    ])
    assert hints["platforms"] == {"ESXi"}
    assert hints["categories"] == {"application", "cloud", "identity"}
    assert unmatched == ["some random asset"]


def test_crown_jewel_hints_no_entries_is_noop():
    hints, unmatched = crown_jewel_hints([])
    assert hints == {"platforms": set(), "categories": set()}
    assert unmatched == []
    hints, unmatched = crown_jewel_hints(None)
    assert hints == {"platforms": set(), "categories": set()}
    assert unmatched == []


def test_crown_jewel_lift_within_tier_never_jumps_tier():
    # Two techniques in the SAME tier, one crown-jewel-relevant (matches
    # the "application"/"cloud" hint from a database crown jewel via its
    # Cloud Storage Access data source) -> it must rank first within the
    # tier. A tier-1 technique still outranks both regardless.
    techniques = [
        _result("T1059.001", "not_covered"),  # tier 1 (via shared _PRIORITIES pattern below)
        _result("T1530", "not_covered"),      # cloud storage access -> "cloud" category
        _result("T1112", "not_covered"),      # registry -> no crown-jewel match
    ]
    priorities = {"techniques": [
        {"technique_id": "T1059.001", "tier": 1},
        {"technique_id": "T1530", "tier": 2},
        {"technique_id": "T1112", "tier": 2},
    ]}
    ranked = rank_gaps(
        techniques, ["Sysmon"], [], index=_index(), priorities=priorities,
        crown_jewels=["Customer database"],
    )
    order = [g["technique_id"] for g in ranked["gaps"]]
    assert order == ["T1059.001", "T1530", "T1112"]  # tier 1 first, then crown-jewel lift within tier 2
    assert ranked["gaps"][1]["crown_jewel_relevant"] is True
    assert ranked["gaps"][2]["crown_jewel_relevant"] is False


def test_crown_jewel_weighting_toggle_off_keeps_annotation_drops_lift():
    techniques = [
        _result("T1530", "not_covered"),
        _result("T1112", "not_covered"),
    ]
    priorities = {"techniques": [
        {"technique_id": "T1530", "tier": 2},
        {"technique_id": "T1112", "tier": 2},
    ]}
    ranked = rank_gaps(
        techniques, ["Sysmon"], [], index=_index(), priorities=priorities,
        crown_jewels=["Customer database"], crown_jewel_weighting=False,
    )
    by_id = {g["technique_id"]: g for g in ranked["gaps"]}
    # annotation survives even with the lift disabled...
    assert by_id["T1530"]["crown_jewel_relevant"] is True
    # ...but ordering falls back to id order (no lift applied)
    assert [g["technique_id"] for g in ranked["gaps"]] == ["T1112", "T1530"]


def test_no_crown_jewels_sheet_is_a_noop():
    ranked = _rank([_result("T1046", "not_covered")], log_sources=["Sysmon"])
    assert ranked["gaps"][0]["crown_jewel_relevant"] is False
    assert ranked["crown_jewel_unmatched"] == []


# --- Phase A6: Log Sources health columns downgrade short -> mid ---

def test_log_source_health_normalized_false_downgrades_to_mid():
    ranked = rank_gaps(
        [_result("T1059.001", "not_covered")], ["WinEventLog"], [],
        index=_index(), priorities=_PRIORITIES,
        log_source_health={"WinEventLog": {"normalized": False, "last_event_seen": None, "parser_format": None}},
    )
    gap = ranked["gaps"][0]
    assert gap["feasibility"] == "mid"
    assert gap["via"] == "WinEventLog"
    assert "not normalized" in gap["hint"]


def test_log_source_health_stale_last_event_downgrades_to_mid():
    from datetime import date, timedelta
    stale = (date.today() - timedelta(days=90)).isoformat()
    ranked = rank_gaps(
        [_result("T1059.001", "not_covered")], ["WinEventLog"], [],
        index=_index(), priorities=_PRIORITIES,
        log_source_health={"WinEventLog": {"normalized": True, "last_event_seen": stale, "parser_format": None}},
    )
    gap = ranked["gaps"][0]
    assert gap["feasibility"] == "mid"
    assert "no recent events" in gap["hint"]


def test_log_source_health_fresh_and_normalized_stays_short():
    from datetime import date, timedelta
    fresh = (date.today() - timedelta(days=1)).isoformat()
    ranked = rank_gaps(
        [_result("T1059.001", "not_covered")], ["WinEventLog"], [],
        index=_index(), priorities=_PRIORITIES,
        log_source_health={"WinEventLog": {"normalized": True, "last_event_seen": fresh, "parser_format": "CIM"}},
    )
    gap = ranked["gaps"][0]
    assert gap["feasibility"] == "short"


def test_log_source_health_absent_changes_nothing():
    ranked_without = rank_gaps(
        [_result("T1059.001", "not_covered")], ["WinEventLog"], [],
        index=_index(), priorities=_PRIORITIES,
    )
    ranked_with_empty = rank_gaps(
        [_result("T1059.001", "not_covered")], ["WinEventLog"], [],
        index=_index(), priorities=_PRIORITIES, log_source_health={},
    )
    assert ranked_without["gaps"][0]["feasibility"] == ranked_with_empty["gaps"][0]["feasibility"] == "short"
