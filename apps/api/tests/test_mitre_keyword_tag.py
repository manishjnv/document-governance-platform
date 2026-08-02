"""Unit tests for the deterministic keyword-tagging pre-pass (Phase 6).
Pure — synthetic index for matcher semantics, real pinned dataset for the
alias map. No DB, no LLM."""

from app.mitre import keyword_tag
from app.mitre.attack_data import DEFAULT, AttackIndex
from app.mitre.keyword_tag import KEYWORD_CONFIDENCE, keyword_tag_rows


def _t(tid, name, **overrides):
    tech = {
        "id": tid,
        "name": name,
        "tactics": ["TA0002"],
        "platforms": ["Windows"],
        "data_sources": [],
        "is_subtechnique": "." in tid,
        "parent_id": tid.split(".")[0] if "." in tid else None,
        "deprecated": False,
        "revoked": False,
        "superseded_by": None,
        "summary": "",
    }
    tech.update(overrides)
    return tech


def _index(enterprise=(), mobile=()):
    return AttackIndex({
        "version": "19.1",
        "domains": {
            "enterprise": {"tactics": [], "techniques": list(enterprise)},
            "mobile": {"tactics": [], "techniques": list(mobile)},
        },
    })


def _row(name, description="", logic="", row_ref="s:1"):
    return {"row_ref": row_ref, "name": name, "description": description, "logic": logic}


def _ids(result, row_ref="s:1"):
    return sorted(m["technique_id"] for m in result.get(row_ref, []))


# --- technique-name matching (synthetic index) ---

def test_name_whole_phrase_match_shape():
    index = _index(enterprise=[_t("T1055", "Process Injection")])
    result = keyword_tag_rows(
        [_row("Process injection detected via CreateRemoteThread")], index=index
    )
    (mapping,) = result["s:1"]
    assert mapping["technique_id"] == "T1055"
    assert mapping["source"] == "keyword"
    assert mapping["confidence"] == KEYWORD_CONFIDENCE
    assert "process injection" in mapping["rationale"]


def test_name_requires_word_boundary():
    index = _index(enterprise=[_t("T1053.005", "Scheduled Task")])
    assert keyword_tag_rows([_row("rescheduled task backlog")], index=index) == {}


def test_short_names_are_skipped():
    index = _index(enterprise=[_t("T1053.002", "At")])
    assert keyword_tag_rows([_row("alert at job start")], index=index) == {}


def test_cross_domain_ambiguous_names_are_dropped():
    index = _index(
        enterprise=[_t("T1566", "Phishing Message")],
        mobile=[_t("T1660", "Phishing Message")],
    )
    assert keyword_tag_rows([_row("Phishing message reported by user")], index=index) == {}


def test_single_word_names_are_not_indexed():
    # "Databases" (T1213.006-style) is a generic category label — single
    # words only map via the curated alias file (adversarial finding V1).
    index = _index(enterprise=[_t("T1213.006", "Databases")])
    assert keyword_tag_rows([_row("Sensitive databases access audit")], index=index) == {}


def test_pre_compromise_only_techniques_are_not_indexed():
    recon = _t("T1583.002", "DNS Server", tactics=["TA0043"])
    execution = _t("T1055.999", "DNS Server", tactics=["TA0002"])
    # recon-only -> excluded entirely
    assert keyword_tag_rows(
        [_row("DNS server health alert")], index=_index(enterprise=[recon])
    ) == {}
    # same name under a post-compromise tactic -> matches
    result = keyword_tag_rows(
        [_row("DNS server health alert")], index=_index(enterprise=[execution])
    )
    assert _ids(result) == ["T1055.999"]


def test_recon_category_names_do_not_fire_on_real_dataset():
    # Adversarial review V1: benign ops rules must not map to
    # Reconnaissance/Resource-Development category-word techniques.
    rows = [
        _row("AWS IAM Credentials Exposed in Public S3 Bucket", row_ref="s:1"),
        _row("Critical Vulnerabilities Detected on Host (Qualys)", row_ref="s:2"),
        _row("Sensitive Databases Access Audit", row_ref="s:3"),
        _row("DNS Server Health Alert", row_ref="s:4"),
        _row("Unauthorized Software Installation Alert", row_ref="s:5"),
        _row("Blocklisted IP Addresses Contacted", row_ref="s:6"),
    ]
    assert keyword_tag_rows(rows) == {}


def test_field_cap_bounds_scan_cost():
    # An oversized logic cell is truncated at _FIELD_CAP before scanning —
    # an alias hidden beyond the cap must not match (adversarial finding V2).
    beyond = "x " * (keyword_tag._FIELD_CAP // 2) + " mimikatz"
    within = ("x " * 100) + " mimikatz"
    assert keyword_tag_rows([_row("Verbose rule", logic=beyond)]) == {}
    assert _ids(keyword_tag_rows([_row("Verbose rule", logic=within)])) == ["T1003.001"]


def test_deprecated_and_revoked_names_not_indexed():
    index = _index(
        enterprise=[
            _t("T1111", "Old Technique Name", deprecated=True),
            _t("T2222", "Gone Technique Name", revoked=True),
        ]
    )
    assert keyword_tag_rows(
        [_row("Old technique name and gone technique name")], index=index
    ) == {}


def test_alias_target_missing_from_index_is_dropped():
    # Alias file targets real IDs; against an index without them, resolve()
    # returns unknown and nothing is emitted.
    index = _index(enterprise=[_t("T1055", "Process Injection")])
    assert keyword_tag_rows([_row("Mimikatz activity")], index=index) == {}


def test_field_join_cannot_fake_adjacency():
    index = _index(enterprise=[_t("T1078.004", "Cloud Accounts")])
    # name ends "cloud", description starts "accounts" — must NOT match.
    assert keyword_tag_rows(
        [_row("logins to cloud", description="accounts audit")], index=index
    ) == {}


# --- alias matching (real pinned dataset) ---

def test_alias_match_real_dataset():
    result = keyword_tag_rows([_row("Mimikatz credential access")])
    assert _ids(result) == ["T1003.001"]


def test_alias_matches_in_logic_field():
    result = keyword_tag_rows(
        [_row("Suspicious admin activity", logic='CommandLine contains "wevtutil cl Security"')]
    )
    # The alias file states the widely-known T1070.001; v19.1 revokes it in
    # favor of T1685.005 and resolve() remaps — assert the canonical result.
    expected, status = DEFAULT.resolve("T1070.001")
    assert status == "remapped"
    assert _ids(result) == [expected]


def test_at_exe_only_fires_on_literal_dotted_form():
    hit = keyword_tag_rows([_row("at.exe job creation")])
    miss = keyword_tag_rows([_row("look at exe files dropped in temp")])
    assert _ids(hit) == ["T1053.002"]
    assert miss == {}


def test_enc_flag_not_fired_by_hyphenated_english():
    hit = keyword_tag_rows([_row("PowerShell launched with -enc argument")])
    miss = keyword_tag_rows([_row("base64-encoded payload observed")])
    assert "T1059.001" in _ids(hit)
    assert miss == {}


def test_cmd_alias_does_not_fire_inside_command():
    assert keyword_tag_rows([_row("command and control beacon detected")]) == {}


def test_name_and_alias_dedup_to_one_mapping():
    result = keyword_tag_rows([_row("PowerShell abuse", description="powershell.exe spawned")])
    assert _ids(result) == ["T1059.001"]
    assert len(result["s:1"]) == 1


def test_unmatched_rows_absent():
    result = keyword_tag_rows(
        [_row("Data volume anomaly", logic="stats by host"), _row("Rclone exfil", row_ref="s:2")]
    )
    assert "s:1" not in result
    assert _ids(result, "s:2") == ["T1567.002"]


def test_every_alias_target_resolves_in_pinned_dataset():
    for pattern, technique_id in keyword_tag._load_aliases():
        canonical, status = DEFAULT.resolve(technique_id)
        assert status in ("ok", "remapped"), (
            f"alias '{pattern}' -> {technique_id} no longer resolves "
            f"({status}) in ATT&CK v{DEFAULT.version}"
        )
        assert canonical
