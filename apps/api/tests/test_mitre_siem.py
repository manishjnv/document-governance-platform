"""Phase 13a SIEM-pull tests. NO test touches the network: DNS and the
pinned connection are faked at the egress seams, and the Sentinel API is
faked at fetch_json. Endpoint tests run against real edgp_test Postgres."""

import io
import json
import uuid

import pytest
from httpx import ASGITransport, AsyncClient

from app.auth import create_access_token
from app.mitre import ingest
from app.mitre.connectors import base as connectors_base
from app.mitre.connectors import egress, sentinel
from app.mitre.connectors.base import ConnectorConfigError, ConnectorError
from app.mitre.connectors.egress import EgressError
from app.models.organization import Organization
from app.models.user import User
from main import app

# ---------------------------------------------------------------------------
# egress.py — deny set, pinning, redirect/size discipline
# ---------------------------------------------------------------------------


def _fake_getaddrinfo(*ips):
    def fake(host, port, **kwargs):
        return [(2, 1, 6, "", (ip, port)) for ip in ips]
    return fake


@pytest.mark.parametrize(
    "ip",
    [
        "10.0.0.5",            # RFC-1918
        "192.168.1.1",
        "172.16.9.9",
        "127.0.0.1",           # loopback
        "169.254.169.254",     # cloud metadata / link-local
        "100.64.0.1",          # CGNAT
        "0.0.0.0",
        "224.0.0.1",           # multicast
        "::1",                 # v6 loopback
        "fe80::1",             # v6 link-local
        "fd00::1",             # v6 ULA
        "::ffff:10.0.0.1",     # v4-mapped v6 private
    ],
)
def test_deny_set_refuses_non_public_addresses(monkeypatch, ip):
    monkeypatch.setattr(egress.socket, "getaddrinfo", _fake_getaddrinfo(ip))
    with pytest.raises(EgressError, match="non-public"):
        egress._validated_ip("evil.example.com")


def test_deny_set_rejects_mixed_public_and_private(monkeypatch):
    # a rebinding name answering both public and private must lose outright
    monkeypatch.setattr(
        egress.socket, "getaddrinfo", _fake_getaddrinfo("8.8.8.8", "10.0.0.5")
    )
    with pytest.raises(EgressError, match="non-public"):
        egress._validated_ip("rebind.example.com")


def test_public_address_resolves(monkeypatch):
    monkeypatch.setattr(egress.socket, "getaddrinfo", _fake_getaddrinfo("8.8.8.8"))
    assert egress._validated_ip("api.example.com") == "8.8.8.8"


def test_fetch_json_refuses_host_outside_allowlist(monkeypatch):
    def explode(*a, **k):  # resolution must not even be attempted
        raise AssertionError("resolved a non-allowlisted host")
    monkeypatch.setattr(egress.socket, "getaddrinfo", explode)
    with pytest.raises(EgressError, match="allowlist"):
        egress.fetch_json(
            "attacker.example.com", "/x", allowed_hosts=frozenset({"good.example.com"})
        )


class _FakeResponse:
    def __init__(self, status, body=b"{}", headers=None):
        self.status = status
        self._body = body
        self._pos = 0
        self._headers = headers or {}

    def read(self, n):
        chunk = self._body[self._pos : self._pos + n]
        self._pos += n
        return chunk

    def getheader(self, name):
        return self._headers.get(name)


def _fake_conn_class(responses, seen):
    class _FakeConn:
        def __init__(self, host, pinned_ip):
            seen.append({"host": host, "pinned_ip": pinned_ip})
            self._response = responses.pop(0)

        def request(self, method, path, body=None, headers=None):
            seen[-1].update({"method": method, "path": path})

        def getresponse(self):
            return self._response

        def close(self):
            pass

    return _FakeConn


def _patched_fetch(monkeypatch, responses):
    seen = []
    monkeypatch.setattr(egress, "_validated_ip", lambda host: "8.8.8.8")
    monkeypatch.setattr(
        egress, "_PinnedHTTPSConnection", _fake_conn_class(responses, seen)
    )
    return seen


def test_fetch_json_pins_validated_ip_and_parses(monkeypatch):
    seen = _patched_fetch(monkeypatch, [_FakeResponse(200, b'{"ok": 1}')])
    status, payload = egress.fetch_json(
        "good.example.com", "/x", allowed_hosts=frozenset({"good.example.com"})
    )
    assert (status, payload) == (200, {"ok": 1})
    assert seen[0]["pinned_ip"] == "8.8.8.8"
    assert seen[0]["host"] == "good.example.com"  # SNI/Host stay the hostname


def test_fetch_json_rejects_redirects(monkeypatch):
    _patched_fetch(
        monkeypatch,
        [_FakeResponse(302, headers={"Location": "https://evil.example.com/"})],
    )
    with pytest.raises(EgressError, match="redirect"):
        egress.fetch_json(
            "good.example.com", "/x", allowed_hosts=frozenset({"good.example.com"})
        )


def test_fetch_json_caps_response_size(monkeypatch):
    _patched_fetch(monkeypatch, [_FakeResponse(200, b"x" * 300)])
    monkeypatch.setattr(egress, "MAX_RESPONSE_BYTES", 100)
    with pytest.raises(EgressError, match="large"):
        egress.fetch_json(
            "good.example.com", "/x", allowed_hosts=frozenset({"good.example.com"})
        )


def test_fetch_json_returns_4xx_for_connector_mapping(monkeypatch):
    _patched_fetch(monkeypatch, [_FakeResponse(403, b'{"error": "denied"}')])
    status, _ = egress.fetch_json(
        "good.example.com", "/x", allowed_hosts=frozenset({"good.example.com"})
    )
    assert status == 403


@pytest.mark.parametrize("retry_after", ["-5", "nan", "inf", "999999", "soon"])
def test_hostile_retry_after_never_crashes(monkeypatch, retry_after):
    # adversarial finding #1: Retry-After is attacker-influenced — clamp,
    # never let it reach time.sleep as a negative/NaN (ValueError -> 500)
    sleeps = []
    monkeypatch.setattr(egress.time, "sleep", lambda s: sleeps.append(s))
    _patched_fetch(
        monkeypatch,
        [
            _FakeResponse(429, headers={"Retry-After": retry_after}),
            _FakeResponse(200, b'{"ok": 1}'),
        ],
    )
    status, payload = egress.fetch_json(
        "good.example.com", "/x", allowed_hosts=frozenset({"good.example.com"})
    )
    assert (status, payload) == (200, {"ok": 1})
    assert len(sleeps) == 1
    assert 0.0 <= sleeps[0] <= egress.RETRY_AFTER_CAP


# ---------------------------------------------------------------------------
# sentinel.py — config validation, nextLink guard, normalization goldens
# ---------------------------------------------------------------------------

_GOOD_CONFIG = {
    "tenant_id": "11111111-2222-3333-4444-555555555555",
    "client_id": "aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee",
    "subscription_id": "99999999-8888-7777-6666-555555555555",
    "resource_group": "sec-rg",
    "workspace": "prod-sentinel",
}

_RULES = [
    {
        "name": "r1",
        "kind": "Scheduled",
        "properties": {
            "displayName": "Encoded PowerShell",
            "description": "Detects -enc launches",
            "query": "SecurityEvent | where CommandLine contains '-enc'",
            "enabled": True,
            "techniques": ["T1059"],
            "subTechniques": ["T1059.001"],
        },
    },
    {
        "name": "r2",
        "kind": "Scheduled",
        "properties": {
            "displayName": "RDP brute force",
            "description": "",
            "query": "SigninLogs | where ResultType != 0",
            "enabled": False,
            "techniques": ["T1110"],
        },
    },
    {
        "name": "f1",
        "kind": "Fusion",
        "properties": {
            "displayName": "Advanced multistage attack",
            "enabled": True,
            "techniques": [],
        },
    },
]


def test_validate_config_good_and_bad():
    assert sentinel.validate_config(_GOOD_CONFIG)["workspace"] == "prod-sentinel"
    with pytest.raises(ConnectorConfigError, match="tenant_id"):
        sentinel.validate_config({**_GOOD_CONFIG, "tenant_id": "not-a-guid"})
    with pytest.raises(ConnectorConfigError, match="workspace"):
        sentinel.validate_config({**_GOOD_CONFIG, "workspace": "x"})
    with pytest.raises(ConnectorConfigError):
        sentinel.validate_config("nope")
    # adversarial finding #2: dot-only / dot-edged resource groups would
    # splice a traversal token into the API path — rejected
    for bad_rg in ("..", ".", "foo.", ".foo"):
        with pytest.raises(ConnectorConfigError, match="resource_group"):
            sentinel.validate_config({**_GOOD_CONFIG, "resource_group": bad_rg})
    assert sentinel.validate_config({**_GOOD_CONFIG, "resource_group": "a.b-c(d)"})


def test_next_link_must_stay_on_allowlisted_https_host():
    ok = sentinel._next_page_path(
        "https://management.azure.com/subscriptions/x/rules?api-version=1&$skipToken=t"
    )
    assert ok == "/subscriptions/x/rules?api-version=1&$skipToken=t"
    for bad in (
        "https://evil.example.com/rules",
        "http://management.azure.com/rules",  # not https
        "https://management.azure.com.evil.example.com/rules",
    ):
        with pytest.raises(EgressError, match="allowlist"):
            sentinel._next_page_path(bad)


def _fake_sentinel_fetch(monkeypatch, pages, token_status=200, dc_pages=None):
    """Phase A7: dataConnectors calls are routed separately from alertRules
    pages so existing callers don't need to account for the extra
    auto-import read — default is an empty connector list (no derived log
    sources), unless a test opts in with dc_pages=[...]."""
    calls = []
    dc_pages = list(dc_pages) if dc_pages is not None else None

    def fake(host, path, *, allowed_hosts, method="GET", headers=None, body=None):
        calls.append({"host": host, "path": path, "method": method})
        if host == "login.microsoftonline.com":
            if token_status != 200:
                return token_status, {}
            assert b"client_credentials" in body  # secret goes in the body, once
            return 200, {"access_token": "tok-123"}
        if "dataConnectors" in path:
            return dc_pages.pop(0) if dc_pages else (200, {"value": []})
        return pages.pop(0)

    monkeypatch.setattr(sentinel, "fetch_json", fake)
    return calls


def test_pull_normalizes_rules_to_template_csv(monkeypatch):
    calls = _fake_sentinel_fetch(monkeypatch, [(200, {"value": _RULES})])
    result = sentinel.pull(sentinel.validate_config(_GOOD_CONFIG), "s3cr3t")
    assert result["rule_count"] == 3
    assert any("no query text" in w for w in result["warnings"])
    assert calls[1]["host"] == "management.azure.com"
    assert "s3cr3t" not in result["csv_bytes"].decode("utf-8")

    # the CSV must round-trip through the real ingest parser
    parsed = ingest.parse_use_case_file(result["csv_bytes"], "csv")
    assert parsed["row_count"] == 3
    for field in ("name", "description", "logic", "tags", "enabled", "log_source"):
        assert field in parsed["columns"], parsed["columns"]
    rows = {r["name"]: r for r in parsed["rows"]}
    assert rows["Encoded PowerShell"]["tags"] == ["T1059", "T1059.001"]
    assert rows["Encoded PowerShell"]["enabled"] is True
    assert rows["RDP brute force"]["enabled"] is False
    assert "Sentinel" in rows["Encoded PowerShell"]["log_source"]
    assert rows["Advanced multistage attack"]["logic"] in (None, "")


def test_pull_maps_statuses_to_actionable_errors(monkeypatch):
    _fake_sentinel_fetch(monkeypatch, [], token_status=401)
    with pytest.raises(ConnectorError, match="sign-in failed"):
        sentinel.pull(sentinel.validate_config(_GOOD_CONFIG), "bad")

    _fake_sentinel_fetch(monkeypatch, [(403, {})])
    with pytest.raises(ConnectorError, match="Sentinel Reader"):
        sentinel.pull(sentinel.validate_config(_GOOD_CONFIG), "s")

    _fake_sentinel_fetch(monkeypatch, [(404, {})])
    with pytest.raises(ConnectorError, match="workspace not found"):
        sentinel.pull(sentinel.validate_config(_GOOD_CONFIG), "s")

    _fake_sentinel_fetch(monkeypatch, [(200, {"value": []})])
    with pytest.raises(ConnectorError, match="no analytics rules"):
        sentinel.pull(sentinel.validate_config(_GOOD_CONFIG), "s")


def test_pull_follows_next_link_within_allowlist(monkeypatch):
    calls = _fake_sentinel_fetch(
        monkeypatch,
        [
            (200, {"value": [_RULES[0]], "nextLink": "https://management.azure.com/p2?x=1"}),
            (200, {"value": [_RULES[1]]}),
        ],
    )
    result = sentinel.pull(sentinel.validate_config(_GOOD_CONFIG), "s")
    assert result["rule_count"] == 2
    assert calls[2]["path"] == "/p2?x=1"


def test_unknown_platform_rejected():
    with pytest.raises(ConnectorConfigError, match="Unknown SIEM platform"):
        connectors_base.pull_rules("splunk", {}, "s")


# ---------------------------------------------------------------------------
# Phase A7 — data-connector auto-import (mapping goldens, degrade, secrets)
# ---------------------------------------------------------------------------

_CONNECTORS = [
    {"name": "aad", "kind": "AzureActiveDirectory"},
    {"name": "mdatp", "kind": "MicrosoftDefenderAdvancedThreatProtection"},
    {"name": "o365", "kind": "Office365"},
    {"name": "dup-aad", "kind": "AzureActiveDirectoryIdentityProtection"},  # maps to same source
    {"name": "weird", "kind": "SomeFutureConnectorKindNobodyHasSeen"},
]


def test_data_connector_mapping_golden(monkeypatch):
    calls = _fake_sentinel_fetch(
        monkeypatch, [(200, {"value": _RULES})],
        dc_pages=[(200, {"value": _CONNECTORS})],
    )
    result = sentinel.pull(sentinel.validate_config(_GOOD_CONFIG), "s")
    assert result["derived_log_sources"] == ["Azure AD", "Microsoft Defender", "Office 365"]
    assert result["unmapped_connectors"] == ["SomeFutureConnectorKindNobodyHasSeen"]
    assert any(c["path"].endswith(f"dataConnectors?api-version={sentinel.API_VERSION}") for c in calls)


def test_data_connector_pull_degrades_without_failing_the_whole_pull(monkeypatch):
    # dataConnectors 500 -> the alertRules pull still succeeds; a warning
    # is added, never an exception (contract point 4: failure isolation).
    calls = _fake_sentinel_fetch(
        monkeypatch, [(200, {"value": _RULES})], dc_pages=[(500, {})],
    )
    result = sentinel.pull(sentinel.validate_config(_GOOD_CONFIG), "s")
    assert result["rule_count"] == 3
    assert result["derived_log_sources"] == []
    assert any("could not auto-import" in w for w in result["warnings"])
    assert len(calls) == 3  # token + alertRules + the failed dataConnectors call


def test_data_connector_pull_network_error_also_degrades(monkeypatch):
    def raising_fetch(host, path, *, allowed_hosts, method="GET", headers=None, body=None):
        if host == "login.microsoftonline.com":
            return 200, {"access_token": "tok"}
        if "dataConnectors" in path:
            raise EgressError("simulated network failure")
        return 200, {"value": _RULES}

    monkeypatch.setattr(sentinel, "fetch_json", raising_fetch)
    result = sentinel.pull(sentinel.validate_config(_GOOD_CONFIG), "s")
    assert result["rule_count"] == 3
    assert result["derived_log_sources"] == []
    assert any("could not auto-import" in w for w in result["warnings"])


def test_data_connector_response_never_carries_the_secret(monkeypatch):
    calls = _fake_sentinel_fetch(
        monkeypatch, [(200, {"value": _RULES})], dc_pages=[(200, {"value": _CONNECTORS})],
    )
    sentinel.pull(sentinel.validate_config(_GOOD_CONFIG), "s3cr3t-value")
    assert not any("s3cr3t-value" in str(c) for c in calls)


def test_data_connector_malformed_entries_degrade_not_crash(monkeypatch):
    # Adversarial finding (2026-08-03 A7 self-review): a non-dict entry in
    # the "value" array must not raise an unhandled exception -- that
    # would defeat the "inventory pull failure never fails the assessment"
    # contract. Mix of a string, None, and a valid dict.
    malformed = ["not-a-dict", None, 42, {"kind": "Office365"}]
    _fake_sentinel_fetch(
        monkeypatch, [(200, {"value": _RULES})], dc_pages=[(200, {"value": malformed})],
    )
    result = sentinel.pull(sentinel.validate_config(_GOOD_CONFIG), "s")
    assert result["rule_count"] == 3          # alertRules pull unaffected
    assert result["derived_log_sources"] == ["Office 365"]  # the one valid entry still mapped


def test_data_connector_giant_kind_is_truncated(monkeypatch):
    # Independent adversarial review finding (2026-08-03): an uncapped
    # attacker-controlled `kind` flows into stored assumptions and can
    # exceed Excel's 32,767-char cell limit, permanently breaking XLSX
    # export for the assessment. Must be truncated like every other
    # attacker string in the module.
    giant = "K" * 50_000
    _fake_sentinel_fetch(
        monkeypatch,
        [(200, {"value": _RULES})],
        dc_pages=[(200, {"value": [{"kind": giant}, {"kind": "Office365"}]})],
    )
    result = sentinel.pull(sentinel.validate_config(_GOOD_CONFIG), "s")
    assert result["derived_log_sources"] == ["Office 365"]
    assert all(len(k) <= 200 for k in result["unmapped_connectors"])


@pytest.mark.asyncio
async def test_from_siem_auto_imports_log_sources_end_to_end(client, db_session, monkeypatch):
    _fake_sentinel_fetch(
        monkeypatch, [(200, {"value": _RULES})], dc_pages=[(200, {"value": _CONNECTORS})],
    )
    _, _, headers = await _make_user(db_session)
    res = await client.post(
        "/api/v1/mitre/assessments/from-siem", headers=headers, json=_body()
    )
    assert res.status_code == 201, res.text
    preview = res.json()
    assert preview["environment_provided"] is True
    assert preview["sheets_found"]["log_sources"] == (
        "Microsoft Sentinel data connectors (auto-imported)"
    )
    assert any(
        "auto-imported from Sentinel" in a and "3 data" in a
        for a in preview["assumptions"]
    )
    assert any(
        "SomeFutureConnectorKindNobodyHasSeen" in a for a in preview["assumptions"]
    )

    got = (
        await client.get(
            f"/api/v1/mitre/assessments/{preview['assessment_id']}", headers=headers
        )
    ).json()
    env_lists = got["params"]["environment_lists"]
    assert env_lists["log_sources"] == ["Azure AD", "Microsoft Defender", "Office 365"]
    assert env_lists["sheets_found"]["log_sources"] == (
        "Microsoft Sentinel data connectors (auto-imported)"
    )
    # inventory_provided (Assets) stays False -- no platforms were derived,
    # so the coverage-is-a-lower-bound assumption stays honest.
    assert got["params"]["environment"]["inventory_provided"] is False


@pytest.mark.asyncio
async def test_from_siem_empty_data_connectors_is_a_noop(client, db_session, monkeypatch):
    _fake_sentinel_fetch(
        monkeypatch, [(200, {"value": _RULES})], dc_pages=[(200, {"value": []})],
    )
    _, _, headers = await _make_user(db_session)
    res = await client.post(
        "/api/v1/mitre/assessments/from-siem", headers=headers, json=_body()
    )
    assert res.status_code == 201, res.text
    preview = res.json()
    assert preview["environment_provided"] is False
    assert preview["sheets_found"] == {}
    assert not any("auto-imported from Sentinel" in a for a in preview["assumptions"])
    got = (
        await client.get(
            f"/api/v1/mitre/assessments/{preview['assessment_id']}", headers=headers
        )
    ).json()
    assert got["params"]["environment_lists"]["log_sources"] == []
    assert got["params"]["environment_lists"]["sheets_found"] == {}


# ---------------------------------------------------------------------------
# endpoint E2E — real Postgres, faked Sentinel API
# ---------------------------------------------------------------------------


@pytest.fixture
async def client():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as c:
        yield c


async def _make_user(db_session, *, role="admin"):
    org = Organization(org_id=uuid.uuid4(), name=f"org-{uuid.uuid4()}")
    user = User(user_id=uuid.uuid4(), org_id=org.org_id, email=f"{uuid.uuid4()}@x.com")
    db_session.add_all([org, user])
    await db_session.commit()
    token, _ = create_access_token(
        user_id=user.user_id, email=user.email, org_id=org.org_id, role=role
    )
    return org, user, {"Authorization": f"Bearer {token}"}


_SECRET = "super-secret-value-42"


def _body(**overrides):
    return {
        "platform": "sentinel",
        "config": dict(_GOOD_CONFIG),
        "secret": _SECRET,
        **overrides,
    }


@pytest.mark.asyncio
async def test_from_siem_creates_assessment_with_provenance(client, db_session, monkeypatch):
    _fake_sentinel_fetch(monkeypatch, [(200, {"value": _RULES})])
    _, _, headers = await _make_user(db_session)

    res = await client.post(
        "/api/v1/mitre/assessments/from-siem", headers=headers, json=_body()
    )
    assert res.status_code == 201, res.text
    preview = res.json()
    assert preview["row_count"] == 3
    assert preview["tagged"] == 2  # two rules carry technique IDs
    assert preview["siem"] == {"platform": "sentinel", "rule_count": 3}
    assert preview["name"].startswith("Sentinel pull ")

    got = (
        await client.get(
            f"/api/v1/mitre/assessments/{preview['assessment_id']}", headers=headers
        )
    ).json()
    siem = got["params"]["siem"]
    assert siem["trigger"] == "manual" and siem["rule_count"] == 3
    assert siem["workspace_ref"]["workspace"] == "prod-sentinel"
    # the secret must not be persisted ANYWHERE on the assessment
    assert _SECRET not in json.dumps(got)


@pytest.mark.asyncio
async def test_from_siem_stamps_customer_from_workspace(client, db_session, monkeypatch):
    """Phase A12: a token-at-trigger pull (no saved connection) stamps
    params.customer from the workspace name so trend comparisons scope
    correctly even without a saved connection."""
    _fake_sentinel_fetch(monkeypatch, [(200, {"value": _RULES})])
    _, _, headers = await _make_user(db_session)

    res = await client.post(
        "/api/v1/mitre/assessments/from-siem", headers=headers, json=_body()
    )
    assert res.status_code == 201, res.text
    got = (
        await client.get(
            f"/api/v1/mitre/assessments/{res.json()['assessment_id']}", headers=headers
        )
    ).json()
    assert got["params"]["customer"] == "prod-sentinel"


@pytest.mark.asyncio
async def test_from_siem_validation_and_authz(client, db_session, monkeypatch):
    _, _, headers = await _make_user(db_session)
    _, _, viewer = await _make_user(db_session, role="viewer")

    forbidden = await client.post(
        "/api/v1/mitre/assessments/from-siem", headers=viewer, json=_body()
    )
    assert forbidden.status_code == 403

    no_secret = await client.post(
        "/api/v1/mitre/assessments/from-siem", headers=headers, json=_body(secret="  ")
    )
    assert no_secret.status_code == 422
    assert "never stored" in no_secret.json()["detail"]

    bad_config = await client.post(
        "/api/v1/mitre/assessments/from-siem",
        headers=headers,
        json=_body(config={**_GOOD_CONFIG, "tenant_id": "nope"}),
    )
    assert bad_config.status_code == 422
    assert "tenant_id" in bad_config.json()["detail"]

    _fake_sentinel_fetch(monkeypatch, [(403, {})])
    denied = await client.post(
        "/api/v1/mitre/assessments/from-siem", headers=headers, json=_body()
    )
    assert denied.status_code == 502
    assert "Sentinel Reader" in denied.json()["detail"]
