-- 039: Code Security Review module (Phase 1). New table + widened audit CHECK.
--
-- Apply to ALL of (no migration runner exists — RCA #3/#11/#12/#13):
--   docker exec -i edgp-postgres psql -U edgp_user -d edgp_dev  < apps/api/migrations/039_code_review.sql
--   docker exec -i edgp-postgres psql -U edgp_user -d edgp_test < apps/api/migrations/039_code_review.sql
--   docker exec -i scopewise-postgres psql -U scopewise_user -d scopewise_prod < apps/api/migrations/039_code_review.sql
--
-- audit_logs is NOT one of test_insights_extra.py's hand-rolled tables, so
-- that fixture needs no edit.
--
-- updated_at is maintained by the application (no set_updated_at trigger),
-- same pattern as migration 029.

CREATE TABLE IF NOT EXISTS code_reviews (
    review_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    org_id UUID NOT NULL REFERENCES organizations(org_id) ON DELETE CASCADE,
    name VARCHAR(255) NOT NULL,
    repo_label VARCHAR(255),
    git_sha VARCHAR(64),
    source_format VARCHAR(10) NOT NULL,
    source_path VARCHAR(500) NOT NULL,
    manifest_path VARCHAR(500),
    report JSONB NOT NULL,
    created_by UUID REFERENCES users(user_id) ON DELETE SET NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT clock_timestamp(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT clock_timestamp(),
    deleted_at TIMESTAMPTZ
);

DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'ck_code_reviews_source_format') THEN
        ALTER TABLE code_reviews ADD CONSTRAINT ck_code_reviews_source_format
            CHECK (source_format IN ('findings', 'sarif'));
    END IF;
END $$;

CREATE INDEX IF NOT EXISTS ix_code_reviews_org ON code_reviews (org_id);

COMMENT ON TABLE code_reviews IS 'Code Security Review module (app/codereview): one row per imported VVAH findings.json/SARIF report, normalized report lives in the report JSONB column.';

-- Widen audit_logs.resource_type CHECK to allow 'code_review' (mirror in
-- app/models/audit_log.py and enums.AuditResourceType). Wrapped so there is
-- no window where the CHECK is absent.
BEGIN;
ALTER TABLE audit_logs DROP CONSTRAINT IF EXISTS ck_audit_logs_resource_type;
ALTER TABLE audit_logs ADD CONSTRAINT ck_audit_logs_resource_type
    CHECK (resource_type IN (
        'document', 'review', 'finding', 'user', 'organization',
        'mitre_assessment', 'code_review'
    ));
COMMIT;
