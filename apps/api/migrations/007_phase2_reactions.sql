-- =====================================================================
-- EDGP Phase 2 — Comment Reactions
-- Ref: T-2065 (comment emoji reactions)
-- Target: PostgreSQL 16
--
-- Depends on:
--   - organizations table (org_id FK)
--   - users table (user_id FK)
--   - comments table (comment_id FK) — created in T-2063 (comment.py migration)
-- =====================================================================

-- Comment reactions: emoji toggles per user per comment
CREATE TABLE comment_reactions (
  reaction_id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  comment_id           UUID NOT NULL REFERENCES comments(comment_id) ON DELETE CASCADE,
  user_id              UUID NOT NULL REFERENCES users(user_id) ON DELETE CASCADE,
  emoji                VARCHAR(16) NOT NULL,
  created_at           TIMESTAMPTZ NOT NULL DEFAULT clock_timestamp(),

  -- A user can react with each emoji only once per comment
  CONSTRAINT uq_comment_reactions_per_emoji
    UNIQUE (comment_id, user_id, emoji)
);

COMMENT ON TABLE comment_reactions IS
  'Emoji reactions to comments. One row per unique (comment, user, emoji) triplet. Hard-deleted on toggle.';

CREATE INDEX idx_comment_reactions_comment_id
  ON comment_reactions (comment_id);
CREATE INDEX idx_comment_reactions_user_id
  ON comment_reactions (user_id);
