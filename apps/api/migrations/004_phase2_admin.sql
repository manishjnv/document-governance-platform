-- =====================================================================
-- EDGP Phase 2 — Org settings / branding admin fields
-- Ref: T-2081 (org settings backend), T-2082 (org branding)
-- Target: PostgreSQL 16
--
-- Adds logo + brand color columns to organizations so the admin API
-- (T-2081/T-2082) has somewhere to persist tenant branding. Colors are
-- validated as 6-digit hex (#RRGGBB) at the DB layer, matching the
-- CheckConstraint added to app/models/organization.py.
-- =====================================================================

ALTER TABLE organizations ADD COLUMN logo_url VARCHAR(1024) NULL;
ALTER TABLE organizations ADD COLUMN brand_primary_color VARCHAR(7) NULL;
ALTER TABLE organizations ADD COLUMN brand_secondary_color VARCHAR(7) NULL;

COMMENT ON COLUMN organizations.logo_url IS
  'Public URL of the org logo shown on reports/UI. NULL = no custom logo.';
COMMENT ON COLUMN organizations.brand_primary_color IS
  'Primary brand color, #RRGGBB. NULL = platform default.';
COMMENT ON COLUMN organizations.brand_secondary_color IS
  'Secondary brand color, #RRGGBB. NULL = platform default.';

ALTER TABLE organizations ADD CONSTRAINT ck_organizations_brand_colors_format CHECK (
  (brand_primary_color IS NULL OR brand_primary_color ~ '^#[0-9A-Fa-f]{6}$') AND
  (brand_secondary_color IS NULL OR brand_secondary_color ~ '^#[0-9A-Fa-f]{6}$')
);
