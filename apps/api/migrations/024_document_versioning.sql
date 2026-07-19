-- 024_document_versioning.sql
-- Phase B of Document Lifecycle & Multi-Project plan: similarity-suggestion
-- storage (dismissible, persists beyond a one-time upload toast) + a
-- per-org tunable similarity threshold (mirrors the org_scoring_weights /
-- org_risk_weights override pattern in app/admin/customization.py, but as
-- a single scalar column since there's only one value to tune here, not a
-- keyed set).

ALTER TABLE organizations
    ADD COLUMN similarity_suggestion_threshold NUMERIC(3, 2) NOT NULL DEFAULT 0.55;

CREATE TABLE document_link_suggestions (
    suggestion_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    org_id UUID NOT NULL REFERENCES organizations(org_id) ON DELETE CASCADE,
    doc_id UUID NOT NULL REFERENCES documents(doc_id) ON DELETE CASCADE,
    suggested_doc_id UUID NOT NULL REFERENCES documents(doc_id) ON DELETE CASCADE,
    similarity_score NUMERIC(5, 4) NOT NULL,
    status VARCHAR(20) NOT NULL DEFAULT 'pending'
        CHECK (status IN ('pending', 'accepted', 'dismissed')),
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT uq_document_link_suggestions_doc UNIQUE (doc_id)
);
