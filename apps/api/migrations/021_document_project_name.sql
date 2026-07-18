-- 021_document_project_name.sql
-- Adds an optional, user-supplied project name to documents so the
-- dashboard table can show a human-meaningful grouping label instead of
-- just the raw filename.

ALTER TABLE documents ADD COLUMN project_name VARCHAR(255);
