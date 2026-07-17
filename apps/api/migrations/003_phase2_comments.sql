-- =====================================================================
-- EDGP Phase 2 — Comments & Approvals
-- Ref: T-2061 (comment system), T-2062 (inline annotations), T-2066 (approval workflow)
-- Target: PostgreSQL 16
--
-- Builds on 001_init_schema.sql — organizations, users, documents, reviews
-- already exist, and the set_updated_at() trigger function is already
-- defined there (reused as-is below, not redefined).
-- =====================================================================


-- =====================================================================
-- 7. comments — document comments + inline annotations
-- =====================================================================
CREATE TABLE comments (
  comment_id        UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  org_id            UUID NOT NULL REFERENCES organizations(org_id) ON DELETE CASCADE,
  doc_id            UUID NOT NULL REFERENCES documents(doc_id) ON DELETE CASCADE,
  user_id           UUID NULL REFERENCES users(user_id) ON DELETE SET NULL,
  parent_comment_id UUID NULL REFERENCES comments(comment_id) ON DELETE CASCADE,
  content           TEXT NOT NULL,
  -- Inline annotation range into the document's parsed text (T-2062).
  -- Both NULL = a plain, doc-level (non-anchored) comment.
  anchor_start      INT NULL,
  anchor_end        INT NULL,
  created_at        TIMESTAMPTZ NOT NULL DEFAULT clock_timestamp(),
  updated_at        TIMESTAMPTZ NOT NULL DEFAULT clock_timestamp(),
  deleted_at        TIMESTAMPTZ NULL,

  CONSTRAINT ck_comments_anchor_range
    CHECK (anchor_start IS NULL OR (anchor_end IS NOT NULL AND anchor_end >= anchor_start))
);
COMMENT ON TABLE comments IS
  'Document comments and inline annotations. parent_comment_id threads replies (stored flat; nesting is done by the caller). anchor_start/anchor_end mark an inline text range when present.';

CREATE INDEX idx_comments_org_active ON comments (org_id) WHERE deleted_at IS NULL;
CREATE INDEX idx_comments_doc_id ON comments (doc_id);
CREATE INDEX idx_comments_parent_comment_id ON comments (parent_comment_id);

CREATE TRIGGER trg_comments_updated_at
  BEFORE UPDATE ON comments
  FOR EACH ROW EXECUTE FUNCTION set_updated_at();


-- =====================================================================
-- 8. approvals — per-approver decision on a review
-- =====================================================================
CREATE TABLE approvals (
  approval_id  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  org_id       UUID NOT NULL REFERENCES organizations(org_id) ON DELETE CASCADE,
  review_id    UUID NOT NULL REFERENCES reviews(review_id) ON DELETE CASCADE,
  approver_id  UUID NOT NULL REFERENCES users(user_id) ON DELETE CASCADE,
  status       VARCHAR(50) NOT NULL DEFAULT 'pending',
  notes        TEXT NULL,
  created_at   TIMESTAMPTZ NOT NULL DEFAULT clock_timestamp(),
  updated_at   TIMESTAMPTZ NOT NULL DEFAULT clock_timestamp(),

  CONSTRAINT ck_approvals_status CHECK (status IN ('pending', 'approved', 'rejected'))
);
COMMENT ON TABLE approvals IS
  'One row per (review, approver) — an approver''s pending/decided status on a review. No soft delete: a decision is a permanent record.';

CREATE INDEX idx_approvals_review_id ON approvals (review_id);
CREATE INDEX idx_approvals_approver_status ON approvals (approver_id, status);

CREATE TRIGGER trg_approvals_updated_at
  BEFORE UPDATE ON approvals
  FOR EACH ROW EXECUTE FUNCTION set_updated_at();
