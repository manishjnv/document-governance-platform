-- 028: Per-review audit metadata (GUIDELINE_FEASIBILITY_PLAN Phase D).
-- Single JSONB column, nullable, no backfill: parsed-text SHA-256, model(s)
-- actually used per agent, rule library version, app git SHA, timestamp.
--
-- Apply to: local edgp_dev, local edgp_test, VPS scopewise_prod, AND the
-- hand-rolled CREATE TABLE reviews in apps/api/tests/test_insights_extra.py.

ALTER TABLE reviews ADD COLUMN IF NOT EXISTS audit_meta JSONB;
