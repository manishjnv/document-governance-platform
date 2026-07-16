"""Document upload and management schemas."""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


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
