-- 027: Typed evidence model on findings (GUIDELINE_FEASIBILITY_PLAN Phase B).
-- All columns nullable, no backfill -- historical findings keep freetext
-- evidence only. evidence_type vocabulary per SOW_Review_Training_Guideline
-- §1/§6.
--
-- Apply to: local edgp_dev, local edgp_test, VPS scopewise_prod, AND the
-- hand-rolled CREATE TABLE in apps/api/tests/test_insights_extra.py.

ALTER TABLE findings
    ADD COLUMN IF NOT EXISTS evidence_type VARCHAR(30),
    ADD COLUMN IF NOT EXISTS page INT,
    ADD COLUMN IF NOT EXISTS line_start INT,
    ADD COLUMN IF NOT EXISTS line_end INT,
    ADD COLUMN IF NOT EXISTS anchor_before VARCHAR(255),
    ADD COLUMN IF NOT EXISTS anchor_after VARCHAR(255),
    ADD COLUMN IF NOT EXISTS matched_text TEXT;

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint WHERE conname = 'ck_findings_evidence_type'
    ) THEN
        ALTER TABLE findings ADD CONSTRAINT ck_findings_evidence_type
            CHECK (evidence_type IS NULL OR evidence_type IN
                ('location', 'missing_section', 'cross_document', 'conflict', 'reference'));
    END IF;
END $$;
