"""Phase 13c scheduler tests: due-instant math (pure), schedule PATCH
validation, the beat sweep (advance/enqueue/dedup semantics), and the
worker pull-and-run task called in-process with an injected session
factory (the celery wrappers' fresh-engine pattern is exercised by calling
the async internals the same way they do). Sentinel traffic faked at
fetch_json; the narrative agent is stubbed to its template path."""

import base64
import uuid
from datetime import datetime, timedelta, timezone

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import async_sessionmaker

from app.auth import create_access_token
from app.mitre import agents
from app.mitre.tasks import _run_scheduled_pull_async, _sweep_async, most_recent_due
from app.models.mitre_assessment import MitreAssessment
from app.models.mitre_connection import MitreConnection
from app.models.organization import Organization
from app.models.user import User
from main import app

from tests.test_mitre_siem import _GOOD_CONFIG, _RULES, _fake_sentinel_fetch

_KEY_B64 = base64.b64encode(b"k" * 32).decode("ascii")
_SECRET = "sched-secret-3"


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


async def _make_connection(client, headers, **schedule) -> str:
    res = await client.post(
        "/api/v1/mitre/connections",
        headers=headers,
        json={
            "platform": "sentinel",
            "config": dict(_GOOD_CONFIG),
            "secret": _SECRET,
            "name": "Sched Sentinel",
        },
    )
    assert res.status_code == 201, res.text
    cid = res.json()["connection_id"]
    if schedule:
        patched = await client.patch(
            f"/api/v1/mitre/connections/{cid}", headers=headers, json=schedule
        )
        assert patched.status_code == 200, patched.text
    return cid


# ---------------------------------------------------------------------------
# most_recent_due — pure goldens
# ---------------------------------------------------------------------------


def test_most_recent_due_daily():
    now = datetime(2026, 8, 2, 10, 30, tzinfo=timezone.utc)  # Sunday
    assert most_recent_due(now, "daily", 9, None) == datetime(
        2026, 8, 2, 9, 0, tzinfo=timezone.utc
    )
    # hour not reached yet today -> yesterday's instant
    assert most_recent_due(now, "daily", 14, None) == datetime(
        2026, 8, 1, 14, 0, tzinfo=timezone.utc
    )


def test_most_recent_due_weekly_and_invalid():
    now = datetime(2026, 8, 2, 10, 30, tzinfo=timezone.utc)  # Sunday = weekday 6
    # Monday 09:00 (weekday 0) -> last Monday, 2026-07-27
    assert most_recent_due(now, "weekly", 9, 0) == datetime(
        2026, 7, 27, 9, 0, tzinfo=timezone.utc
    )
    # Sunday 09:00 (today, already passed)
    assert most_recent_due(now, "weekly", 9, 6) == datetime(
        2026, 8, 2, 9, 0, tzinfo=timezone.utc
    )
    # Sunday 14:00 (today, not yet) -> a week ago
    assert most_recent_due(now, "weekly", 14, 6) == datetime(
        2026, 7, 26, 14, 0, tzinfo=timezone.utc
    )
    assert most_recent_due(now, None, 9, 0) is None
    assert most_recent_due(now, "weekly", 9, None) is None
    assert most_recent_due(now, "daily", None, None) is None


# ---------------------------------------------------------------------------
# schedule PATCH validation
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_schedule_patch_validation(client, db_session):
    _, _, headers = await _make_user(db_session)
    cid = await _make_connection(client, headers)
    url = f"/api/v1/mitre/connections/{cid}"

    ok = await client.patch(
        url, headers=headers, json={"schedule_cadence": "daily", "schedule_hour_utc": 3}
    )
    assert ok.status_code == 200
    assert ok.json()["schedule_cadence"] == "daily"

    for payload, needle in [
        ({"schedule_cadence": "hourly"}, "daily"),
        ({"schedule_cadence": "daily", "schedule_hour_utc": 24}, "0-23"),
        ({"schedule_cadence": "weekly", "schedule_hour_utc": 3}, "schedule_weekday"),
        ({"schedule_cadence": "weekly", "schedule_hour_utc": 3, "schedule_weekday": 7}, "0-6"),
    ]:
        res = await client.patch(url, headers=headers, json=payload)
        assert res.status_code == 422, (payload, res.text)
        assert needle in res.json()["detail"]

    cleared = await client.patch(url, headers=headers, json={"schedule_cadence": None})
    assert cleared.status_code == 200
    body = cleared.json()
    assert body["schedule_cadence"] is None
    assert body["schedule_hour_utc"] is None and body["schedule_weekday"] is None


# ---------------------------------------------------------------------------
# the beat sweep — advance/enqueue/dedup
# ---------------------------------------------------------------------------


def _factory(db_session):
    return async_sessionmaker(db_session.bind, expire_on_commit=False)


@pytest.mark.asyncio
async def test_sweep_enqueues_due_and_advances(client, db_session):
    _, _, headers = await _make_user(db_session)
    hour_due = (datetime.now(timezone.utc).hour - 1) % 24
    cid = await _make_connection(
        client, headers, schedule_cadence="daily", schedule_hour_utc=hour_due
    )
    calls = []
    result = await _sweep_async(_factory(db_session), enqueue=calls.append)
    assert calls == [cid]
    assert result["enqueued"] == [cid]

    row = await db_session.get(MitreConnection, uuid.UUID(cid))
    await db_session.refresh(row)
    assert row.last_scheduled_at is not None

    # second sweep in the same slot: nothing due
    calls.clear()
    await _sweep_async(_factory(db_session), enqueue=calls.append)
    assert calls == []


@pytest.mark.asyncio
async def test_sweep_dedups_in_flight_without_advancing(client, db_session):
    org, user, headers = await _make_user(db_session)
    hour_due = (datetime.now(timezone.utc).hour - 1) % 24
    cid = await _make_connection(
        client, headers, schedule_cadence="daily", schedule_hour_utc=hour_due
    )
    db_session.add(
        MitreAssessment(
            assessment_id=uuid.uuid4(),
            org_id=org.org_id,
            name="in flight",
            status="running",
            attack_version="19.1",
            params={"siem": {"connection_id": cid}},
            created_by=user.user_id,
            updated_at=datetime.now(timezone.utc),
        )
    )
    await db_session.commit()

    calls = []
    result = await _sweep_async(_factory(db_session), enqueue=calls.append)
    assert calls == []
    assert result["skipped_running"] == [cid]
    row = await db_session.get(MitreConnection, uuid.UUID(cid))
    await db_session.refresh(row)
    assert row.last_scheduled_at is None  # slot NOT consumed — retries later


def _assessment_for(org, user, cid, *, status="running", age_minutes=0):
    return MitreAssessment(
        assessment_id=uuid.uuid4(),
        org_id=org.org_id,
        name="row",
        status=status,
        error_message="x" if status == "failed" else None,
        attack_version="19.1",
        params={"siem": {"connection_id": cid}},
        created_by=user.user_id,
        updated_at=datetime.now(timezone.utc) - timedelta(minutes=age_minutes),
    )


@pytest.mark.asyncio
async def test_sweep_heals_stale_running_and_proceeds(client, db_session):
    # adversarial finding #1: a crashed worker's 'running' row (>30 min)
    # must not block the schedule forever — the sweep flips it to failed
    # and enqueues in the same pass.
    org, user, headers = await _make_user(db_session)
    hour_due = (datetime.now(timezone.utc).hour - 1) % 24
    cid = await _make_connection(
        client, headers, schedule_cadence="daily", schedule_hour_utc=hour_due
    )
    stale = _assessment_for(org, user, cid, status="running", age_minutes=31)
    db_session.add(stale)
    await db_session.commit()

    calls = []
    result = await _sweep_async(_factory(db_session), enqueue=calls.append)
    assert calls == [cid]
    assert result["enqueued"] == [cid]
    await db_session.refresh(stale)
    assert stale.status == "failed"
    assert "interrupted" in stale.error_message


@pytest.mark.asyncio
async def test_sweep_ignores_pending_previews(client, db_session):
    # adversarial finding #1 (second half): a never-run 'pending' preview
    # hasn't touched the SIEM and must not consume the schedule slot.
    org, user, headers = await _make_user(db_session)
    hour_due = (datetime.now(timezone.utc).hour - 1) % 24
    cid = await _make_connection(
        client, headers, schedule_cadence="daily", schedule_hour_utc=hour_due
    )
    db_session.add(_assessment_for(org, user, cid, status="pending"))
    await db_session.commit()

    calls = []
    result = await _sweep_async(_factory(db_session), enqueue=calls.append)
    assert calls == [cid]
    assert result["skipped_running"] == []


# ---------------------------------------------------------------------------
# the worker pull-and-run task
# ---------------------------------------------------------------------------


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
async def test_scheduled_pull_completes_with_provenance(
    client, db_session, monkeypatch, _template_narrative
):
    _fake_sentinel_fetch(monkeypatch, [(200, {"value": _RULES})])
    _, _, headers = await _make_user(db_session)
    cid = await _make_connection(client, headers)

    result = await _run_scheduled_pull_async(cid, _factory(db_session))
    assert result["status"] == "completed", result

    got = await client.get(
        f"/api/v1/mitre/assessments/{result['assessment_id']}", headers=headers
    )
    body = got.json()
    assert body["status"] == "completed"
    assert body["params"]["siem"]["trigger"] == "scheduled"
    assert body["params"]["siem"]["connection_id"] == cid
    assert body["name"].startswith("Scheduled pull · Sched Sentinel")
    assert body["summary"]["overall"]["covered"] >= 1


@pytest.mark.asyncio
async def test_scheduled_pull_failure_lands_as_failed_assessment(
    client, db_session, monkeypatch
):
    _fake_sentinel_fetch(monkeypatch, [(403, {})])
    _, _, headers = await _make_user(db_session)
    cid = await _make_connection(client, headers)

    result = await _run_scheduled_pull_async(cid, _factory(db_session))
    assert result["status"] == "failed"

    got = await client.get(
        f"/api/v1/mitre/assessments/{result['assessment_id']}", headers=headers
    )
    body = got.json()
    assert body["status"] == "failed"
    assert "Sentinel Reader" in body["error_message"]
    assert body["params"]["siem"]["trigger"] == "scheduled"
    assert _SECRET not in str(body)


@pytest.mark.asyncio
async def test_scheduled_pull_skips_deleted_connection(client, db_session):
    _, _, headers = await _make_user(db_session)
    cid = await _make_connection(client, headers)
    await client.delete(f"/api/v1/mitre/connections/{cid}", headers=headers)

    result = await _run_scheduled_pull_async(cid, _factory(db_session))
    assert result == {"status": "skipped", "reason": "connection deleted"}
