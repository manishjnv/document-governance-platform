-- T-3001: Performance indexes for hot query paths (Phase 3).
--
-- Checked existing migrations first (grep for CREATE INDEX) to avoid
-- duplicates:
--   - audit_logs (org_id, created_at DESC) already exists as
--     idx_audit_logs_org_created (001_init_schema.sql) — skipped.
--   - reviews (doc_id, ...) already exists as idx_reviews_doc_id
--     (001_init_schema.sql) — skipped.
--   - findings has no document_id column (it links via review_id, which
--     is already indexed as idx_findings_review_id) — skipped.
--
-- What's actually missing:
--   - documents: only separate (org_id) and (created_at DESC) indexes
--     exist, no composite for the common "list org's documents by
--     recency" query.
--   - findings: only separate (org_id) and (severity) indexes exist, no
--     composite for "severity-filtered findings per org".
--   - reviews: no index on completed_at, used for "recently completed
--     reviews" queries.
--
-- CONCURRENTLY requires running outside a transaction block.

CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_documents_org_created
    ON documents (org_id, created_at DESC);

CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_findings_org_severity
    ON findings (org_id, severity);

CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_reviews_completed_at
    ON reviews (completed_at DESC);
