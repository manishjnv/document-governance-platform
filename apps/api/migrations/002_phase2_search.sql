-- =====================================================================
-- EDGP Phase 2 — Full-text search: combined relevance index
-- Ref: T-2001 (PostgreSQL full-text search setup)
-- Target: PostgreSQL 16
--
-- 001_init_schema.sql already indexes parsed_text alone
-- (idx_documents_parsed_text_fts) for basic full-text search. This adds
-- a second GIN index over a *weighted* tsvector combining filename,
-- document_type, and parsed_text, so a single query can rank a
-- filename match above a document_type match above a parsed_text
-- match (see app/search/engine.py's _SEARCH_VECTOR, T-2003). That
-- expression must stay textually identical to the one indexed here, or
-- Postgres falls back to computing to_tsvector() at scan time instead
-- of using this index.
-- =====================================================================

CREATE INDEX idx_documents_search_combined_fts
  ON documents USING GIN ((
    setweight(to_tsvector('english', coalesce(filename, '')), 'A') ||
    setweight(to_tsvector('english', coalesce(document_type, '')), 'B') ||
    setweight(to_tsvector('english', coalesce(parsed_text, '')), 'C')
  ));
