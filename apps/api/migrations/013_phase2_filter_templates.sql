-- =====================================================================
-- EDGP Phase 2 Wave 2 — Filter Templates
-- Ref: T-2015 (saved filter templates, reusable across bulk operations)
-- Target: PostgreSQL 16
--
-- Tables:
--   1. filter_templates — user-owned filter templates (no soft delete)
--
-- =====================================================================

CREATE TABLE filter_templates (
  template_id         UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  org_id              UUID NOT NULL REFERENCES organizations(org_id) ON DELETE CASCADE,
  user_id             UUID NOT NULL REFERENCES users(user_id) ON DELETE CASCADE,
  name                VARCHAR(255) NOT NULL,
  filters             JSONB NOT NULL DEFAULT '{}'::jsonb,
  created_at          TIMESTAMPTZ NOT NULL DEFAULT clock_timestamp(),
  updated_at          TIMESTAMPTZ NOT NULL DEFAULT clock_timestamp()
);

COMMENT ON TABLE filter_templates IS
  'User-owned filter templates for reuse in bulk operations and document lists.';
COMMENT ON COLUMN filter_templates.filters IS
  'JSON object: {document_type: str|null, date_from: ISO8601|null, date_to: ISO8601|null, score_min: int|null, score_max: int|null}';

CREATE UNIQUE INDEX uq_filter_templates_user_name
  ON filter_templates (user_id, name);
CREATE INDEX idx_filter_templates_user_created
  ON filter_templates (user_id, created_at DESC);
