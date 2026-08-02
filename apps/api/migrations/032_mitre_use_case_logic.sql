-- 032: add mitre_use_cases.logic — the detection condition/query text.
--
-- Phase 7: until now a dump with BOTH a description and a logic column lost
-- the logic text at create time (router folded logic into description only
-- when description was empty), so neither the keyword pre-pass nor the AI
-- tagger ever saw the actual rule condition. Persisting it separately feeds
-- both taggers (more literal tool/command strings live in the query ->
-- more deterministic matches, fewer AI calls).
--
-- Plain nullable TEXT column, no CHECK -> the 5th ORM-sync-point rule does
-- not apply (the model still gains the field in lockstep). Idempotent.
--
-- Apply to ALL of (no migration runner exists — RCA #3/#11/#12/#13):
--   docker exec -i edgp-postgres psql -U edgp_user -d edgp_dev  < apps/api/migrations/032_mitre_use_case_logic.sql
--   docker exec -i edgp-postgres psql -U edgp_user -d edgp_test < apps/api/migrations/032_mitre_use_case_logic.sql
--   docker exec -i scopewise-postgres psql -U scopewise_user -d scopewise_prod < apps/api/migrations/032_mitre_use_case_logic.sql
-- mitre_use_cases is NOT one of test_insights_extra.py's 5 hand-rolled
-- tables, so that fixture needs no edit.

BEGIN;
ALTER TABLE mitre_use_cases ADD COLUMN IF NOT EXISTS logic TEXT;
COMMIT;
