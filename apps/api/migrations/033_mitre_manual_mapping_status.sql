-- 033: allow 'manual' as a mitre_use_cases.mapping_status.
--
-- Phase 10 adds a per-mapping override: an admin/reviewer can correct a
-- rule's technique mappings (remove a wrong AI/keyword tag, add a missing
-- one) via PATCH /assessments/{id}/use-cases/{id}/mappings. Edited rows get
-- mapping_status='manual' and each mapping source='manual' @ confidence 1.0
-- so provenance stays distinguishable from customer/keyword/AI tags.
--
-- Adding an allowed value never invalidates existing rows, so the re-add is
-- safe on populated tables. Idempotent: drop-if-exists then add.
--
-- Apply to ALL of (no migration runner exists — RCA #3/#11/#12/#13):
--   docker exec -i edgp-postgres psql -U edgp_user -d edgp_dev  < apps/api/migrations/033_mitre_manual_mapping_status.sql
--   docker exec -i edgp-postgres psql -U edgp_user -d edgp_test < apps/api/migrations/033_mitre_manual_mapping_status.sql
--   docker exec -i scopewise-postgres psql -U scopewise_user -d scopewise_prod < apps/api/migrations/033_mitre_manual_mapping_status.sql
-- mitre_use_cases is NOT one of test_insights_extra.py's hand-rolled
-- tables, so that fixture needs no edit. 5th sync point (CLAUDE.md): the ORM
-- CheckConstraint in app/models/mitre_use_case.py is updated in lockstep.

-- Wrapped so there is no window where the CHECK is absent.
BEGIN;
ALTER TABLE mitre_use_cases DROP CONSTRAINT IF EXISTS ck_mitre_use_cases_mapping_status;
ALTER TABLE mitre_use_cases ADD CONSTRAINT ck_mitre_use_cases_mapping_status
    CHECK (mapping_status IN (
        'customer_tagged', 'keyword_tagged', 'ai_tagged', 'manual',
        'unmapped', 'invalid'
    ));
COMMIT;
