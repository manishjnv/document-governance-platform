"""Review request/response schemas."""

from datetime import datetime
from decimal import Decimal
from typing import Any, Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.models.enums import ReviewStatus

_Score = Optional[Decimal]  # 0-100, matches the DB's ck_reviews_scores_range CHECK
_score_field = Field(None, ge=0, le=100)


class ReviewCreate(BaseModel):
    """Trigger a new review run for a document."""

    org_id: UUID
    doc_id: UUID
    document_version: int = Field(1, gt=0)


class ReviewRead(BaseModel):
    """Review as returned by the API."""

    model_config = ConfigDict(from_attributes=True)

    review_id: UUID
    org_id: UUID
    doc_id: UUID
    document_version: int
    status: ReviewStatus
    overall_score: _Score = _score_field
    risk_score: _Score = _score_field
    score_completeness: _Score = _score_field
    score_clarity: _Score = _score_field
    score_consistency: _Score = _score_field
    score_commercial: _Score = _score_field
    score_delivery: _Score = _score_field
    score_operations: _Score = _score_field
    score_security: _Score = _score_field
    executive_summary: Optional[str] = None
    critical_finding_count: int = 0
    major_finding_count: int = 0
    medium_finding_count: int = 0
    low_finding_count: int = 0
    info_finding_count: int = 0
    started_at: datetime
    completed_at: Optional[datetime] = None
    processing_time_seconds: Optional[int] = None
    error_message: Optional[str] = None
    error_details: Optional[Any] = None
    created_at: datetime
    updated_at: datetime
