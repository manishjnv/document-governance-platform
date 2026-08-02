-- 031: allow 'keyword_tagged' as a mitre_use_cases.mapping_status.
--
-- Phase 6 adds a deterministic keyword/alias tagging pre-pass
-- (app/mitre/keyword_tag.py) that maps untagged rules by exact ATT&CK
-- technique names and curated tool/command aliases BEFORE any AI tagging.
-- Rows it maps get mapping_status='keyword_tagged' so provenance stays
-- distinguishable from customer tags and AI suggestions.
--
-- Adding an allowed value never invalidates existing rows, so the re-add is
-- safe on populated tables. Idempotent: drop-if-exists then add.
--
-- Apply to ALL of (no migration runner exists — RCA #3/#11/#12/#13):
--   docker exec -i edgp-postgres psql -U edgp_user -d edgp_dev  < apps/api/migrations/031_mitre_keyword_tagged_status.sql
--   docker exec -i edgp-postgres psql -U edgp_user -d edgp_test < apps/api/migrations/031_mitre_keyword_tagged_status.sql
--   docker exec -i scopewise-postgres psql -U scopewise_user -d scopewise_prod < apps/api/migrations/031_mitre_keyword_tagged_status.sql
-- mitre_use_cases is NOT one of test_insights_extra.py's 5 hand-rolled
-- tables, so that fixture needs no edit. 5th sync point (CLAUDE.md): the ORM
-- CheckConstraint in app/models/mitre_use_case.py is updated in lockstep.

-- Wrapped so there is no window where the CHECK is absent.
BEGIN;
ALTER TABLE mitre_use_cases DROP CONSTRAINT IF EXISTS ck_mitre_use_cases_mapping_status;
ALTER TABLE mitre_use_cases ADD CONSTRAINT ck_mitre_use_cases_mapping_status
    CHECK (mapping_status IN (
        'customer_tagged', 'keyword_tagged', 'ai_tagged', 'unmapped', 'invalid'
    ));
COMMIT;
