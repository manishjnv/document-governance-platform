-- =====================================================================
-- EDGP Phase 1 MVP — Initial schema
-- Ref: 3_DATABASE_SCHEMA.md, T-201/T-202/T-204..T-209
-- Target: PostgreSQL 16
--
-- Deviations from 3_DATABASE_SCHEMA.md (that doc is pseudo-SQL, not
-- valid Postgres, and has a few bugs — fixed here, see inline notes):
--   1. `INDEX ... ON (...)` inside CREATE TABLE is MySQL syntax, not
--      Postgres. Split into standalone CREATE INDEX statements below.
--   2. TIMESTAMP -> TIMESTAMPTZ everywhere (multi-tenant SaaS spans
--      timezones; naive timestamps are a correctness bug waiting to
--      happen).
--   3. *_user_id columns were `NOT NULL` + `ON DELETE SET NULL` at the
--      same time, which is self-contradicting (deleting the user would
--      violate NOT NULL). Made nullable to match the doc's own stated
--      intent ("preserve audit trail" when a user is removed).
--   4. UNIQUE(org_id, email) / UNIQUE(org_id, s3_path, version) as hard
--      constraints would permanently block reuse after a soft delete
--      (the "deleted" row still occupies the key). Converted to partial
--      unique indexes scoped to `deleted_at IS NULL`.
--   5. reviews.UNIQUE(doc_id, version) referenced a `version` column
--      that doesn't exist on `reviews`. Removed; added
--      `document_version` (which document version this review ran
--      against) with a plain index — re-review/retry is allowed, so no
--      uniqueness constraint.
--   6. documents had no way to group multiple versions of "the same"
--      document (doc_id is the per-row/per-version PK). Added
--      `document_group_id` so version history is queryable without a
--      second table.
--   7. Enum-like VARCHAR columns get CHECK constraints (no magic
--      strings enforced only in application code).
--   8. findings gets a cross-column CHECK tying finding_source to
--      exactly one of agent_name / rule_id.
--
-- Soft delete: enforced at the application/repository layer (always
-- `UPDATE ... SET deleted_at = now()`, never a raw DELETE). No
-- delete-intercepting trigger:
-- ponytail: a BEFORE DELETE trigger that rewrites deletes into soft
-- deletes would also silently swallow the *manual* GDPR hard-delete
-- path the doc's own retention policy calls for. App-level is the
-- correct layer here; add a trigger only if raw SQL deletes from
-- outside the app become a real, recurring threat.
-- =====================================================================


-- ---------------------------------------------------------------------
-- Shared trigger: auto-touch updated_at on every UPDATE.
-- ---------------------------------------------------------------------
CREATE OR REPLACE FUNCTION set_updated_at()
RETURNS TRIGGER AS $$
BEGIN
  NEW.updated_at = clock_timestamp();
  RETURN NEW;
END;
$$ LANGUAGE plpgsql;


-- =====================================================================
-- 1. organizations — tenant container
-- =====================================================================
CREATE TABLE organizations (
  org_id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  name                VARCHAR(255) NOT NULL,
  subscription_tier   VARCHAR(50) NOT NULL DEFAULT 'free',
  created_at          TIMESTAMPTZ NOT NULL DEFAULT clock_timestamp(),
  updated_at          TIMESTAMPTZ NOT NULL DEFAULT clock_timestamp(),
  deleted_at          TIMESTAMPTZ NULL,

  CONSTRAINT ck_organizations_subscription_tier
    CHECK (subscription_tier IN ('free', 'pro', 'enterprise'))
);
COMMENT ON TABLE organizations IS
  'Tenant/organization container. Every other table is scoped to org_id for isolation.';

CREATE UNIQUE INDEX uq_organizations_name_active
  ON organizations (name) WHERE deleted_at IS NULL;
CREATE INDEX idx_organizations_deleted_at ON organizations (deleted_at);

CREATE TRIGGER trg_organizations_updated_at
  BEFORE UPDATE ON organizations
  FOR EACH ROW EXECUTE FUNCTION set_updated_at();


-- =====================================================================
-- 2. users — per-org users
-- =====================================================================
CREATE TABLE users (
  user_id         UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  org_id          UUID NOT NULL REFERENCES organizations(org_id) ON DELETE CASCADE,
  email           VARCHAR(255) NOT NULL,
  password_hash   VARCHAR(255) NULL,          -- bcrypt hash; NULL if SSO-only
  full_name       VARCHAR(255) NULL,
  role            VARCHAR(50) NOT NULL DEFAULT 'viewer',
  is_active       BOOLEAN NOT NULL DEFAULT TRUE,
  last_login      TIMESTAMPTZ NULL,
  created_at      TIMESTAMPTZ NOT NULL DEFAULT clock_timestamp(),
  updated_at      TIMESTAMPTZ NOT NULL DEFAULT clock_timestamp(),
  deleted_at      TIMESTAMPTZ NULL,

  CONSTRAINT ck_users_role CHECK (role IN ('admin', 'reviewer', 'viewer'))
);
COMMENT ON TABLE users IS
  'Users scoped to an organization. Same email may exist in different orgs (composite uniqueness).';

CREATE UNIQUE INDEX uq_users_org_email_active
  ON users (org_id, email) WHERE deleted_at IS NULL;
CREATE INDEX idx_users_org_active ON users (org_id) WHERE deleted_at IS NULL;

CREATE TRIGGER trg_users_updated_at
  BEFORE UPDATE ON users
  FOR EACH ROW EXECUTE FUNCTION set_updated_at();


-- =====================================================================
-- 3. documents — uploaded files (one row per version)
-- =====================================================================
CREATE TABLE documents (
  doc_id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  -- Stable identifier shared across versions of "the same" document.
  -- Defaults to a fresh UUID for a brand-new upload; the app carries the
  -- existing group's id forward when a new version is uploaded.
  document_group_id   UUID NOT NULL DEFAULT gen_random_uuid(),
  org_id              UUID NOT NULL REFERENCES organizations(org_id) ON DELETE CASCADE,
  uploaded_by_user_id UUID NULL REFERENCES users(user_id) ON DELETE SET NULL,
  filename            VARCHAR(255) NOT NULL,
  original_filename   VARCHAR(255) NOT NULL,
  file_size_bytes     BIGINT NOT NULL,
  file_type           VARCHAR(20) NOT NULL,
  s3_path             VARCHAR(512) NOT NULL,
  s3_etag             VARCHAR(100) NULL,
  version             INT NOT NULL DEFAULT 1,
  parsed_text         TEXT NULL,
  parsed_sections     JSONB NULL,
  document_type       VARCHAR(50) NULL,
  page_count          INT NULL,
  language            VARCHAR(10) NOT NULL DEFAULT 'en',
  storage_status      VARCHAR(50) NOT NULL DEFAULT 'uploaded',
  created_at          TIMESTAMPTZ NOT NULL DEFAULT clock_timestamp(),
  updated_at          TIMESTAMPTZ NOT NULL DEFAULT clock_timestamp(),
  deleted_at          TIMESTAMPTZ NULL,

  CONSTRAINT ck_documents_file_type CHECK (file_type IN ('pdf', 'docx')),
  CONSTRAINT ck_documents_document_type
    CHECK (document_type IS NULL OR document_type IN ('SOW', 'Proposal', 'Other')),
  CONSTRAINT ck_documents_storage_status
    CHECK (storage_status IN ('uploaded', 'archived', 'deleted_from_s3')),
  CONSTRAINT ck_documents_version_positive CHECK (version > 0),
  CONSTRAINT ck_documents_file_size_positive CHECK (file_size_bytes > 0),
  CONSTRAINT ck_documents_page_count_nonneg CHECK (page_count IS NULL OR page_count >= 0)
);
COMMENT ON TABLE documents IS
  'Uploaded documents. One row per version; document_group_id links versions of the same logical document.';

CREATE UNIQUE INDEX uq_documents_org_s3path_version_active
  ON documents (org_id, s3_path, version) WHERE deleted_at IS NULL;
CREATE INDEX idx_documents_org_active ON documents (org_id) WHERE deleted_at IS NULL;
CREATE INDEX idx_documents_uploaded_by ON documents (uploaded_by_user_id);
CREATE INDEX idx_documents_document_type ON documents (document_type);
CREATE INDEX idx_documents_created_at ON documents (created_at DESC);
CREATE INDEX idx_documents_group ON documents (document_group_id, version DESC);
-- Full-text search over extracted text (Phase 2 cross-document search groundwork).
CREATE INDEX idx_documents_parsed_text_fts
  ON documents USING GIN (to_tsvector('english', coalesce(parsed_text, '')));

CREATE TRIGGER trg_documents_updated_at
  BEFORE UPDATE ON documents
  FOR EACH ROW EXECUTE FUNCTION set_updated_at();


-- =====================================================================
-- 4. reviews — AI review executions
-- =====================================================================
CREATE TABLE reviews (
  review_id            UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  org_id               UUID NOT NULL REFERENCES organizations(org_id) ON DELETE CASCADE,
  doc_id               UUID NOT NULL REFERENCES documents(doc_id) ON DELETE CASCADE,
  -- Which version of the document this review actually ran against
  -- (documents.version at the time the review started).
  document_version     INT NOT NULL DEFAULT 1,
  triggered_by_user_id UUID NULL REFERENCES users(user_id) ON DELETE SET NULL,
  status               VARCHAR(50) NOT NULL DEFAULT 'pending',
  overall_score        DECIMAL(5,2) NULL,
  risk_score           DECIMAL(5,2) NULL,

  score_completeness   DECIMAL(5,2) NULL,
  score_clarity        DECIMAL(5,2) NULL,
  score_consistency    DECIMAL(5,2) NULL,
  score_commercial     DECIMAL(5,2) NULL,
  score_delivery       DECIMAL(5,2) NULL,
  score_operations     DECIMAL(5,2) NULL,
  score_security       DECIMAL(5,2) NULL,

  executive_summary       TEXT NULL,
  critical_finding_count  INT NOT NULL DEFAULT 0,
  major_finding_count     INT NOT NULL DEFAULT 0,
  medium_finding_count    INT NOT NULL DEFAULT 0,
  low_finding_count       INT NOT NULL DEFAULT 0,
  info_finding_count      INT NOT NULL DEFAULT 0,

  started_at              TIMESTAMPTZ NOT NULL DEFAULT clock_timestamp(),
  completed_at             TIMESTAMPTZ NULL,
  processing_time_seconds INT NULL,

  error_message   TEXT NULL,
  error_details   JSONB NULL,

  created_at  TIMESTAMPTZ NOT NULL DEFAULT clock_timestamp(),
  updated_at  TIMESTAMPTZ NOT NULL DEFAULT clock_timestamp(),
  deleted_at  TIMESTAMPTZ NULL,

  CONSTRAINT ck_reviews_status
    CHECK (status IN ('pending', 'running', 'completed', 'failed')),
  CONSTRAINT ck_reviews_completed_has_timestamp
    CHECK (status <> 'completed' OR completed_at IS NOT NULL),
  CONSTRAINT ck_reviews_failed_has_error
    CHECK (status <> 'failed' OR error_message IS NOT NULL),
  CONSTRAINT ck_reviews_scores_range CHECK (
    (overall_score      IS NULL OR overall_score      BETWEEN 0 AND 100) AND
    (risk_score         IS NULL OR risk_score         BETWEEN 0 AND 100) AND
    (score_completeness IS NULL OR score_completeness BETWEEN 0 AND 100) AND
    (score_clarity      IS NULL OR score_clarity      BETWEEN 0 AND 100) AND
    (score_consistency  IS NULL OR score_consistency  BETWEEN 0 AND 100) AND
    (score_commercial   IS NULL OR score_commercial   BETWEEN 0 AND 100) AND
    (score_delivery     IS NULL OR score_delivery     BETWEEN 0 AND 100) AND
    (score_operations   IS NULL OR score_operations   BETWEEN 0 AND 100) AND
    (score_security     IS NULL OR score_security     BETWEEN 0 AND 100)
  ),
  CONSTRAINT ck_reviews_finding_counts_nonneg CHECK (
    critical_finding_count >= 0 AND major_finding_count >= 0 AND
    medium_finding_count >= 0 AND low_finding_count >= 0 AND info_finding_count >= 0
  ),
  CONSTRAINT ck_reviews_processing_time_nonneg
    CHECK (processing_time_seconds IS NULL OR processing_time_seconds >= 0),
  CONSTRAINT ck_reviews_document_version_positive CHECK (document_version > 0)
);
COMMENT ON TABLE reviews IS
  'One row per AI review execution against a specific document version.';

CREATE INDEX idx_reviews_org_active ON reviews (org_id) WHERE deleted_at IS NULL;
CREATE INDEX idx_reviews_doc_id ON reviews (doc_id, document_version);
CREATE INDEX idx_reviews_status ON reviews (status);
CREATE INDEX idx_reviews_created_at ON reviews (created_at DESC);

CREATE TRIGGER trg_reviews_updated_at
  BEFORE UPDATE ON reviews
  FOR EACH ROW EXECUTE FUNCTION set_updated_at();


-- =====================================================================
-- 5. findings — per-review AI agent / rule engine results
-- =====================================================================
CREATE TABLE findings (
  finding_id  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  org_id      UUID NOT NULL REFERENCES organizations(org_id) ON DELETE CASCADE,
  review_id   UUID NOT NULL REFERENCES reviews(review_id) ON DELETE CASCADE,

  finding_source  VARCHAR(50) NOT NULL,
  agent_name      VARCHAR(100) NULL,
  rule_id         VARCHAR(100) NULL,

  category    VARCHAR(100) NOT NULL,
  title       VARCHAR(255) NOT NULL,
  description TEXT NOT NULL,
  evidence    TEXT NULL,
  section_ref VARCHAR(255) NULL,

  severity        VARCHAR(50) NOT NULL,
  confidence      DECIMAL(5,2) NOT NULL DEFAULT 100.00,
  business_impact VARCHAR(50) NULL,

  recommendation TEXT NOT NULL,
  suggested_text TEXT NULL,

  status              VARCHAR(50) NOT NULL DEFAULT 'open',
  assigned_to_user_id UUID NULL REFERENCES users(user_id) ON DELETE SET NULL,
  notes               JSONB NULL,

  created_at  TIMESTAMPTZ NOT NULL DEFAULT clock_timestamp(),
  updated_at  TIMESTAMPTZ NOT NULL DEFAULT clock_timestamp(),
  deleted_at  TIMESTAMPTZ NULL,

  CONSTRAINT ck_findings_source CHECK (finding_source IN ('agent', 'rule')),
  -- Exactly one of agent_name / rule_id, matching finding_source.
  CONSTRAINT ck_findings_source_origin CHECK (
    (finding_source = 'agent' AND agent_name IS NOT NULL AND rule_id IS NULL) OR
    (finding_source = 'rule'  AND rule_id IS NOT NULL AND agent_name IS NULL)
  ),
  CONSTRAINT ck_findings_severity
    CHECK (severity IN ('critical', 'major', 'medium', 'low', 'info')),
  CONSTRAINT ck_findings_confidence_range CHECK (confidence BETWEEN 0 AND 100),
  CONSTRAINT ck_findings_business_impact
    CHECK (business_impact IS NULL OR business_impact IN ('high', 'medium', 'low')),
  CONSTRAINT ck_findings_status
    CHECK (status IN ('open', 'acknowledged', 'resolved', 'dismissed'))
);
COMMENT ON TABLE findings IS
  'Individual findings attached to a review — either an AI agent observation or a rule-engine hit.';

CREATE INDEX idx_findings_org_active ON findings (org_id) WHERE deleted_at IS NULL;
CREATE INDEX idx_findings_review_id ON findings (review_id);
CREATE INDEX idx_findings_severity ON findings (severity);
CREATE INDEX idx_findings_status ON findings (status);
CREATE INDEX idx_findings_agent_name ON findings (agent_name);

CREATE TRIGGER trg_findings_updated_at
  BEFORE UPDATE ON findings
  FOR EACH ROW EXECUTE FUNCTION set_updated_at();


-- =====================================================================
-- 6. audit_logs — immutable action history (no soft delete: never mutated)
-- =====================================================================
CREATE TABLE audit_logs (
  log_id        BIGSERIAL PRIMARY KEY,
  org_id        UUID NOT NULL REFERENCES organizations(org_id) ON DELETE CASCADE,
  user_id       UUID NULL REFERENCES users(user_id) ON DELETE SET NULL,

  action        VARCHAR(100) NOT NULL,
  resource_type VARCHAR(50) NOT NULL,
  resource_id   UUID NULL,

  details     JSONB NOT NULL DEFAULT '{}'::jsonb,
  ip_address  VARCHAR(45) NULL,
  user_agent  VARCHAR(500) NULL,

  created_at  TIMESTAMPTZ NOT NULL DEFAULT clock_timestamp(),

  -- action is an open, ever-growing event vocabulary (new event types are
  -- added continuously) so it's intentionally not CHECK-constrained;
  -- resource_type is a small, genuinely closed set.
  CONSTRAINT ck_audit_logs_resource_type
    CHECK (resource_type IN ('document', 'review', 'finding', 'user', 'organization'))
);
COMMENT ON TABLE audit_logs IS
  'Immutable audit trail. Rows are append-only — never updated or deleted by the application.';

CREATE INDEX idx_audit_logs_org_created ON audit_logs (org_id, created_at DESC);
CREATE INDEX idx_audit_logs_user_created ON audit_logs (user_id, created_at DESC);
CREATE INDEX idx_audit_logs_resource ON audit_logs (resource_type, resource_id);
CREATE INDEX idx_audit_logs_action ON audit_logs (action);
