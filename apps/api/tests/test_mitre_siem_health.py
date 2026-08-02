"""Phase 13d tests: provenance surfacing (list brief + report footer),
connection health/streak math, and the scheduled-failure notification
(fires at exactly 2, once per streak, resets on success, never carries
secrets or rule content). Sentinel traffic faked; narrative stubbed."""

import base64
import uuid
from datetime import datetime, timezone

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import async_sessionmaker

from app.auth import create_access_token
from app.mitre import agents
from app.mitre import tasks as mitre_tasks
from app.mitre.report import build_html_report
from app.mitre.tasks import _run_scheduled_pull_async, connection_health
from app.models.mitre_connection import MitreConnection
from app.models.organization import Organization
from app.models.user import User
from main import app

from tests.test_mitre_siem import _GOOD_CONFIG, _RULES, _fake_sentinel_fetch

_KEY_B64 = base64.b64encode(b"k" * 32).decode("ascii")
_SECRET = "health-secret-5"


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
    # role set on the DB row too — the notification recipient query reads
    # users.role, not the JWT
    user = User(
        user_id=uuid.uuid4(), org_id=org.org_id, email=f"{uuid.uuid4()}@x.com", role=role
    )
    db_session.add_all([org, user])
    await db_session.commit()
    token, _ = create_access_token(
        user_id=user.user_id, email=user.email, org_id=org.org_id, role=role
    )
    return org, user, {"Authorization": f"Bearer {token}"}


async def _make_connection(client, headers) -> str:
    res = await client.post(
        "/api/v1/mitre/connections",
        headers=headers,
        json={
            "platform": "sentinel",
            "config": dict(_GOOD_CONFIG),
            "secret": _SECRET,
            "name": "Health Sentinel",
        },
    )
    assert res.status_code == 201, res.text
    return res.json()["connection_id"]


def _factory(db_session):
    return async_sessionmaker(db_session.bind, expire_on_commit=False)


@pytest.fixture
def _emails(monkeypatch):
    sent = []

    async def fake_send(to, subject, body, html_body=None):
        sent.append({"to": to, "subject": subject, "body": body})
        return True

    # tasks.py imports send_email inside the function — patch the source
    monkeypatch.setattr("app.email.send_email", fake_send)
    return sent


@pytest.fixture
def _template_narrative(monkeypatch):
    async def fake(computed, *, agent=None):
        return {
            "narrative": agents.build_template_narrative(computed),
            "generated_by": "template",
            "model_used": None,
        }

    monkeypatch.setattr(agents, "generate_narrative", fake)


@pytest.mark.asyncio
async def test_list_carries_siem_brief_and_report_footer(client, db_session, monkeypatch):
    _fake_sentinel_fetch(monkeypatch, [(200, {"value": _RULES})])
    _, _, headers = await _make_user(db_session)
    res = await client.post(
        "/api/v1/mitre/assessments/from-siem",
        headers=headers,
        json={"platform": "sentinel", "config": dict(_GOOD_CONFIG), "secret": _SECRET},
    )
    aid = res.json()["assessment_id"]

    listed = (await client.get("/api/v1/mitre/assessments", headers=headers)).json()
    row = next(r for r in listed if r["assessment_id"] == aid)
    assert row["siem"] == {"platform": "sentinel", "trigger": "manual"}

    # report footer provenance (hand-complete so the builder accepts it)
    from app.models.mitre_assessment import MitreAssessment

    assessment = await db_session.get(MitreAssessment, uuid.UUID(aid))
    assessment.status = "completed"
    assessment.completed_at = datetime.now(timezone.utc)
    assessment.summary = {"overall": {}, "domains": {}, "narrative": {}}
    assessment.technique_results = []
    await db_session.commit()
    html = build_html_report(assessment, [])
    assert "Microsoft Sentinel pull" in html
    assert "prod-sentinel" in html  # workspace ref, non-secret
    assert _SECRET not in html


@pytest.mark.asyncio
async def test_notification_fires_at_exactly_two_and_resets(
    client, db_session, monkeypatch, _emails, _template_narrative
):
    org, user, headers = await _make_user(db_session)
    cid = await _make_connection(client, headers)
    factory = _factory(db_session)

    # failure #1 — no email
    _fake_sentinel_fetch(monkeypatch, [(403, {})])
    assert (await _run_scheduled_pull_async(cid, factory))["status"] == "failed"
    assert _emails == []

    # failure #2 — exactly one email to the org admin
    _fake_sentinel_fetch(monkeypatch, [(403, {})])
    assert (await _run_scheduled_pull_async(cid, factory))["status"] == "failed"
    assert len(_emails) == 1
    assert _emails[0]["to"] == user.email
    assert "Health Sentinel" in _emails[0]["subject"]
    body = _emails[0]["body"]
    assert "Sentinel Reader" in body          # the actionable error
    assert _SECRET not in body                # never the secret
    assert "SecurityEvent" not in body        # never rule content

    # failure #3 — same streak, no second email
    _fake_sentinel_fetch(monkeypatch, [(403, {})])
    assert (await _run_scheduled_pull_async(cid, factory))["status"] == "failed"
    assert len(_emails) == 1

    # success resets the streak…
    _fake_sentinel_fetch(monkeypatch, [(200, {"value": _RULES})])
    assert (await _run_scheduled_pull_async(cid, factory))["status"] == "completed"

    # …so the next single failure does not notify
    _fake_sentinel_fetch(monkeypatch, [(403, {})])
    assert (await _run_scheduled_pull_async(cid, factory))["status"] == "failed"
    assert len(_emails) == 1

    # health reflects the current streak of 1
    row = await db_session.get(MitreConnection, uuid.UUID(cid))
    health = await connection_health(db_session, row)
    assert health["scheduled_failure_streak"] == 1
    assert "Sentinel Reader" in health["last_error"]
    assert health["last_status"] == "failed"


@pytest.mark.asyncio
async def test_connections_endpoint_includes_health(client, db_session, monkeypatch, _emails):
    _, _, headers = await _make_user(db_session)
    cid = await _make_connection(client, headers)
    _fake_sentinel_fetch(monkeypatch, [(404, {})])
    await _run_scheduled_pull_async(cid, _factory(db_session))

    listed = (await client.get("/api/v1/mitre/connections", headers=headers)).json()
    row = next(c for c in listed if c["connection_id"] == cid)
    assert row["health"]["scheduled_failure_streak"] == 1
    assert "workspace not found" in row["health"]["last_error"]
    assert row["health"]["last_status"] == "failed"
    assert _SECRET not in str(listed)


def test_notify_threshold_is_two():
    # pin the product decision (plan §2.6) so a drive-by edit gets caught
    assert mitre_tasks._NOTIFY_AT_STREAK == 2


@pytest.mark.asyncio
async def test_stale_flip_reaching_threshold_still_notifies(
    client, db_session, monkeypatch, _emails
):
    """Adversarial finding: a sweep stale-flip that lands the streak on
    exactly 2 must email — otherwise a deploy-restart mid-run silently
    consumes the threshold and the streak never notifies."""
    from datetime import timedelta

    from app.mitre.tasks import _sweep_async
    from app.models.mitre_assessment import MitreAssessment

    org, user, headers = await _make_user(db_session)
    cid = await _make_connection(client, headers)
    hour_due = (datetime.now(timezone.utc).hour - 1) % 24
    await client.patch(
        f"/api/v1/mitre/connections/{cid}",
        headers=headers,
        json={"schedule_cadence": "daily", "schedule_hour_utc": hour_due},
    )

    # failure #1 — normal path, no email
    _fake_sentinel_fetch(monkeypatch, [(403, {})])
    await _run_scheduled_pull_async(cid, _factory(db_session))
    assert _emails == []

    # failure #2 arrives as a STALE running row flipped by the sweep
    db_session.add(
        MitreAssessment(
            assessment_id=uuid.uuid4(),
            org_id=org.org_id,
            name="crashed run",
            status="running",
            attack_version="19.1",
            params={"siem": {"connection_id": cid, "trigger": "scheduled"}},
            created_by=user.user_id,
            updated_at=datetime.now(timezone.utc) - timedelta(minutes=31),
        )
    )
    await db_session.commit()

    await _sweep_async(_factory(db_session), enqueue=lambda _cid: None)
    assert len(_emails) == 1  # the flip completed the streak — notified
    assert "Health Sentinel" in _emails[0]["subject"]


@pytest.mark.asyncio
async def test_connection_name_crlf_stripped(client, db_session):
    # email-Subject header-injection hardening (review minor note)
    _, _, headers = await _make_user(db_session)
    res = await client.post(
        "/api/v1/mitre/connections",
        headers=headers,
        json={
            "platform": "sentinel",
            "config": dict(_GOOD_CONFIG),
            "secret": _SECRET,
            "name": "evil\r\nBcc: victim@example.com",
        },
    )
    assert res.status_code == 201
    assert res.json()["name"] == "evil Bcc: victim@example.com"
