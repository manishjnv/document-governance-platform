-- =====================================================================
-- EDGP Phase 2 — Search History & Saved Searches
-- Ref: T-2005 (search history & saved searches, DB-backed)
-- Target: PostgreSQL 16
--
-- Tables:
--   1. search_history — audit trail of all user searches
--   2. saved_searches — named search templates for reuse
--
-- =====================================================================

-- =====================================================================
-- 1. search_history — audit trail of searches
-- =====================================================================
CREATE TABLE search_history (
  history_id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  org_id              UUID NOT NULL REFERENCES organizations(org_id) ON DELETE CASCADE,
  user_id             UUID NOT NULL REFERENCES users(user_id) ON DELETE CASCADE,
  query               VARCHAR(500) NOT NULL,
  filters             JSONB NOT NULL DEFAULT '{}'::jsonb,
  created_at          TIMESTAMPTZ NOT NULL DEFAULT clock_timestamp()
);

COMMENT ON TABLE search_history IS
  'Audit trail of all user searches. Immutable once inserted (no soft delete).';
COMMENT ON COLUMN search_history.query IS
  'Full-text search query string.';
COMMENT ON COLUMN search_history.filters IS
  'JSON object: {document_type: str|null, date_from: ISO8601|null, date_to: ISO8601|null}';

CREATE INDEX idx_search_history_user_created
  ON search_history (user_id, created_at DESC);
CREATE INDEX idx_search_history_org_created
  ON search_history (org_id, created_at DESC);


-- =====================================================================
-- 2. saved_searches — named search templates
-- =====================================================================
CREATE TABLE saved_searches (
  saved_id            UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  org_id              UUID NOT NULL REFERENCES organizations(org_id) ON DELETE CASCADE,
  user_id             UUID NOT NULL REFERENCES users(user_id) ON DELETE CASCADE,
  name                VARCHAR(255) NOT NULL,
  query               VARCHAR(500) NOT NULL,
  filters             JSONB NOT NULL DEFAULT '{}'::jsonb,
  created_at          TIMESTAMPTZ NOT NULL DEFAULT clock_timestamp()
);

COMMENT ON TABLE saved_searches IS
  'Named search templates for quick reuse. Unique (user_id, name) among active rows.';
COMMENT ON COLUMN saved_searches.query IS
  'Full-text search query string.';
COMMENT ON COLUMN saved_searches.filters IS
  'JSON object: {document_type: str|null, date_from: ISO8601|null, date_to: ISO8601|null}';

CREATE UNIQUE INDEX uq_saved_searches_user_name
  ON saved_searches (user_id, name);
CREATE INDEX idx_saved_searches_user_created
  ON saved_searches (user_id, created_at DESC);
