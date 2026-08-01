-- 030: allow 'mitre_assessment' as an audit_logs.resource_type.
--
-- The MITRE module (migration 029) logged its per-assessment audit events
-- with resource_type='organization' because 001's closed CHECK predated the
-- module and Phases 1-4 deliberately avoided ALTERing shared tables. This
-- closes that wart so the audit trail names what it actually touched.
--
-- Adding an allowed value never invalidates existing rows, so the re-add is
-- safe on populated tables. Idempotent: drop-if-exists then add.
--
-- Apply to ALL of (no migration runner exists — RCA #3/#11/#12/#13):
--   docker exec -i edgp-postgres psql -U edgp_user -d edgp_dev  < apps/api/migrations/030_audit_mitre_resource_type.sql
--   docker exec -i edgp-postgres psql -U edgp_user -d edgp_test < apps/api/migrations/030_audit_mitre_resource_type.sql
--   docker exec -i scopewise-postgres psql -U scopewise_user -d scopewise_prod < apps/api/migrations/030_audit_mitre_resource_type.sql
-- audit_logs is NOT one of test_insights_extra.py's 5 hand-rolled tables, so
-- that fixture needs no edit.

-- Wrapped so there is no window where the CHECK is absent.
BEGIN;
ALTER TABLE audit_logs DROP CONSTRAINT IF EXISTS ck_audit_logs_resource_type;
ALTER TABLE audit_logs ADD CONSTRAINT ck_audit_logs_resource_type
    CHECK (resource_type IN (
        'document', 'review', 'finding', 'user', 'organization',
        'mitre_assessment'
    ));
COMMIT;
