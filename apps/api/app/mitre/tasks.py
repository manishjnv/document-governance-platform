"""Scheduled SIEM re-assessment worker tasks (Phase 13c, plan §2.3/§2.5).

Runs in the scopewise-worker container (Celery worker + in-process beat).
One beat sweep every 15 minutes finds due connections and enqueues one
pull-and-run task per connection. Semantics:

- `last_scheduled_at` advances exactly when a run is ENQUEUED: a failed
  run still advances (no retry storms — plan §2.6); a dedup-skip (an
  assessment for that connection already pending/running) does NOT, so
  the slot retries on later sweeps until the in-flight run finishes.
- A failed scheduled pull lands as a status='failed' assessment row with
  a plain-English error_message — visible in the UI, never a silent skip
  and never a misleading 0-rule "success" (plan §2.6).
- Engine discipline: the app-wide async engine binds to the first event
  loop; every task here builds a fresh engine + sessionmaker and disposes
  it (document_tasks.py pattern, memory 18954) and hands the factory to
  the pipeline (`session_factory` param added in 13c).
- Secrets: decrypted in-process for the pull only (vault rules apply —
  never logged/stored/returned).
"""

import asyncio
import logging
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
from uuid import UUID, uuid4

from sqlalchemy import select

from app.core.celery_app import celery_app
from app.mitre.router import STALE_RUN_MESSAGE, STALE_RUN_MINUTES

logger = logging.getLogger(__name__)

SWEEP_INTERVAL_SECONDS = 15 * 60


def most_recent_due(now, cadence, hour_utc, weekday):
    """Latest scheduled instant <= now for this schedule, or None.

    Pure + unit-tested. weekday follows Python's date.weekday() (0=Monday).
    """
    if cadence not in ("daily", "weekly") or hour_utc is None:
        return None
    candidate = now.replace(hour=hour_utc, minute=0, second=0, microsecond=0)
    if cadence == "daily":
        return candidate if candidate <= now else candidate - timedelta(days=1)
    if weekday is None:
        return None
    days_back = (now.weekday() - weekday) % 7
    candidate = candidate - timedelta(days=days_back)
    return candidate if candidate <= now else candidate - timedelta(days=7)


def _fresh_engine():
    from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

    from app.config import settings

    engine = create_async_engine(settings.database_url, pool_pre_ping=True)
    return engine, async_sessionmaker(engine, expire_on_commit=False)


async def _sweep_async(session_factory, *, enqueue) -> dict:
    """Find due connections; advance last_scheduled_at and enqueue each.
    `enqueue` is injected (celery .delay in prod, a stub in tests)."""
    from app.models.mitre_assessment import MitreAssessment
    from app.models.mitre_connection import MitreConnection

    now = datetime.now(timezone.utc)
    enqueued, skipped_running = [], []
    async with session_factory() as db:
        result = await db.execute(
            select(MitreConnection).where(
                (MitreConnection.schedule_cadence.isnot(None))
                & (MitreConnection.deleted_at.is_(None))
            )
        )
        for connection in result.scalars().all():
            due_at = most_recent_due(
                now,
                connection.schedule_cadence,
                connection.schedule_hour_utc,
                connection.schedule_weekday,
            )
            if due_at is None:
                continue
            if connection.last_scheduled_at is not None and connection.last_scheduled_at >= due_at:
                continue
            # dedup: a RUNNING assessment for this connection blocks the
            # slot. 'pending' does NOT (a never-run preview hasn't touched
            # the SIEM), and a stale 'running' row (>30 min — crashed
            # worker/restart) is flipped to failed HERE, not just lazily on
            # GET, so a dead run can never block the schedule forever
            # (2026-08-02 adversarial finding #1).
            in_flight = await db.execute(
                select(MitreAssessment).where(
                    (MitreAssessment.org_id == connection.org_id)
                    & (MitreAssessment.status == "running")
                    & (MitreAssessment.deleted_at.is_(None))
                    & (
                        MitreAssessment.params["siem"]["connection_id"].astext
                        == str(connection.connection_id)
                    )
                ).limit(1)
            )
            running = in_flight.scalar_one_or_none()
            if running is not None:
                age_cutoff = now - timedelta(minutes=STALE_RUN_MINUTES)
                if running.updated_at is not None and running.updated_at < age_cutoff:
                    running.status = "failed"
                    running.error_message = STALE_RUN_MESSAGE
                    running.updated_at = now
                    await db.commit()
                    logger.warning(
                        f"mitre schedule sweep: flipped stale running assessment "
                        f"{running.assessment_id} to failed (connection "
                        f"{connection.connection_id})"
                    )
                    # a stale flip advances the failure streak too — check
                    # the notification threshold HERE, or a streak could
                    # pass 2 without ever emailing (2026-08-02 adversarial
                    # finding: deploy-restart mid-run is a routine event)
                    await _notify_admins_if_failing(db, connection)
                else:
                    skipped_running.append(str(connection.connection_id))
                    logger.info(
                        f"mitre schedule sweep: connection {connection.connection_id} "
                        "due but a run is in flight — will retry next sweep"
                    )
                    continue
            connection.last_scheduled_at = now
            await db.commit()  # advance BEFORE enqueue: a crashed task never storms
            enqueue(str(connection.connection_id))
            enqueued.append(str(connection.connection_id))
    return {"enqueued": enqueued, "skipped_running": skipped_running}


async def connection_health(db, connection) -> dict:
    """Pull health for one connection from its assessment rows (Phase 13d):
    last pull time/status, last error, and the CONSECUTIVE scheduled-failure
    streak (failed runs since the last completed one; pending/running rows
    are ignored). Shared by the admin health view and the notification
    trigger so both always agree."""
    from app.models.mitre_assessment import MitreAssessment

    result = await db.execute(
        select(MitreAssessment)
        .where(
            (MitreAssessment.org_id == connection.org_id)
            & (MitreAssessment.deleted_at.is_(None))
            & (
                MitreAssessment.params["siem"]["connection_id"].astext
                == str(connection.connection_id)
            )
        )
        .order_by(MitreAssessment.created_at.desc())
        .limit(20)
    )
    rows = result.scalars().all()
    last_pull_at = rows[0].created_at.isoformat() if rows else None
    last_status = rows[0].status if rows else None
    last_error = next(
        (r.error_message[:300] for r in rows if r.status == "failed" and r.error_message),
        None,
    )
    streak = 0
    for row in rows:
        siem = (row.params or {}).get("siem") or {}
        if siem.get("trigger") != "scheduled" or row.status in ("pending", "running"):
            continue
        if row.status == "failed":
            streak += 1
            continue
        break  # completed — streak over
    return {
        "last_pull_at": last_pull_at,
        "last_status": last_status,
        "last_error": last_error,
        "scheduled_failure_streak": streak,
    }


_NOTIFY_AT_STREAK = 2  # exactly-at-2 => one notice per streak, reset on success


async def _notify_admins_if_failing(db, connection) -> int:
    """Plan §2.6: after exactly _NOTIFY_AT_STREAK consecutive scheduled
    failures, email the org's admins once. The body carries the connector's
    static, secret-free error message and connection metadata ONLY — never
    credentials, never rule content. Returns how many emails were sent."""
    from app.email import send_email
    from app.models.user import User

    health = await connection_health(db, connection)
    if health["scheduled_failure_streak"] != _NOTIFY_AT_STREAK:
        return 0

    admins = (
        await db.execute(
            select(User).where(
                (User.org_id == connection.org_id)
                & (User.role == "admin")
                & (User.is_active.is_(True))
            )
        )
    ).scalars().all()
    workspace = (connection.config or {}).get("workspace", "")
    body = (
        f"Scheduled SIEM pulls for the connection '{connection.name}' "
        f"(Microsoft Sentinel, workspace {workspace}) have now failed "
        f"{_NOTIFY_AT_STREAK} times in a row.\n\n"
        f"Most recent error: {health['last_error'] or 'unknown'}\n\n"
        "Runs will keep being attempted on schedule. Fix the credentials or "
        "permissions (the service principal needs 'Microsoft Sentinel "
        "Reader'), or pause the schedule from the connection settings. The "
        "next successful pull resets this notice.\n\n"
        "— ScopeWise (automated notice; you won't be emailed again for this "
        "failure streak)"
    )
    sent = 0
    for admin in admins:
        if await send_email(
            admin.email,
            f"ScopeWise: scheduled SIEM pull failing — {connection.name}",
            body,
        ):
            sent += 1
    logger.warning(
        f"mitre schedule: connection {connection.connection_id} hit "
        f"{_NOTIFY_AT_STREAK} consecutive scheduled failures; notified "
        f"{sent}/{len(admins)} org admins"
    )
    return sent


@celery_app.task(name="mitre.schedule_sweep")
def schedule_sweep() -> dict:
    async def _run():
        engine, factory = _fresh_engine()
        try:
            return await _sweep_async(
                factory, enqueue=lambda cid: run_scheduled_pull.delay(cid)
            )
        finally:
            await engine.dispose()

    return asyncio.run(_run())


async def _record_failed_assessment(db, connection, message: str) -> str:
    """Plan §2.6: a failed scheduled pull must be VISIBLE — create a
    status='failed' assessment row carrying the actionable message."""
    from app.mitre import attack_data
    from app.models.mitre_assessment import MitreAssessment

    now = datetime.now(timezone.utc)
    assessment = MitreAssessment(
        assessment_id=uuid4(),
        org_id=connection.org_id,
        name=f"Scheduled pull · {connection.name}",
        status="failed",
        error_message=str(message)[:2000],
        attack_version=attack_data.DEFAULT.version,
        params={
            "intake": {},
            "siem": {
                "platform": connection.platform,
                "trigger": "scheduled",
                "connection_id": str(connection.connection_id),
                "connection_name": connection.name,
                "pulled_at": now.isoformat(),
            },
        },
        created_by=connection.created_by,
    )
    db.add(assessment)
    await db.commit()
    return str(assessment.assessment_id)


async def _run_scheduled_pull_async(connection_id: str, session_factory) -> dict:
    from fastapi import HTTPException

    from app.mitre import service
    from app.mitre.connectors import vault
    from app.mitre.router import _create_assessment_from_pull
    from app.models.mitre_connection import MitreConnection

    async with session_factory() as db:
        result = await db.execute(
            select(MitreConnection).where(
                (MitreConnection.connection_id == UUID(connection_id))
                & (MitreConnection.deleted_at.is_(None))
            )
        )
        connection = result.scalar_one_or_none()
        if connection is None:
            return {"status": "skipped", "reason": "connection deleted"}

        shim_user = SimpleNamespace(
            org_id=str(connection.org_id),
            user_id=str(connection.created_by) if connection.created_by else None,
        )
        try:
            secret = vault.decrypt_secret(
                connection.secret_ciphertext,
                connection.key_version,
                aad=str(connection.connection_id),
            )
        except vault.VaultError as exc:
            aid = await _record_failed_assessment(db, connection, str(exc))
            await _notify_admins_if_failing(db, connection)
            return {"status": "failed", "assessment_id": aid}

        try:
            response = await _create_assessment_from_pull(
                db,
                shim_user,
                platform=connection.platform,
                config=connection.config,
                secret=secret,
                name=f"Scheduled pull · {connection.name} · "
                f"{datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M')}",
                intake_data={},
                connection=connection,
                trigger="scheduled",
            )
        except HTTPException as exc:
            # connector/config/parse failure — record it visibly (plan §2.6)
            aid = await _record_failed_assessment(db, connection, exc.detail)
            await _notify_admins_if_failing(db, connection)
            return {"status": "failed", "assessment_id": aid}
        finally:
            del secret

        assessment_id = UUID(response["assessment_id"])
        from app.models.mitre_assessment import MitreAssessment

        assessment = await db.get(MitreAssessment, assessment_id)
        assessment.status = "running"
        assessment.updated_at = datetime.now(timezone.utc)
        await db.commit()

    # pipeline gets the worker's own session factory (loop-safe)
    await service.run_assessment_pipeline(
        assessment_id, connection.org_id, session_factory=session_factory
    )
    return {"status": "completed", "assessment_id": str(assessment_id)}


@celery_app.task(name="mitre.run_scheduled_pull")
def run_scheduled_pull(connection_id: str) -> dict:
    async def _run():
        engine, factory = _fresh_engine()
        try:
            return await _run_scheduled_pull_async(connection_id, factory)
        finally:
            await engine.dispose()

    return asyncio.run(_run())


# In-process beat schedule (worker runs `celery ... worker -B`): the ONLY
# beat entry in the app. 15-minute granularity is deliberate — this feeds
# trend data, not alerting (plan §2.5).
celery_app.conf.beat_schedule = {
    "mitre-schedule-sweep": {
        "task": "mitre.schedule_sweep",
        "schedule": float(SWEEP_INTERVAL_SECONDS),
    }
}
