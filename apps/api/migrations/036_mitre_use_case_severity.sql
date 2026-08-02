-- 036: mitre_use_cases gains severity + last_triggered (plan phase A6).
--
-- Customer template upgrade: the use-case template gains two OPTIONAL
-- columns after Status ("Severity", "Last Triggered"). Both are leniently
-- parsed free text (severity: critical/high/medium/low/informational or
-- raw text; last_triggered: an ISO-ish date string or the literal
-- "never", NULL when the column is absent/blank). quality.py applies
-- small deterministic strength adjustments from these when present;
-- absent values change nothing (existing dumps parse identically).
--
-- Plain nullable TEXT columns, no CHECK -> the 5th ORM-sync-point rule
-- does not apply (the model still gains the fields in lockstep).
-- mitre_use_cases is NOT one of test_insights_extra.py's hand-rolled
-- tables, so that fixture needs no edit (verified 2026-08-03). Idempotent.
--
-- Apply to ALL of (no migration runner exists — RCA #3/#11/#12/#13):
--   docker exec -i edgp-postgres psql -U edgp_user -d edgp_dev  < apps/api/migrations/036_mitre_use_case_severity.sql
--   docker exec -i edgp-postgres psql -U edgp_user -d edgp_test < apps/api/migrations/036_mitre_use_case_severity.sql
--   docker exec -i scopewise-postgres psql -U scopewise_user -d scopewise_prod < apps/api/migrations/036_mitre_use_case_severity.sql

BEGIN;
ALTER TABLE mitre_use_cases ADD COLUMN IF NOT EXISTS severity VARCHAR(50);
ALTER TABLE mitre_use_cases ADD COLUMN IF NOT EXISTS last_triggered VARCHAR(50);
COMMIT;
