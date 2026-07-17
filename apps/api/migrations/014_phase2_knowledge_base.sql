-- =====================================================================
-- EDGP Phase 2 Wave 2 — Knowledge Base (FAQ, Best Practices, Guides)
-- Ref: T-2036 (FAQ database), T-2037 (similar findings search),
--      T-2038 (issue resolution database), T-2039 (best practices guide),
--      T-2040 (knowledge base search UI)
-- =====================================================================


-- =====================================================================
-- kb_articles — unified table for FAQs, best practices, and guides
-- One table, three article_type values. Reuses set_updated_at() trigger
-- from migration 001.
-- =====================================================================
CREATE TABLE kb_articles (
  article_id            UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  org_id                UUID NOT NULL REFERENCES organizations(org_id) ON DELETE CASCADE,
  article_type          VARCHAR(50) NOT NULL,
  title                 VARCHAR(255) NOT NULL,
  content               TEXT NOT NULL,
  tags                  JSONB NOT NULL DEFAULT '[]'::jsonb,
  created_by_user_id    UUID NULL REFERENCES users(user_id) ON DELETE SET NULL,
  created_at            TIMESTAMPTZ NOT NULL DEFAULT clock_timestamp(),
  updated_at            TIMESTAMPTZ NOT NULL DEFAULT clock_timestamp(),
  deleted_at            TIMESTAMPTZ NULL,

  CONSTRAINT ck_kb_articles_type
    CHECK (article_type IN ('faq', 'best_practice', 'guide'))
);

COMMENT ON TABLE kb_articles IS
  'Knowledge base articles: FAQs, best practices, guides. One unified table to avoid over-splitting schema.';

CREATE TRIGGER trg_kb_articles_updated_at
  BEFORE UPDATE ON kb_articles
  FOR EACH ROW EXECUTE FUNCTION set_updated_at();

-- Org-scoped active index
CREATE INDEX idx_kb_articles_org_active
  ON kb_articles (org_id) WHERE deleted_at IS NULL;

-- Full-text search index over title + content
CREATE INDEX idx_kb_articles_search_combined_fts
  ON kb_articles USING GIN (to_tsvector('english', title || ' ' || content))
  WHERE deleted_at IS NULL;

-- Type filter index
CREATE INDEX idx_kb_articles_type
  ON kb_articles (article_type) WHERE deleted_at IS NULL;
