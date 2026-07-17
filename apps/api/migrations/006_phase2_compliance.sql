-- =====================================================================
-- EDGP Phase 2 — Compliance & Audit Retention
-- Ref: T-2043 (audit log retention policies), T-2045 (compliance export),
--      T-2049 (PII detection)
-- Target: PostgreSQL 16
-- =====================================================================

-- Add audit retention policy to organizations
ALTER TABLE organizations
  ADD COLUMN audit_retention_days INT NOT NULL DEFAULT 90;

-- Validate retention days are only allowed values (30, 90, 365)
ALTER TABLE organizations
  ADD CONSTRAINT ck_organizations_audit_retention_days
    CHECK (audit_retention_days IN (30, 90, 365));

COMMENT ON COLUMN organizations.audit_retention_days IS
  'Number of days to retain audit logs before hard-deletion. Allowed values: 30, 90, 365.';
