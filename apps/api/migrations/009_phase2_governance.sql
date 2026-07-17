-- =====================================================================
-- EDGP Phase 2 — Governance: Document/Review Data Retention
-- Ref: T-2046 (document/review data retention), T-2047 (GDPR export),
--      T-2048 (GDPR right-to-be-forgotten), T-2050 (encryption at rest)
-- Target: PostgreSQL 16
-- =====================================================================

-- Document/review retention policy for organizations. Separate from
-- audit_retention_days (006_phase2_compliance.sql, audit logs only) --
-- this column governs how long documents/reviews are retained before
-- purge_expired_documents() (app/compliance/data_retention.py) soft-deletes
-- them (sets deleted_at, never a hard DELETE -- see 001_init_schema.sql's
-- soft-delete note).
ALTER TABLE organizations ADD COLUMN data_retention_days INT NOT NULL DEFAULT 365;

-- Unlike audit_retention_days (fixed 30/90/365 set), document retention is
-- an open positive-integer policy -- only a floor is enforced here.
ALTER TABLE organizations
  ADD CONSTRAINT ck_organizations_data_retention_days CHECK (data_retention_days > 0);

COMMENT ON COLUMN organizations.data_retention_days IS
  'Number of days to retain documents/reviews before soft-deletion (deleted_at set). Must be > 0. Separate from audit_retention_days (audit logs specifically).';
