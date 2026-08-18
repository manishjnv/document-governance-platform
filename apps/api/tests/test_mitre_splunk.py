"""Splunk connector unit tests — config validation, entry→CSV mapping,
paginated pull via a faked transport. No test touches the network (same
strategy as test_mitre_siem.py's Sentinel coverage)."""

import pytest

from app.mitre.connectors import base as connectors_base
from app.mitre.connectors import splunk
from app.mitre.connectors.base import ConnectorConfigError, ConnectorError

_GOOD_CONFIG = {"host": "Acme.SplunkCloud.com", "port": 8089, "app": "search"}

_ENTRIES = [
    {
        "name": "MHE001_P1_Suspicious Login",
        "acl": {"app": "search"},
        "content": {
            "search": "index=okta action=login | stats count",
            "description": "Flags odd logins",
            "disabled": False,
            "action.correlationsearch.annotations": '{"mitre_attack": ["T1078", "T1078"]}',
        },
    },
    {
        "name": "MHE002_P2_Old Rule",
        "acl": {"app": "es_app"},
        "content": {"search": "", "disabled": "1"},
    },
]


def test_validate_config_normalizes():
    cfg = splunk.validate_config(_GOOD_CONFIG)
    assert cfg == {"host": "acme.splunkcloud.com", "port": 8089, "app": "search"}
    # defaults: port 8089, app "-" (all apps)
    assert splunk.validate_config({"host": "x.example.com"}) == {
        "host": "x.example.com",
        "port": 8089,
        "app": "-",
    }


@pytest.mark.parametrize(
    "bad",
    [
        {"host": "https://x.example.com"},          # scheme
        {"host": "x.example.com:8089"},             # port in host
        {"host": "intranet"},                       # single label
        {"host": "x.example.com", "port": 9999},    # port outside allowlist
        {"host": "x.example.com", "app": ".."},     # traversal token
        {},                                         # missing host
    ],
)
def test_validate_config_rejects(bad):
    with pytest.raises(ConnectorConfigError):
        splunk.validate_config(bad)


def test_entries_to_csv_mapping():
    csv_bytes, warnings = splunk._entries_to_csv(_ENTRIES)
    text = csv_bytes.decode("utf-8")
    lines = text.strip().split("\n")
    assert lines[0].startswith("Rule Name,")
    assert "MHE001_P1_Suspicious Login" in lines[1]
    assert "T1078" in lines[1] and lines[1].count("T1078") == 1  # deduped
    assert "Enabled" in lines[1] and "Splunk · search" in lines[1]
    assert "Disabled" in lines[2]
    assert any("no query text" in w for w in warnings)  # the query-less row


def test_technique_ids_malformed_json_falls_back_to_regex():
    assert splunk._technique_ids('{"mitre_attack": ["T1059.001"') == ["T1059.001"]
    assert splunk._technique_ids(None) == []


def _fake_fetch(monkeypatch, responses):
    calls = []

    def fake(host, path, *, allowed_hosts, method="GET", headers=None, body=None, port=443):
        calls.append({"host": host, "path": path, "port": port})
        assert host in allowed_hosts
        return responses[len(calls) - 1]

    monkeypatch.setattr(splunk, "fetch_json", fake)
    return calls


def test_pull_paginates_and_dispatches(monkeypatch):
    page1 = {"entry": [_ENTRIES[0]], "paging": {"total": 2}}
    page2 = {"entry": [_ENTRIES[1]], "paging": {"total": 2}}
    calls = _fake_fetch(monkeypatch, [(200, page1), (200, page2)])
    # through the base dispatch — proves "splunk" is a registered platform
    result = connectors_base.pull_rules("splunk", _GOOD_CONFIG, "tok")
    assert result["rule_count"] == 2
    assert result["stats"] == {"pages": 2, "platform": "splunk"}
    assert result["derived_log_sources"] == [] and result["unmapped_connectors"] == []
    assert calls[0]["port"] == 8089
    assert calls[0]["path"].startswith("/servicesNS/-/search/saved/searches?")
    assert "offset=1" in calls[1]["path"]


@pytest.mark.parametrize(
    "status,match",
    [(401, "rejected the token"), (403, "cannot list saved searches"), (404, "app name")],
)
def test_pull_maps_http_errors(monkeypatch, status, match):
    _fake_fetch(monkeypatch, [(status, {})])
    with pytest.raises(ConnectorError, match=match):
        splunk.pull(splunk.validate_config(_GOOD_CONFIG), "tok")


def test_pull_empty_instance_errors(monkeypatch):
    _fake_fetch(monkeypatch, [(200, {"entry": [], "paging": {"total": 0}})])
    with pytest.raises(ConnectorError, match="no saved searches"):
        splunk.pull(splunk.validate_config(_GOOD_CONFIG), "tok")


def test_egress_refuses_ports_outside_allowlist():
    # the port gate fires before any DNS resolution or connection
    from app.mitre.connectors import egress

    assert egress.ALLOWED_PORTS == frozenset({443, 8089})
    with pytest.raises(egress.EgressError, match="port outside"):
        egress.fetch_json(
            "x.example.com", "/", allowed_hosts=frozenset({"x.example.com"}), port=9999
        )
