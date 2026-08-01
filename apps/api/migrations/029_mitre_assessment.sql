-- 029: MITRE ATT&CK coverage-assessment module (Phase 1).
-- New tables ONLY — zero ALTERs to existing tables, deliberately keeping the
-- test_insights_extra.py hand-rolled fixture out of play. Keep it that way.
--
-- Apply to: local edgp_dev, local edgp_test. VPS scopewise_prod is applied in
-- Phase 5 (deploy), not before:
--   docker exec -i edgp-postgres psql -U edgp_user -d edgp_dev  < apps/api/migrations/029_mitre_assessment.sql
--   docker exec -i edgp-postgres psql -U edgp_user -d edgp_test < apps/api/migrations/029_mitre_assessment.sql
--
-- updated_at is maintained by the application (no set_updated_at trigger on
-- these tables) — the stale-run guard sets it explicitly on status changes.

CREATE TABLE IF NOT EXISTS mitre_assessments (
    assessment_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    org_id UUID NOT NULL REFERENCES organizations(org_id) ON DELETE CASCADE,
    name VARCHAR(255) NOT NULL,
    status VARCHAR(50) NOT NULL DEFAULT 'pending',
    attack_version VARCHAR(20) NOT NULL,
    params JSONB,
    technique_results JSONB,
    summary JSONB,
    error_message TEXT,
    completed_at TIMESTAMPTZ,
    created_by UUID REFERENCES users(user_id) ON DELETE SET NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT clock_timestamp(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT clock_timestamp(),
    deleted_at TIMESTAMPTZ
);

DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'ck_mitre_assessments_status') THEN
        ALTER TABLE mitre_assessments ADD CONSTRAINT ck_mitre_assessments_status
            CHECK (status IN ('pending', 'running', 'completed', 'failed'));
    END IF;
    IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'ck_mitre_assessments_completed_has_timestamp') THEN
        ALTER TABLE mitre_assessments ADD CONSTRAINT ck_mitre_assessments_completed_has_timestamp
            CHECK (status <> 'completed' OR completed_at IS NOT NULL);
    END IF;
    IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'ck_mitre_assessments_failed_has_error') THEN
        ALTER TABLE mitre_assessments ADD CONSTRAINT ck_mitre_assessments_failed_has_error
            CHECK (status <> 'failed' OR error_message IS NOT NULL);
    END IF;
END $$;

CREATE INDEX IF NOT EXISTS ix_mitre_assessments_org ON mitre_assessments (org_id);

CREATE TABLE IF NOT EXISTS mitre_files (
    file_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    assessment_id UUID NOT NULL REFERENCES mitre_assessments(assessment_id) ON DELETE CASCADE,
    org_id UUID NOT NULL REFERENCES organizations(org_id) ON DELETE CASCADE,
    kind VARCHAR(20) NOT NULL,
    filename VARCHAR(255) NOT NULL,
    file_type VARCHAR(10) NOT NULL,
    s3_path VARCHAR(500) NOT NULL,
    parse_status VARCHAR(50) NOT NULL DEFAULT 'parsed',
    row_count INT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT clock_timestamp(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT clock_timestamp(),
    deleted_at TIMESTAMPTZ
);

DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'ck_mitre_files_kind') THEN
        ALTER TABLE mitre_files ADD CONSTRAINT ck_mitre_files_kind
            CHECK (kind IN ('use_cases', 'environment'));
    END IF;
    IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'ck_mitre_files_file_type') THEN
        ALTER TABLE mitre_files ADD CONSTRAINT ck_mitre_files_file_type
            CHECK (file_type IN ('xlsx', 'xls', 'csv', 'pdf', 'docx'));
    END IF;
END $$;

CREATE INDEX IF NOT EXISTS ix_mitre_files_assessment ON mitre_files (assessment_id);

CREATE TABLE IF NOT EXISTS mitre_use_cases (
    use_case_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    assessment_id UUID NOT NULL REFERENCES mitre_assessments(assessment_id) ON DELETE CASCADE,
    org_id UUID NOT NULL REFERENCES organizations(org_id) ON DELETE CASCADE,
    file_id UUID REFERENCES mitre_files(file_id) ON DELETE SET NULL,
    row_ref VARCHAR(100) NOT NULL,
    name VARCHAR(500) NOT NULL,
    description TEXT,
    log_source VARCHAR(255),
    enabled BOOLEAN,  -- NULL = unknown (treated as enabled + assumption)
    mappings JSONB NOT NULL DEFAULT '[]'::jsonb,
    mapping_status VARCHAR(30) NOT NULL DEFAULT 'unmapped',
    created_at TIMESTAMPTZ NOT NULL DEFAULT clock_timestamp(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT clock_timestamp(),
    deleted_at TIMESTAMPTZ
);

DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'ck_mitre_use_cases_mapping_status') THEN
        ALTER TABLE mitre_use_cases ADD CONSTRAINT ck_mitre_use_cases_mapping_status
            CHECK (mapping_status IN ('customer_tagged', 'ai_tagged', 'unmapped', 'invalid'));
    END IF;
END $$;

CREATE INDEX IF NOT EXISTS ix_mitre_use_cases_assessment ON mitre_use_cases (assessment_id);

-- Org-keyed tunables (app/admin/customization.py pattern: absent row = code
-- default). Keys: confidence_covered, confidence_partial_floor,
-- partial_credit, count_disabled_as_coverage. JSONB value holds float/bool.
CREATE TABLE IF NOT EXISTS mitre_settings (
    org_id UUID NOT NULL REFERENCES organizations(org_id) ON DELETE CASCADE,
    setting_key VARCHAR(50) NOT NULL,
    setting_value JSONB NOT NULL,
    PRIMARY KEY (org_id, setting_key)
);

COMMENT ON TABLE mitre_assessments IS 'MITRE ATT&CK coverage assessment runs (module: app/mitre). technique_results/summary are materialized at run time against the stamped attack_version.';
COMMENT ON TABLE mitre_files IS 'Uploaded MITRE-assessment source files (use-case dump / environment workbook), stored via the platform storage backend.';
COMMENT ON TABLE mitre_use_cases IS 'One row per detection rule parsed from a use-case dump; mappings JSONB carries [{technique_id, source, confidence, rationale}].';
COMMENT ON TABLE mitre_settings IS 'Per-org MITRE tunables. Absent row = code default (see app/mitre/service.py).';
