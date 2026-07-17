# Database Schema Design - Enterprise SOW Review Platform

**Database:** PostgreSQL 16+
**Pattern:** Normalized relational schema with multi-tenancy (org_id isolation)
**Versioning:** Alembic migrations

---

## Schema Overview

```
organizations (tenant container)
├── users (per-org users)
├── documents (uploaded SOWs)
├── reviews (review executions)
├── findings (agent findings + rule results)
├── rules (rule definitions)
└── audit_logs (all changes)
```

---

## Table Definitions

### 1. organizations

Tenant/Organization container.

```sql
CREATE TABLE organizations (
  org_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  name VARCHAR(255) NOT NULL,
  subscription_tier VARCHAR(50) DEFAULT 'free', -- free | pro | enterprise
  created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
  deleted_at TIMESTAMP NULL, -- soft delete
  
  UNIQUE(name),
  INDEX idx_deleted_at ON (deleted_at)
);
```

**Notes:**
- `subscription_tier` for future billing/feature gating
- Soft delete via `deleted_at` (queries filter `WHERE deleted_at IS NULL`)
- Single name uniqueness (can be relaxed later for multi-region)

---

### 2. users

Users within organizations.

```sql
CREATE TABLE users (
  user_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  org_id UUID NOT NULL REFERENCES organizations(org_id) ON DELETE CASCADE,
  email VARCHAR(255) NOT NULL,
  password_hash VARCHAR(255) NULL, -- bcrypt hash, NULL if SSO only
  full_name VARCHAR(255),
  role VARCHAR(50) NOT NULL DEFAULT 'viewer', -- admin | reviewer | viewer
  is_active BOOLEAN DEFAULT TRUE,
  last_login TIMESTAMP NULL,
  created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
  deleted_at TIMESTAMP NULL,
  
  UNIQUE(org_id, email),
  FOREIGN KEY (org_id) REFERENCES organizations(org_id) ON DELETE CASCADE,
  INDEX idx_org_deleted ON (org_id, deleted_at)
);
```

**Notes:**
- Composite unique (org_id, email) — same email can exist in different orgs
- `role` determines document access (admin/reviewer can see all, viewer only their own)
- `password_hash` NULL if using Azure AD/Entra ID only
- Soft delete per org

---

### 3. documents

Uploaded SOW files.

```sql
CREATE TABLE documents (
  doc_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  org_id UUID NOT NULL REFERENCES organizations(org_id) ON DELETE CASCADE,
  uploaded_by_user_id UUID NOT NULL REFERENCES users(user_id) ON DELETE SET NULL,
  filename VARCHAR(255) NOT NULL,
  original_filename VARCHAR(255) NOT NULL, -- user's uploaded filename
  file_size_bytes BIGINT NOT NULL,
  file_type VARCHAR(20) NOT NULL, -- pdf | docx
  s3_path VARCHAR(512) NOT NULL, -- org/{org_id}/doc/{doc_id}/v{version}.pdf
  s3_etag VARCHAR(100) NULL, -- for version control
  version INT DEFAULT 1,
  parsed_text TEXT NULL, -- full extracted text (searchable)
  parsed_sections JSONB NULL, -- detected sections: [{title, content, page}]
  document_type VARCHAR(50) NULL, -- detected type: 'SOW' | 'Proposal' | 'Other'
  page_count INT NULL,
  language VARCHAR(10) DEFAULT 'en',
  storage_status VARCHAR(50) DEFAULT 'uploaded', -- uploaded | archived | deleted_from_s3
  created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
  deleted_at TIMESTAMP NULL,
  
  FOREIGN KEY (org_id) REFERENCES organizations(org_id) ON DELETE CASCADE,
  FOREIGN KEY (uploaded_by_user_id) REFERENCES users(user_id) ON DELETE SET NULL,
  INDEX idx_org_deleted ON (org_id, deleted_at),
  INDEX idx_uploaded_by ON (uploaded_by_user_id),
  INDEX idx_doc_type ON (document_type),
  INDEX idx_created_at ON (created_at DESC),
  UNIQUE(org_id, s3_path, version)
);
```

**Notes:**
- `s3_path` is the S3 key (org-scoped)
- `parsed_text` is indexed for full-text search (can upgrade to Elasticsearch later)
- `parsed_sections` is JSONB for flexible structure (sections with title, content, page)
- `document_type` is auto-detected during upload (SOW vs other)
- `storage_status` for soft deletes from S3 (separate from DB soft delete)
- One row per document version (version increments on re-upload)

---

### 4. reviews

Review execution records (one per document analysis).

```sql
CREATE TABLE reviews (
  review_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  org_id UUID NOT NULL REFERENCES organizations(org_id) ON DELETE CASCADE,
  doc_id UUID NOT NULL REFERENCES documents(doc_id) ON DELETE CASCADE,
  triggered_by_user_id UUID NOT NULL REFERENCES users(user_id) ON DELETE SET NULL,
  status VARCHAR(50) NOT NULL DEFAULT 'pending', -- pending | running | completed | failed
  overall_score DECIMAL(5,2) NULL, -- 0.00 to 100.00
  risk_score DECIMAL(5,2) NULL, -- 0.00 to 100.00
  
  -- Category scores (0-100)
  score_completeness DECIMAL(5,2) NULL,
  score_clarity DECIMAL(5,2) NULL,
  score_consistency DECIMAL(5,2) NULL,
  score_commercial DECIMAL(5,2) NULL,
  score_delivery DECIMAL(5,2) NULL,
  score_operations DECIMAL(5,2) NULL,
  score_security DECIMAL(5,2) NULL,
  
  -- Metadata
  executive_summary TEXT NULL,
  critical_finding_count INT DEFAULT 0,
  major_finding_count INT DEFAULT 0,
  medium_finding_count INT DEFAULT 0,
  low_finding_count INT DEFAULT 0,
  info_finding_count INT DEFAULT 0,
  
  -- Processing times
  started_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
  completed_at TIMESTAMP NULL,
  processing_time_seconds INT NULL,
  
  -- Error handling
  error_message TEXT NULL,
  error_details JSONB NULL,
  
  created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
  deleted_at TIMESTAMP NULL,
  
  FOREIGN KEY (org_id) REFERENCES organizations(org_id) ON DELETE CASCADE,
  FOREIGN KEY (doc_id) REFERENCES documents(doc_id) ON DELETE CASCADE,
  FOREIGN KEY (triggered_by_user_id) REFERENCES users(user_id) ON DELETE SET NULL,
  INDEX idx_org_deleted ON (org_id, deleted_at),
  INDEX idx_doc_id ON (doc_id),
  INDEX idx_status ON (status),
  INDEX idx_created_at ON (created_at DESC),
  UNIQUE(doc_id, version) -- one review per document version (add version FK later)
);
```

**Notes:**
- `status` tracks review lifecycle (polling on client)
- Scores are DECIMAL(5,2) for accounting precision
- Finding counts are denormalized (could also aggregate from findings table)
- `processing_time_seconds` for performance metrics
- `error_details` is JSONB for rich error context
- One review per document (add version tracking later if re-reviews needed)

---

### 5. findings

AI agent findings + rule engine results.

```sql
CREATE TABLE findings (
  finding_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  org_id UUID NOT NULL REFERENCES organizations(org_id) ON DELETE CASCADE,
  review_id UUID NOT NULL REFERENCES reviews(review_id) ON DELETE CASCADE,
  
  -- Source
  finding_source VARCHAR(50) NOT NULL, -- agent | rule
  agent_name VARCHAR(100) NULL, -- scope_reviewer | delivery_reviewer | commercial_reviewer | security_reviewer | pmo_reviewer
  rule_id VARCHAR(100) NULL, -- sow-001, sow-002, etc. (if from rule)
  
  -- Content
  category VARCHAR(100) NOT NULL, -- deliverables, timeline, pricing, security, etc.
  title VARCHAR(255) NOT NULL, -- human-readable issue title
  description TEXT NOT NULL, -- detailed explanation
  evidence TEXT NULL, -- quoted text from document
  section_ref VARCHAR(255) NULL, -- detected section name (e.g., "Scope", "Timeline")
  
  -- Scoring
  severity VARCHAR(50) NOT NULL, -- critical | major | medium | low | info
  confidence DECIMAL(5,2) NOT NULL DEFAULT 100.00, -- 0-100, from AI agent
  business_impact VARCHAR(50) NULL, -- high | medium | low
  
  -- Remediation
  recommendation TEXT NOT NULL, -- suggested fix
  suggested_text TEXT NULL, -- if applicable, suggested wording
  
  -- Tracking
  status VARCHAR(50) DEFAULT 'open', -- open | acknowledged | resolved | dismissed
  assigned_to_user_id UUID NULL REFERENCES users(user_id) ON DELETE SET NULL,
  notes JSONB NULL, -- rich notes field for additional context
  
  created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
  deleted_at TIMESTAMP NULL,
  
  FOREIGN KEY (org_id) REFERENCES organizations(org_id) ON DELETE CASCADE,
  FOREIGN KEY (review_id) REFERENCES reviews(review_id) ON DELETE CASCADE,
  INDEX idx_org_deleted ON (org_id, deleted_at),
  INDEX idx_review_id ON (review_id),
  INDEX idx_severity ON (severity),
  INDEX idx_status ON (status),
  INDEX idx_agent ON (agent_name)
);
```

**Notes:**
- `finding_source` distinguishes AI agent findings from rule engine results
- `agent_name` allows filtering by agent (e.g., "show all scope reviewer findings")
- `confidence` is from the AI agent (0-100), helps sort by quality
- `severity` is derived from confidence + rule criticality
- `evidence` is the quoted text (for showing user the exact concern)
- `suggested_text` provides ready-to-use fixes
- `status` allows users to acknowledge/dismiss findings (Phase 2: workflow)
- `assigned_to_user_id` for future assignment workflow

---

### 6. rules

Rule definitions (configuration-driven rule engine).

```sql
CREATE TABLE rules (
  rule_id VARCHAR(100) PRIMARY KEY, -- sow-001, sow-002, etc.
  org_id UUID NULL REFERENCES organizations(org_id) ON DELETE CASCADE, -- NULL = global, non-null = org-specific (Phase 2)
  document_type VARCHAR(50) NOT NULL, -- SOW, Proposal, etc.
  rule_name VARCHAR(255) NOT NULL,
  description TEXT NOT NULL,
  
  -- Rule definition
  check_type VARCHAR(50) NOT NULL, -- section_presence | keyword_present | section_word_count | regex_match | semantic
  rule_config JSONB NOT NULL, -- {"required_sections": [...]} or {"keywords": [...]} etc.
  
  -- Severity
  severity VARCHAR(50) NOT NULL, -- critical | major | medium | low
  
  -- Metadata
  is_enabled BOOLEAN DEFAULT TRUE,
  created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
  
  INDEX idx_doc_type ON (document_type),
  INDEX idx_org_id ON (org_id)
);
```

**Notes:**
- `rule_id` is human-readable (sow-001, sow-002)
- `org_id` NULL means rule is global/default; non-NULL = org-specific override (Phase 2)
- `rule_config` is JSONB for flexible rule configuration without schema changes
- `check_type` determines how rule is evaluated (section_presence, keyword search, etc.)
- No soft delete needed (update `is_enabled` instead)

---

### 7. audit_logs

Immutable audit trail.

```sql
CREATE TABLE audit_logs (
  log_id BIGSERIAL PRIMARY KEY,
  org_id UUID NOT NULL REFERENCES organizations(org_id) ON DELETE CASCADE,
  user_id UUID NULL REFERENCES users(user_id) ON DELETE SET NULL,
  
  -- Action
  action VARCHAR(100) NOT NULL, -- document_uploaded | review_started | review_completed | finding_dismissed | etc.
  resource_type VARCHAR(50) NOT NULL, -- document | review | finding
  resource_id UUID NULL, -- references the affected resource
  
  -- Details
  details JSONB NOT NULL, -- flexible: {old_value, new_value, reason, etc.}
  ip_address VARCHAR(45) NULL,
  user_agent VARCHAR(500) NULL,
  
  created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
  
  FOREIGN KEY (org_id) REFERENCES organizations(org_id) ON DELETE CASCADE,
  INDEX idx_org_created ON (org_id, created_at DESC),
  INDEX idx_user_created ON (user_id, created_at DESC),
  INDEX idx_resource ON (resource_type, resource_id),
  INDEX idx_action ON (action)
);
```

**Notes:**
- No soft deletes (immutable log)
- `BIGSERIAL` for efficient sorting + paging
- `details` is JSONB for flexible audit information
- Indexes optimized for "who did what when" queries
- `user_id` NULL for system actions

---

## Indexes Summary

| Table | Column(s) | Reason |
|-------|-----------|--------|
| documents | (org_id, deleted_at) | Filter by org + soft delete |
| documents | (document_type) | Filter by doc type in list view |
| documents | (created_at DESC) | Sort by recency |
| reviews | (org_id, deleted_at) | Filter by org + soft delete |
| reviews | (doc_id) | Foreign key lookup |
| reviews | (status) | Poll for pending/running reviews |
| reviews | (created_at DESC) | Sort by recency |
| findings | (org_id, deleted_at) | Filter by org + soft delete |
| findings | (review_id) | Aggregate findings per review |
| findings | (severity) | Filter by severity in UI |
| findings | (status) | Filter by open/resolved |
| findings | (agent_name) | Group findings by agent |
| rules | (document_type) | Load rules for doc type |
| rules | (org_id) | Load org-specific rules (Phase 2) |
| audit_logs | (org_id, created_at DESC) | Audit trail by org |
| audit_logs | (resource_type, resource_id) | Find all changes to a resource |
| audit_logs | (action) | Filter by action type |

---

## Constraints & Relationships

| Constraint | Reason |
|-----------|--------|
| UNIQUE(org_id, email) in users | Prevent duplicate emails per org |
| UNIQUE(org_id, s3_path, version) in documents | Prevent duplicate versions in S3 |
| UNIQUE(doc_id, version) in reviews | One review per document version |
| ON DELETE CASCADE for org_id | If org deleted, cascade to all children |
| ON DELETE SET NULL for user_id | If user deleted, preserve audit trail |

---

## Growth & Partitioning Strategy

**Phase 1 (MVP):**
- Single table (no partitioning)
- Indexes on hot columns
- Expected: <100K documents, <1M findings

**Phase 2 (Scaling):**
- Partition findings by month (findings_2024_01, findings_2024_02, etc.)
- Partition audit_logs by quarter
- Add materialized views for dashboards

**Phase 3+ (Enterprise):**
- Read replicas for reporting queries
- Sharding by org_id if multi-region

---

## Data Retention Policy

**Phase 1 (Default):**
- Keep all data indefinitely
- Soft deletes via `deleted_at`
- Hard deletes via GDPR/retention policy (manual)

**Phase 2:**
- Configurable retention per org
- Auto-archive old documents
- Compliance (90-day audit log retention)

---

## Migrations Strategy

Use Alembic to version schema changes:

```bash
alembic init alembic                          # Init
alembic revision -m "Create organizations"    # New migration
alembic upgrade head                          # Apply
alembic downgrade -1                          # Rollback last
```

**Naming Convention:**
- `001_init_schema.sql` (all Phase 1 tables)
- `002_add_parsed_sections_to_documents.sql` (future)
- `003_add_org_specific_rules.sql` (Phase 2)

---

## Soft Delete Pattern

Queries must include `WHERE deleted_at IS NULL`:

```python
# Bad (retrieves deleted records)
reviews = db.query(Review).filter(Review.doc_id == doc_id).all()

# Good (excludes deleted)
reviews = db.query(Review).filter(
  Review.doc_id == doc_id,
  Review.deleted_at.is_(None)
).all()
```

Implement in base repository class to avoid repeating this filter everywhere.

---

## Sample Queries

### Dashboard: Average quality score per org (7-day trend)

```sql
SELECT 
  DATE_TRUNC('day', r.created_at) as day,
  AVG(r.overall_score) as avg_score
FROM reviews r
WHERE r.org_id = 'some-org-id'
  AND r.deleted_at IS NULL
  AND r.created_at >= NOW() - INTERVAL '7 days'
GROUP BY DATE_TRUNC('day', r.created_at)
ORDER BY day DESC;
```

### Find all critical findings for a review

```sql
SELECT f.*, d.filename
FROM findings f
JOIN reviews r ON f.review_id = r.review_id
JOIN documents d ON r.doc_id = d.doc_id
WHERE f.org_id = 'some-org-id'
  AND f.severity = 'critical'
  AND f.deleted_at IS NULL
ORDER BY f.created_at DESC;
```

### Audit: All actions by a user in the last 30 days

```sql
SELECT * FROM audit_logs
WHERE org_id = 'some-org-id'
  AND user_id = 'some-user-id'
  AND created_at >= NOW() - INTERVAL '30 days'
ORDER BY created_at DESC;
```

### Find most common issues across all org reviews

```sql
SELECT 
  f.category,
  f.severity,
  COUNT(*) as frequency
FROM findings f
JOIN reviews r ON f.review_id = r.review_id
WHERE r.org_id = 'some-org-id'
  AND f.deleted_at IS NULL
GROUP BY f.category, f.severity
ORDER BY frequency DESC
LIMIT 10;
```

---

## Backup & Recovery

**Daily Automated Backups:**
```bash
pg_dump -Fc edgp_db > backup_$(date +%Y%m%d).dump
gsutil cp backup_*.dump gs://edgp-backups/  # Upload to GCS/S3
```

**Restore:**
```bash
pg_restore -d edgp_db backup_20240101.dump
```

---

## Testing the Schema

Create fixtures for testing:

```python
@pytest.fixture
def org():
    return Organization(name="Test Org", subscription_tier="pro")

@pytest.fixture
def user(org):
    return User(org_id=org.org_id, email="test@example.com", role="reviewer")

@pytest.fixture
def document(org, user):
    return Document(
        org_id=org.org_id,
        uploaded_by_user_id=user.user_id,
        filename="sample_sow.pdf",
        s3_path="org/123/doc/456/v1.pdf"
    )

@pytest.fixture
def review(org, document, user):
    return Review(
        org_id=org.org_id,
        doc_id=document.doc_id,
        triggered_by_user_id=user.user_id,
        status="completed",
        overall_score=85.5
    )

@pytest.fixture
def finding(org, review):
    return Finding(
        org_id=org.org_id,
        review_id=review.review_id,
        finding_source="agent",
        agent_name="scope_reviewer",
        severity="major",
        title="Acceptance criteria not defined"
    )
```

Use these fixtures in tests to verify schema integrity.

---

## Performance Considerations

| Query | Optimization |
|-------|--------------|
| List documents by org | Index (org_id, deleted_at) |
| Poll for review status | Index (status), update only changed fields |
| Aggregate findings by severity | Index (severity), use materialized view (Phase 2) |
| Audit trail by user | Index (user_id, created_at DESC) |
| Full-text search in parsed_text | Use PostgreSQL GIN index, upgrade to Elasticsearch (Phase 2) |

---

## Security Considerations

1. **Row-Level Security (RLS):** Implement in Phase 2
   ```sql
   ALTER TABLE documents ENABLE ROW LEVEL SECURITY;
   CREATE POLICY org_isolation ON documents
     USING (org_id = current_setting('app.current_org_id')::uuid);
   ```

2. **Sensitive Data:** Don't store passwords in audit logs
   - Filter sensitive fields before logging

3. **Encryption:** 
   - Database-level encryption at rest (AWS RDS encryption, GCP Cloud SQL encryption)
   - Column-level encryption for PII if needed (Phase 2)

4. **Access Control:** Implement in application layer
   - API shouldn't trust user input for org_id
   - Extract from JWT token

