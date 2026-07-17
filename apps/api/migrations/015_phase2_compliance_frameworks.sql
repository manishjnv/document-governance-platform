-- =====================================================================
-- EDGP Phase 2 — Compliance Framework Tracking
-- Ref: T-2051 (SOC2), T-2052 (ISO27001), T-2053 (GDPR), T-2054 (HIPAA),
--      T-2055 (compliance report generation)
-- Target: PostgreSQL 16
-- =====================================================================

CREATE TABLE compliance_controls (
  control_id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  org_id                  UUID NOT NULL REFERENCES organizations(org_id) ON DELETE CASCADE,
  framework               VARCHAR(20) NOT NULL,
  control_code            VARCHAR(50) NOT NULL,
  description             TEXT NOT NULL,
  status                  VARCHAR(20) NOT NULL DEFAULT 'not_started',
  evidence_notes          TEXT NULL,
  last_reviewed_at        TIMESTAMPTZ NULL,
  created_at              TIMESTAMPTZ NOT NULL DEFAULT clock_timestamp(),
  updated_at              TIMESTAMPTZ NOT NULL DEFAULT clock_timestamp(),

  CONSTRAINT ck_compliance_controls_framework
    CHECK (framework IN ('SOC2', 'ISO27001', 'GDPR', 'HIPAA')),
  CONSTRAINT ck_compliance_controls_status
    CHECK (status IN ('not_started', 'in_progress', 'implemented', 'verified')),
  CONSTRAINT uq_compliance_controls_org_framework_code
    UNIQUE (org_id, framework, control_code)
);

COMMENT ON TABLE compliance_controls IS
  'Self-reported implementation status of starter compliance-control checklists per framework. This is a self-assessment tool, not a certification or audit. It does not constitute actual SOC2/ISO27001/GDPR/HIPAA compliance.';

COMMENT ON COLUMN compliance_controls.framework IS
  'Compliance framework: SOC2, ISO27001, GDPR, or HIPAA.';
COMMENT ON COLUMN compliance_controls.status IS
  'Implementation status: not_started, in_progress, implemented, or verified.';
COMMENT ON COLUMN compliance_controls.evidence_notes IS
  'Admin notes on evidence or implementation approach for this control.';

CREATE INDEX idx_compliance_controls_org_framework
  ON compliance_controls (org_id, framework);
CREATE INDEX idx_compliance_controls_org_status
  ON compliance_controls (org_id, status);

CREATE TRIGGER trg_compliance_controls_updated_at
  BEFORE UPDATE ON compliance_controls
  FOR EACH ROW EXECUTE FUNCTION set_updated_at();
