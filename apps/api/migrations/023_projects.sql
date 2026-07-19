-- 023_projects.sql
-- Phase A of Document Lifecycle & Multi-Project plan: promotes
-- documents.project_name (free text) to a first-class Project entity.
-- project_name is kept (not dropped) so existing rows stay readable until
-- the data migration backfills project_id; see
-- docs/phases/summaries/PROJECT_MIGRATION_REPORT.md for the mapping.

CREATE TABLE projects (
    project_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    org_id UUID NOT NULL REFERENCES organizations(org_id) ON DELETE CASCADE,
    name VARCHAR(255) NOT NULL,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT uq_projects_org_name UNIQUE (org_id, name)
);

ALTER TABLE documents ADD COLUMN project_id UUID REFERENCES projects(project_id) ON DELETE SET NULL;
