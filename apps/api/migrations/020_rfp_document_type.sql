-- 020_rfp_document_type.sql
-- Add RFP to the allowed document_type values (docs/planning/4_AI_AGENT_SPECS.md
-- "Document Type Coverage: SOW vs RFP" -- pre-launch core review-accuracy work).

ALTER TABLE documents DROP CONSTRAINT ck_documents_document_type;

ALTER TABLE documents ADD CONSTRAINT ck_documents_document_type
  CHECK (document_type IS NULL OR document_type IN ('SOW', 'Proposal', 'RFP', 'Other'));
