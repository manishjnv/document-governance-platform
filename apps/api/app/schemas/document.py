"""Document upload and management schemas.

NOTE: The classes below (DocumentUploadRequest, DocumentMetadata, etc.) predate
the finalized UUID-based schema in 3_DATABASE_SCHEMA.md and use int doc_id/org_id
and a float version — inconsistent with the DB (UUID PKs, integer version). The
DocumentCreate/DocumentUpdate/DocumentRead classes at the bottom of this file
match the current DB schema. Left both in place rather than deleting existing
work; reconciling/removing the older set is a separate follow-up, not silently
done here.
"""

from datetime import datetime
from typing import Any, Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.models.enums import DocumentType, FileType, StorageStatus


class DocumentUploadRequest(BaseModel):
    """Document upload request."""

    filename: str = Field(..., description="Original filename")
    org_id: int = Field(..., description="Organization ID")


class DocumentMetadata(BaseModel):
    """Document metadata (file info, parsed content)."""

    doc_id: int
    org_id: int
    user_id: int
    filename: str
    file_size: int
    file_type: str  # pdf | docx
    s3_path: str
    version: float
    status: str  # pending | parsing | parsed | error
    detected_type: Optional[str] = None  # SOW | Proposal | etc.
    page_count: Optional[int] = None
    uploaded_at: datetime
    updated_at: datetime
    parsed_text: Optional[str] = None  # Raw text (truncated for response)
    parsed_sections: Optional[dict] = None  # Detected sections


class DocumentListResponse(BaseModel):
    """Document list response."""

    doc_id: int
    filename: str
    file_type: str
    uploaded_at: datetime
    status: str
    version: float
    detected_type: Optional[str] = None
    review_status: Optional[str] = None  # pending | in_progress | completed


class DocumentDetailResponse(DocumentMetadata):
    """Full document detail response."""

    pass


class DocumentDeleteRequest(BaseModel):
    """Document delete request."""

    reason: Optional[str] = Field(None, description="Reason for deletion")


class DocumentVersionResponse(BaseModel):
    """Document version info."""

    version: float
    uploaded_at: datetime
    uploaded_by: int
    uploaded_by_email: str
    file_size: int
    status: str


class DocumentSearchRequest(BaseModel):
    """Search documents."""

    org_id: int
    query: Optional[str] = Field(None, description="Search query (filename, content)")
    status: Optional[str] = None  # pending | parsed | error
    doc_type: Optional[str] = None  # SOW | Proposal | etc.
    uploaded_after: Optional[datetime] = None
    uploaded_before: Optional[datetime] = None
    limit: int = Field(50, ge=1, le=1000)
    offset: int = Field(0, ge=0)


class DocumentSearchResponse(BaseModel):
    """Search results."""

    total: int
    limit: int
    offset: int
    results: list[DocumentListResponse]


class ParsedSection(BaseModel):
    """Parsed document section."""

    heading: str
    level: int  # 1 = H1, 2 = H2, etc.
    content: str
    page_number: Optional[int] = None
    start_offset: int
    end_offset: int


class DocumentParsingResult(BaseModel):
    """Result from document parsing."""

    doc_id: int
    status: str  # success | partial | failed
    page_count: int
    total_tokens: int
    sections: list[ParsedSection]
    error_message: Optional[str] = None
    parse_duration_seconds: float


# ---------------------------------------------------------------------------
# Current schema (matches 3_DATABASE_SCHEMA.md / migrations/001_init_schema.sql)
# ---------------------------------------------------------------------------


class DocumentCreate(BaseModel):
    """Metadata accompanying a document upload (the file itself is multipart)."""

    org_id: UUID
    original_filename: str = Field(..., min_length=1, max_length=255)
    file_size_bytes: int = Field(..., gt=0)
    file_type: FileType
    # Set when re-uploading a new version of an existing document; omitted on first upload.
    document_group_id: Optional[UUID] = None


class DocumentUpdate(BaseModel):
    """Fields updatable after upload (post-parsing enrichment, archival, etc.)."""

    parsed_text: Optional[str] = None
    parsed_sections: Optional[Any] = None
    document_type: Optional[DocumentType] = None
    page_count: Optional[int] = Field(None, ge=0)
    storage_status: Optional[StorageStatus] = None


class DocumentRead(BaseModel):
    """Document as returned by the API."""

    model_config = ConfigDict(from_attributes=True)

    doc_id: UUID
    document_group_id: UUID
    org_id: UUID
    uploaded_by_user_id: Optional[UUID] = None
    filename: str
    original_filename: str
    project_name: Optional[str] = None
    project_id: Optional[UUID] = None
    file_size_bytes: int
    file_type: FileType
    version: int
    document_type: Optional[DocumentType] = None
    page_count: Optional[int] = None
    language: str
    storage_status: StorageStatus
    created_at: datetime
    updated_at: datetime
    latest_overall_score: Optional[float] = None
    latest_completeness_score: Optional[float] = None


class DocumentDetail(DocumentRead):
    """Single-document fetch -- includes parsed content for the side-by-side
    document viewer on the results page. Deliberately NOT part of
    DocumentRead/list_documents: that response is paginated and would bloat
    every row with full document text for no reason."""

    parsed_sections: Optional[Any] = None
