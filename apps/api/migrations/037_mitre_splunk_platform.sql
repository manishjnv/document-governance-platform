-- 037: allow 'splunk' in mitre_connections.platform (Splunk REST
-- connector, app/mitre/connectors/splunk.py).
--
-- Apply to ALL of (no migration runner exists — RCA #3/#11/#12/#13):
--   docker exec -i edgp-postgres psql -U edgp_user -d edgp_dev  < apps/api/migrations/037_mitre_splunk_platform.sql
--   docker exec -i edgp-postgres psql -U edgp_user -d edgp_test < apps/api/migrations/037_mitre_splunk_platform.sql
--   docker exec -i scopewise-postgres psql -U scopewise_user -d scopewise_prod < apps/api/migrations/037_mitre_splunk_platform.sql
-- The ORM CheckConstraint mirror in app/models/mitre_connection.py is
-- updated in the same commit (5th sync point: keep in lockstep).
-- test_insights_extra.py's hand-rolled fixture doesn't cover
-- mitre_connections — untouched.

ALTER TABLE mitre_connections
    DROP CONSTRAINT IF EXISTS ck_mitre_connections_platform;
ALTER TABLE mitre_connections
    ADD CONSTRAINT ck_mitre_connections_platform
    CHECK (platform IN ('sentinel', 'splunk'));
