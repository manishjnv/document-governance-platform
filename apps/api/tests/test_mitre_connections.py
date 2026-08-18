"""Phase 13b credential-vault tests: crypto unit tests, connections CRUD
(secret write-only), dry-run test endpoint, from-connection assessment
creation, and the log-scrubbing guarantee. All Sentinel traffic is faked
at fetch_json (no network); Postgres is real edgp_test."""

import base64
import json
import logging
import uuid

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import select

from app.auth import create_access_token
from app.mitre.connectors import vault
from app.models.mitre_connection import MitreConnection
from app.models.organization import Organization
from app.models.user import User
from main import app

from tests.test_mitre_siem import _GOOD_CONFIG, _RULES, _fake_sentinel_fetch

_KEY_B64 = base64.b64encode(b"k" * 32).decode("ascii")
_SECRET = "vault-secret-value-97"


@pytest.fixture(autouse=True)
def _vault_key(monkeypatch):
    monkeypatch.setenv("SIEM_CRED_KEY", _KEY_B64)


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


# ---------------------------------------------------------------------------
# vault.py — crypto unit tests
# ---------------------------------------------------------------------------


def test_round_trip_and_aad_binding():
    ciphertext, version = vault.encrypt_secret(_SECRET, aad="conn-1")
    assert version == vault.KEY_VERSION
    assert _SECRET.encode() not in ciphertext  # actually encrypted
    assert vault.decrypt_secret(ciphertext, version, aad="conn-1") == _SECRET
    # a ciphertext transplanted onto another connection fails authentication
    with pytest.raises(vault.VaultError, match="could not be decrypted"):
        vault.decrypt_secret(ciphertext, version, aad="conn-2")


def test_unknown_key_version_and_corrupt_ciphertext():
    ciphertext, _ = vault.encrypt_secret(_SECRET, aad="c")
    with pytest.raises(vault.VaultError, match="old key version"):
        vault.decrypt_secret(ciphertext, 99, aad="c")
    with pytest.raises(vault.VaultError, match="corrupt"):
        vault.decrypt_secret(b"short", vault.KEY_VERSION, aad="c")
    with pytest.raises(vault.VaultError, match="could not be decrypted"):
        vault.decrypt_secret(ciphertext[:-1] + b"X", vault.KEY_VERSION, aad="c")


def test_missing_or_malformed_key(monkeypatch):
    monkeypatch.delenv("SIEM_CRED_KEY")
    assert vault.is_configured() is False
    with pytest.raises(vault.VaultError, match="not configured"):
        vault.encrypt_secret(_SECRET, aad="c")
    monkeypatch.setenv("SIEM_CRED_KEY", "not-base64!!")
    with pytest.raises(vault.VaultError, match="32-byte base64"):
        vault.encrypt_secret(_SECRET, aad="c")
    monkeypatch.setenv("SIEM_CRED_KEY", base64.b64encode(b"short").decode())
    with pytest.raises(vault.VaultError, match="32-byte base64"):
        vault.encrypt_secret(_SECRET, aad="c")


# ---------------------------------------------------------------------------
# connections CRUD — admin-only, org-scoped, secret write-only
# ---------------------------------------------------------------------------


def _create_body(**overrides):
    return {
        "platform": "sentinel",
        "config": dict(_GOOD_CONFIG),
        "secret": _SECRET,
        "name": "Prod Sentinel",
        **overrides,
    }


async def _create_connection(client, headers) -> dict:
    res = await client.post("/api/v1/mitre/connections", headers=headers, json=_create_body())
    assert res.status_code == 201, res.text
    return res.json()


@pytest.mark.asyncio
async def test_crud_secret_write_only(client, db_session):
    _, _, headers = await _make_user(db_session)
    created = await _create_connection(client, headers)
    assert created["name"] == "Prod Sentinel"
    assert created["secret_set"] is True
    assert _SECRET not in json.dumps(created)

    listed = await client.get("/api/v1/mitre/connections", headers=headers)
    assert listed.status_code == 200
    assert len(listed.json()) == 1
    assert _SECRET not in json.dumps(listed.json())

    # stored ciphertext does not contain the plaintext
    row = await db_session.get(MitreConnection, uuid.UUID(created["connection_id"]))
    assert _SECRET.encode() not in bytes(row.secret_ciphertext)
    assert row.key_version == vault.KEY_VERSION

    cid = created["connection_id"]
    patched = await client.patch(
        f"/api/v1/mitre/connections/{cid}",
        headers=headers,
        json={"name": "Renamed", "secret": "replacement-secret-11"},
    )
    assert patched.status_code == 200, patched.text
    assert patched.json()["name"] == "Renamed"
    assert "replacement-secret-11" not in json.dumps(patched.json())
    await db_session.refresh(row)
    assert vault.decrypt_secret(
        bytes(row.secret_ciphertext), row.key_version, aad=cid
    ) == "replacement-secret-11"

    deleted = await client.delete(f"/api/v1/mitre/connections/{cid}", headers=headers)
    assert deleted.status_code == 204
    gone = await client.patch(
        f"/api/v1/mitre/connections/{cid}", headers=headers, json={"name": "x"}
    )
    assert gone.status_code == 404


@pytest.mark.asyncio
async def test_crud_rbac_org_isolation_and_validation(client, db_session):
    _, _, admin_a = await _make_user(db_session)
    _, _, admin_b = await _make_user(db_session)
    _, _, reviewer = await _make_user(db_session, role="reviewer")

    some_id = uuid.uuid4()
    for headers in (reviewer,):
        assert (
            await client.post("/api/v1/mitre/connections", headers=headers, json=_create_body())
        ).status_code == 403
        assert (
            await client.get("/api/v1/mitre/connections", headers=headers)
        ).status_code == 403
        # every admin-only route, not just POST/GET (review note #1)
        assert (
            await client.patch(f"/api/v1/mitre/connections/{some_id}", headers=headers, json={})
        ).status_code == 403
        assert (
            await client.delete(f"/api/v1/mitre/connections/{some_id}", headers=headers)
        ).status_code == 403
        assert (
            await client.post(f"/api/v1/mitre/connections/{some_id}/test", headers=headers)
        ).status_code == 403

    bad_cfg = await client.post(
        "/api/v1/mitre/connections",
        headers=admin_a,
        json=_create_body(config={**_GOOD_CONFIG, "tenant_id": "nope"}),
    )
    assert bad_cfg.status_code == 422
    no_secret = await client.post(
        "/api/v1/mitre/connections", headers=admin_a, json=_create_body(secret=" ")
    )
    assert no_secret.status_code == 422
    # length cap holds on the CRUD path too (review note #2)
    huge = await client.post(
        "/api/v1/mitre/connections", headers=admin_a, json=_create_body(secret="x" * 5000)
    )
    assert huge.status_code == 422
    assert "implausibly long" in huge.json()["detail"]

    created = await _create_connection(client, admin_a)
    cid = created["connection_id"]
    cross = await client.patch(
        f"/api/v1/mitre/connections/{cid}", headers=admin_b, json={"name": "steal"}
    )
    assert cross.status_code == 404
    assert (
        await client.post(f"/api/v1/mitre/connections/{cid}/test", headers=admin_b)
    ).status_code == 404


@pytest.mark.asyncio
async def test_create_splunk_connection_default_name(client, db_session):
    """Regression: the default-name fallback used config['workspace'], which
    only Sentinel configs have — a nameless Splunk create 500'd."""
    _, _, headers = await _make_user(db_session)
    res = await client.post(
        "/api/v1/mitre/connections",
        headers=headers,
        json={
            "platform": "splunk",
            "config": {"host": "acme.splunkcloud.com"},
            "secret": _SECRET,
        },
    )
    assert res.status_code == 201, res.text
    assert res.json()["name"] == "Splunk · acme.splunkcloud.com"


@pytest.mark.asyncio
async def test_create_connection_with_schedule(client, db_session):
    """Schedule trio may ride the create body (same rules as PATCH)."""
    _, _, headers = await _make_user(db_session)
    res = await client.post(
        "/api/v1/mitre/connections",
        headers=headers,
        json=_create_body(schedule_cadence="daily", schedule_hour_utc=6),
    )
    assert res.status_code == 201, res.text
    body = res.json()
    assert body["schedule_cadence"] == "daily"
    assert body["schedule_hour_utc"] == 6
    assert body["schedule_weekday"] is None

    bad = await client.post(
        "/api/v1/mitre/connections",
        headers=headers,
        json=_create_body(schedule_cadence="weekly", schedule_hour_utc=6),
    )
    assert bad.status_code == 422
    assert "schedule_weekday" in bad.json()["detail"]


@pytest.mark.asyncio
async def test_vault_unconfigured_maps_to_503(client, db_session, monkeypatch):
    _, _, headers = await _make_user(db_session)
    monkeypatch.delenv("SIEM_CRED_KEY")
    res = await client.post(
        "/api/v1/mitre/connections", headers=headers, json=_create_body()
    )
    assert res.status_code == 503
    assert "not configured" in res.json()["detail"]


# ---------------------------------------------------------------------------
# dry-run test endpoint + from-connection assessment
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_connection_test_dry_run(client, db_session, monkeypatch):
    _fake_sentinel_fetch(monkeypatch, [(200, {"value": _RULES})])
    _, _, headers = await _make_user(db_session)
    cid = (await _create_connection(client, headers))["connection_id"]

    res = await client.post(f"/api/v1/mitre/connections/{cid}/test", headers=headers)
    assert res.status_code == 200, res.text
    body = res.json()
    assert body["ok"] is True and body["rule_count"] == 3
    assert _SECRET not in json.dumps(body)


@pytest.mark.asyncio
async def test_from_connection_creates_assessment_with_provenance(
    client, db_session, monkeypatch
):
    _fake_sentinel_fetch(monkeypatch, [(200, {"value": _RULES})])
    _, _, admin = await _make_user(db_session)
    created = await _create_connection(client, admin)
    cid = created["connection_id"]

    res = await client.post(
        f"/api/v1/mitre/assessments/from-connection/{cid}",
        headers=admin,
        json={"name": "Nightly-style pull"},
    )
    assert res.status_code == 201, res.text
    preview = res.json()
    assert preview["row_count"] == 3

    got = (
        await client.get(
            f"/api/v1/mitre/assessments/{preview['assessment_id']}", headers=admin
        )
    ).json()
    siem = got["params"]["siem"]
    assert siem["connection_id"] == cid
    assert siem["connection_name"] == "Prod Sentinel"
    assert siem["trigger"] == "manual"
    assert _SECRET not in json.dumps(got)

    # the list endpoint surfaces connection_id (per-connection trend grouping)
    listed = (await client.get("/api/v1/mitre/assessments", headers=admin)).json()
    row = next(x for x in listed if x["assessment_id"] == preview["assessment_id"])
    assert row["siem"]["connection_id"] == cid


@pytest.mark.asyncio
async def test_from_connection_stamps_and_truncates_customer(
    client, db_session, monkeypatch
):
    """Phase A12: a saved-connection pull stamps params.customer from the
    connection's own name (so scheduled re-runs group naturally), capped
    to 200 chars like every other attacker/user string in this module."""
    _fake_sentinel_fetch(monkeypatch, [(200, {"value": _RULES})])
    _, _, admin = await _make_user(db_session)
    giant_name = "Acme " * 50  # 250 chars — under the connection's 255 cap,
    # over the customer field's 200-char cap
    created = (
        await client.post(
            "/api/v1/mitre/connections", headers=admin, json=_create_body(name=giant_name)
        )
    ).json()
    cid = created["connection_id"]

    res = await client.post(
        f"/api/v1/mitre/assessments/from-connection/{cid}", headers=admin, json={}
    )
    assert res.status_code == 201, res.text
    got = (
        await client.get(
            f"/api/v1/mitre/assessments/{res.json()['assessment_id']}", headers=admin
        )
    ).json()
    assert got["params"]["customer"] == " ".join(giant_name.split())[:200]


@pytest.mark.asyncio
async def test_from_connection_rbac_and_cross_org(client, db_session, monkeypatch):
    _fake_sentinel_fetch(monkeypatch, [(200, {"value": _RULES})])
    org_a, _, admin_a = await _make_user(db_session)
    _, _, admin_b = await _make_user(db_session)
    _, _, viewer = await _make_user(db_session, role="viewer")
    # reviewer in ORG A may pull from A's saved connection (plan §3: 13b row)
    reviewer_user = User(user_id=uuid.uuid4(), org_id=org_a.org_id, email=f"{uuid.uuid4()}@x.com")
    db_session.add(reviewer_user)
    await db_session.commit()
    reviewer_token, _ = create_access_token(
        user_id=reviewer_user.user_id, email=reviewer_user.email,
        org_id=org_a.org_id, role="reviewer",
    )
    reviewer_a = {"Authorization": f"Bearer {reviewer_token}"}

    cid = (await _create_connection(client, admin_a))["connection_id"]
    url = f"/api/v1/mitre/assessments/from-connection/{cid}"

    assert (await client.post(url, headers=admin_b, json={})).status_code == 404
    assert (await client.post(url, headers=viewer, json={})).status_code == 403
    ok = await client.post(url, headers=reviewer_a, json={})
    assert ok.status_code == 201, ok.text


# ---------------------------------------------------------------------------
# the log-scrubbing guarantee
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_secret_never_appears_in_logs(client, db_session, monkeypatch, caplog):
    """End-to-end: create + test + from-connection with DEBUG logging
    captured across the app — the plaintext secret must not appear in any
    log record (plan §2.1 'secrets NEVER logged')."""
    _fake_sentinel_fetch(monkeypatch, [(200, {"value": _RULES}), (200, {"value": _RULES})])
    _, _, headers = await _make_user(db_session)

    with caplog.at_level(logging.DEBUG):
        created = await _create_connection(client, headers)
        cid = created["connection_id"]
        await client.post(f"/api/v1/mitre/connections/{cid}/test", headers=headers)
        await client.post(
            f"/api/v1/mitre/assessments/from-connection/{cid}", headers=headers, json={}
        )

    for record in caplog.records:
        assert _SECRET not in record.getMessage()
