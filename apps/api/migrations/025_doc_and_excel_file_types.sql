-- 025_doc_and_excel_file_types.sql
-- Widens documents.file_type to accept legacy .doc (parsed via antiword),
-- .xlsx (openpyxl), .xls (xlrd), and .csv (stdlib) alongside pdf/docx.

ALTER TABLE documents DROP CONSTRAINT ck_documents_file_type;
ALTER TABLE documents ADD CONSTRAINT ck_documents_file_type
    CHECK (file_type IN ('pdf', 'docx', 'doc', 'xlsx', 'xls', 'csv'));
