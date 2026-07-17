-- =====================================================================
-- EDGP Phase 2 Wave 2 — Analytics & Reporting
-- Ref: T-2006 (document analytics), T-2007 (review metrics aggregation),
--      T-2008 (performance dashboard), T-2016 (custom report builder),
--      T-2018 (report templates), T-2020 (report archive & history)
-- Target: PostgreSQL 16
--
-- Tables:
--   1. document_views  — per-read audit trail, feeds view_count /
--                         unique_viewer_count in T-2006
--   2. report_archive  — saved snapshots of generated reports (T-2016 /
--                         T-2018 / T-2020)
-- =====================================================================

-- =====================================================================
-- 1. document_views — one row per document read
-- =====================================================================
CREATE TABLE document_views (
  view_id       UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  org_id        UUID NOT NULL REFERENCES organizations(org_id) ON DELETE CASCADE,
  doc_id        UUID NOT NULL REFERENCES documents(doc_id) ON DELETE CASCADE,
  user_id       UUID REFERENCES users(user_id) ON DELETE SET NULL,
  viewed_at     TIMESTAMPTZ NOT NULL DEFAULT clock_timestamp()
);

COMMENT ON TABLE document_views IS
  'One row per document read. Immutable (no soft delete). Feeds view_count/unique_viewer_count in T-2006.';

CREATE INDEX idx_document_views_doc_viewed
  ON document_views (doc_id, viewed_at DESC);


-- =====================================================================
-- 2. report_archive — generated report snapshots
-- =====================================================================
CREATE TABLE report_archive (
  report_id             UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  org_id                UUID NOT NULL REFERENCES organizations(org_id) ON DELETE CASCADE,
  generated_by_user_id  UUID REFERENCES users(user_id) ON DELETE SET NULL,
  report_type           VARCHAR(50) NOT NULL,
  format                VARCHAR(20) NOT NULL DEFAULT 'json',
  filters               JSONB NOT NULL DEFAULT '{}'::jsonb,
  content               TEXT NOT NULL,
  created_at            TIMESTAMPTZ NOT NULL DEFAULT clock_timestamp()
);

COMMENT ON TABLE report_archive IS
  'Generated report snapshots (T-2016 custom builder, T-2018 templates). Immutable once written; read back via T-2020.';

CREATE INDEX idx_report_archive_org_created
  ON report_archive (org_id, created_at DESC);
