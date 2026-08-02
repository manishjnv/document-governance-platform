-- 035: schedule columns on mitre_connections (MITRE Phase 13c, plan §2.3).
--
-- Per-connection auto-run schedule, admin-configured, off by default
-- (schedule_cadence NULL). The Celery beat sweep (app/mitre/tasks.py,
-- every 15 min) finds due connections and enqueues pull-and-run tasks;
-- last_scheduled_at advances exactly when a run is enqueued (a failed run
-- still advances — no retry storms; a dedup-skip does not — the slot
-- retries once the in-flight assessment finishes).
--
-- Apply to ALL of (no migration runner exists — RCA #3/#11/#12/#13):
--   docker exec -i edgp-postgres psql -U edgp_user -d edgp_dev  < apps/api/migrations/035_mitre_connection_schedule.sql
--   docker exec -i edgp-postgres psql -U edgp_user -d edgp_test < apps/api/migrations/035_mitre_connection_schedule.sql
--   docker exec -i scopewise-postgres psql -U scopewise_user -d scopewise_prod < apps/api/migrations/035_mitre_connection_schedule.sql
-- Existing-table ALTER, but mitre_connections is NOT in
-- test_insights_extra.py's hand-rolled fixture. 5th sync point: the three
-- CHECKs below are mirrored as ORM CheckConstraints in
-- app/models/mitre_connection.py — keep in lockstep.

ALTER TABLE mitre_connections
    ADD COLUMN IF NOT EXISTS schedule_cadence VARCHAR(10),
    ADD COLUMN IF NOT EXISTS schedule_hour_utc INTEGER,
    ADD COLUMN IF NOT EXISTS schedule_weekday INTEGER,
    ADD COLUMN IF NOT EXISTS last_scheduled_at TIMESTAMPTZ;

BEGIN;
ALTER TABLE mitre_connections DROP CONSTRAINT IF EXISTS ck_mitre_connections_schedule_cadence;
ALTER TABLE mitre_connections ADD CONSTRAINT ck_mitre_connections_schedule_cadence
    CHECK (schedule_cadence IS NULL OR schedule_cadence IN ('daily', 'weekly'));
ALTER TABLE mitre_connections DROP CONSTRAINT IF EXISTS ck_mitre_connections_schedule_hour;
ALTER TABLE mitre_connections ADD CONSTRAINT ck_mitre_connections_schedule_hour
    CHECK (schedule_hour_utc IS NULL OR (schedule_hour_utc >= 0 AND schedule_hour_utc <= 23));
ALTER TABLE mitre_connections DROP CONSTRAINT IF EXISTS ck_mitre_connections_schedule_weekday;
ALTER TABLE mitre_connections ADD CONSTRAINT ck_mitre_connections_schedule_weekday
    CHECK (schedule_weekday IS NULL OR (schedule_weekday >= 0 AND schedule_weekday <= 6));
COMMIT;
