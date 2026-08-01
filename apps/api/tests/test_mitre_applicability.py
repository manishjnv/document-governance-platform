"""Applicability engine + attack_data unit tests (MITRE assessment Phase 0).

Golden cases run against a small synthetic dataset via the injectable
AttackIndex; a few smoke checks run against the real pinned attack.json.
"""

from app.mitre import attack_data
from app.mitre.applicability import (
    NO_INVENTORY_ASSUMPTION,
    compute_applicability,
)
from app.mitre.attack_data import AttackIndex, is_valid_technique_id


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
                "tactics": [{"id": "TA0002", "shortname": "execution", "name": "Execution"}],
                "techniques": [
                    _t("T1059", platforms=["Windows", "Linux", "macOS"]),
                    _t("T1059.001", platforms=["Windows"]),
                    _t("T1553.001", platforms=["macOS"]),
                    _t("T1595", platforms=["PRE"]),
                    _t("T1200", platforms=["Windows"]),
                    _t("T1999", deprecated=True),
                    _t("T1998", revoked=True, superseded_by="T1059"),
                ],
            },
            "ics": {
                "tactics": [{"id": "TA0100", "shortname": "ics-x", "name": "ICS X"}],
                # Real v19.1 ICS techniques carry the literal platform "None".
                "techniques": [_t("T0800", platforms=["None"])],
            },
            "mobile": {
                "tactics": [{"id": "TA0027", "shortname": "mob-x", "name": "Mob X"}],
                "techniques": [_t("T1400", platforms=["Android"])],
            },
        },
    })


def _env(**overrides):
    env = {
        "platforms": ["Windows"],
        "has_ics_assets": False,
        "has_managed_mobile": False,
        "inventory_provided": True,
        "exclusions": [],
    }
    env.update(overrides)
    return env


def test_domain_gating():
    result = compute_applicability(_env(), index=_index())
    assert result["na"]["T0800"]["reason"] == (
        "ICS matrix: no OT/ICS assets declared in inventory"
    )
    assert result["na"]["T1400"]["reason"] == (
        "Mobile matrix: no managed mobile fleet declared in inventory"
    )
    assert result["applicable_domains"] == ["enterprise"]

    open_env = _env(has_ics_assets=True, has_managed_mobile=True,
                    platforms=["Windows", "Android"])
    result = compute_applicability(open_env, index=_index())
    assert "T0800" not in result["na"]
    assert "T1400" not in result["na"]
    assert result["applicable_domains"] == ["enterprise", "ics", "mobile"]


def test_platform_filtering_names_missing_platform():
    result = compute_applicability(_env(), index=_index())
    assert result["na"]["T1553.001"] == {
        "reason": "targets macOS; macOS not in asset inventory",
        "kind": "platform",
        "source": "derived",
    }
    assert "T1059" not in result["na"]      # Windows intersects
    assert "T1059.001" not in result["na"]
    assert "T1595" not in result["na"]      # PRE techniques never filtered

    # "None"-platform techniques (all of ICS in v19.1) are never
    # platform-filtered — only domain gating applies to them.
    open_ics = compute_applicability(_env(has_ics_assets=True), index=_index())
    assert "T0800" not in open_ics["na"]


def test_customer_exclusion_verbatim_and_most_specific_wins():
    env = _env(exclusions=[
        {"target": "T1553.001", "reason": "accepted risk, physical controls"},
    ])
    result = compute_applicability(env, index=_index())
    # Technique-level customer exclusion outranks the derived platform N/A.
    assert result["na"]["T1553.001"] == {
        "reason": "accepted risk, physical controls",
        "kind": "excluded_technique",
        "source": "customer-declared",
    }


def test_parent_exclusion_covers_subtechniques():
    env = _env(exclusions=[{"target": "T1059", "reason": "out of scope"}])
    result = compute_applicability(env, index=_index())
    assert result["na"]["T1059"]["source"] == "customer-declared"
    assert result["na"]["T1059.001"]["reason"] == "out of scope"


def test_domain_exclusion_attributed():
    env = _env(has_managed_mobile=True, platforms=["Windows", "Android"],
               exclusions=[{"target": "mobile", "reason": "BYOD unmanaged, not SOC scope"}])
    result = compute_applicability(env, index=_index())
    assert result["na"]["T1400"] == {
        "reason": "BYOD unmanaged, not SOC scope",
        "kind": "excluded_domain",
        "source": "customer-declared",
    }
    assert "mobile" not in result["applicable_domains"]


def test_platform_exclusion():
    env = _env(platforms=["Windows", "macOS"],
               exclusions=[{"target": "macOS", "reason": "MSSP scope"}])
    result = compute_applicability(env, index=_index())
    assert result["na"]["T1553.001"] == {
        "reason": "MSSP scope",
        "kind": "excluded_platform",
        "source": "customer-declared",
    }
    assert "T1059" not in result["na"]  # Windows still assessable


def test_no_inventory_filters_nothing_but_exclusions():
    env = {
        "platforms": [],
        "has_ics_assets": False,
        "has_managed_mobile": False,
        "inventory_provided": False,
        "exclusions": [{"target": "T1200", "reason": "accepted risk"}],
    }
    result = compute_applicability(env, index=_index())
    assert NO_INVENTORY_ASSUMPTION in result["assumptions"]
    assert "T1553.001" not in result["na"]  # no platform filtering
    assert "T0800" not in result["na"]      # no domain gating
    assert "T1400" not in result["na"]
    assert result["na"]["T1200"]["source"] == "customer-declared"
    assert result["na"]["T1999"]["kind"] == "deprecated"  # dataset-derived, stays


def test_deprecated_reason_names_version():
    result = compute_applicability(_env(), index=_index())
    assert result["na"]["T1999"]["reason"] == "deprecated in ATT&CK v19.1"


def test_unknown_exclusion_target_ignored_with_assumption():
    env = _env(exclusions=[{"target": "T4321", "reason": "whatever"}])
    result = compute_applicability(env, index=_index())
    assert "T4321" not in result["na"]
    assert any("T4321" in a for a in result["assumptions"])


def test_revoked_techniques_never_in_na():
    result = compute_applicability(_env(), index=_index())
    assert "T1998" not in result["na"]


def test_technique_id_validation():
    assert is_valid_technique_id("T1059")
    assert is_valid_technique_id("T1059.001")
    for bad in ("T105", "T10590", "1059", "T1059.1", "T1059.0011", "", None):
        assert not is_valid_technique_id(bad)


def test_real_dataset_smoke():
    index = attack_data.DEFAULT
    assert index.version == "19.1"
    assert len(index.techniques("enterprise")) > 600
    assert len(index.techniques("ics")) > 50
    assert len(index.techniques("mobile")) > 75
    powershell = index.get("T1059.001")
    assert powershell["parent_id"] == "T1059"
    assert powershell["domain"] == "enterprise"
    assert index.resolve("T1059.001") == ("T1059.001", "ok")
    assert index.resolve("not-an-id") == (None, "malformed")
    assert index.resolve("T4242") == (None, "unknown")


def test_priorities_file_ids_are_active_in_pinned_dataset():
    priorities = attack_data.load_technique_priorities()
    assert len(priorities["techniques"]) >= 35
    for entry in priorities["techniques"]:
        canonical, status = attack_data.DEFAULT.resolve(entry["technique_id"])
        assert status == "ok", f"{entry['technique_id']}: {status}"
        assert canonical == entry["technique_id"]
        assert entry["tier"] in (1, 2, 3)
