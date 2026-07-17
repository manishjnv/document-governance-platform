-- =====================================================================
-- EDGP Phase 2 Wave 2 — Mentions, Templates, Notifications, History
-- Ref: T-2064 (mentions), T-2067 (multi-approvers), T-2068 (templates),
--      T-2069 (notifications), T-2070 (history)
-- Target: PostgreSQL 16
--
-- Builds on 001-015 (organizations, users, documents, reviews, comments, approvals exist)
-- =====================================================================


-- =====================================================================
-- Add mentioned_user_ids to comments (T-2064)
-- =====================================================================
ALTER TABLE comments
  ADD COLUMN mentioned_user_ids JSONB NULL;

COMMENT ON COLUMN comments.mentioned_user_ids IS
  'Array of @-mentioned user UUIDs, stored as JSONB for flexibility. Null if no mentions.';


-- =====================================================================
-- approval_templates — reusable approval workflows (T-2068)
-- =====================================================================
CREATE TABLE approval_templates (
  template_id       UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  org_id            UUID NOT NULL REFERENCES organizations(org_id) ON DELETE CASCADE,
  name              VARCHAR(255) NOT NULL,
  -- List of approver UUIDs; JSONB for flexible list handling
  approver_user_ids JSONB NOT NULL,
  -- 'parallel' = all approvers start pending; 'serial' = only first row created initially
  mode              VARCHAR(20) NOT NULL DEFAULT 'parallel',
  created_at        TIMESTAMPTZ NOT NULL DEFAULT clock_timestamp(),

  CONSTRAINT ck_approval_templates_mode CHECK (mode IN ('parallel', 'serial')),
  CONSTRAINT ck_approval_templates_approvers CHECK (jsonb_array_length(approver_user_ids) > 0)
);

COMMENT ON TABLE approval_templates IS
  'Template for rapidly spinning up approval workflows. Specifies a list of approvers and an execution mode (parallel or serial).';

CREATE INDEX idx_approval_templates_org_id ON approval_templates (org_id);
