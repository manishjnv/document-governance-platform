-- 038: allow 'tool_attested' as a mitre_use_cases.mapping_status.
--
-- Tool-coverage attestation (MITRE_TOOL_COVERAGE_PLAN.md, 2026-08-19):
-- confirming a matched security tool's alert path creates one enabled rule
-- row per credited technique with mapping_status='tool_attested' (mapping
-- source stays 'manual' @ confidence 1.0 so every existing surface renders
-- it), and coverage is recomputed inline — the customer owns the claim.
--
-- Apply to ALL of (no migration runner exists — RCA #3/#11/#12/#13):
--   docker exec -i edgp-postgres psql -U edgp_user -d edgp_dev  < apps/api/migrations/038_mitre_tool_attested_status.sql
--   docker exec -i edgp-postgres psql -U edgp_user -d edgp_test < apps/api/migrations/038_mitre_tool_attested_status.sql
--   docker exec -i scopewise-postgres psql -U scopewise_user -d scopewise_prod < apps/api/migrations/038_mitre_tool_attested_status.sql
-- The ORM CheckConstraint mirror in app/models/mitre_use_case.py is updated
-- in the same commit (5th sync point: keep in lockstep).
-- test_insights_extra.py's hand-rolled fixture doesn't cover
-- mitre_use_cases — untouched.

BEGIN;
ALTER TABLE mitre_use_cases DROP CONSTRAINT IF EXISTS ck_mitre_use_cases_mapping_status;
ALTER TABLE mitre_use_cases ADD CONSTRAINT ck_mitre_use_cases_mapping_status
    CHECK (mapping_status IN (
        'customer_tagged', 'keyword_tagged', 'ai_tagged', 'manual',
        'tool_attested', 'unmapped', 'invalid'
    ));
COMMIT;
