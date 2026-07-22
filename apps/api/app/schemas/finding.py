"""Finding request/response schemas."""

from datetime import datetime
from decimal import Decimal
from typing import Any, Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.models.enums import BusinessImpact, FindingSource, FindingStatus, Severity


class FindingCreate(BaseModel):
    """A single finding produced by an AI agent or the rule engine."""

    org_id: UUID
    review_id: UUID
    finding_source: FindingSource
    agent_name: Optional[str] = Field(None, max_length=100)
    rule_id: Optional[str] = Field(None, max_length=100)
    category: str = Field(..., min_length=1, max_length=100)
    title: str = Field(..., min_length=1, max_length=255)
    description: str = Field(..., min_length=1)
    evidence: Optional[str] = None
    section_ref: Optional[str] = Field(None, max_length=255)
    evidence_type: Optional[str] = Field(
        None, pattern="^(location|missing_section|cross_document|conflict|reference)$"
    )
    page: Optional[int] = None
    line_start: Optional[int] = None
    line_end: Optional[int] = None
    anchor_before: Optional[str] = Field(None, max_length=255)
    anchor_after: Optional[str] = Field(None, max_length=255)
    matched_text: Optional[str] = None
    severity: Severity
    confidence: Decimal = Field(Decimal("100.00"), ge=0, le=100)
    business_impact: Optional[BusinessImpact] = None
    recommendation: str = Field(..., min_length=1)
    suggested_text: Optional[str] = None

    @model_validator(mode="after")
    def _source_matches_origin(self) -> "FindingCreate":
        # Mirrors the DB's ck_findings_source_origin CHECK — fail fast client-side
        # instead of round-tripping to the DB for a mistake the API layer can catch.
        if self.finding_source == FindingSource.AGENT:
            if not self.agent_name or self.rule_id:
                raise ValueError("agent findings require agent_name and forbid rule_id")
        elif self.finding_source == FindingSource.RULE:
            if not self.rule_id or self.agent_name:
                raise ValueError("rule findings require rule_id and forbid agent_name")
        return self


class FindingUpdate(BaseModel):
    """Reviewer workflow actions on an existing finding."""

    status: Optional[FindingStatus] = None
    assigned_to_user_id: Optional[UUID] = None
    notes: Optional[Any] = None


class FindingRead(BaseModel):
    """Finding as returned by the API."""

    model_config = ConfigDict(from_attributes=True)

    finding_id: UUID
    org_id: UUID
    review_id: UUID
    finding_source: FindingSource
    agent_name: Optional[str] = None
    rule_id: Optional[str] = None
    category: str
    title: str
    description: str
    evidence: Optional[str] = None
    section_ref: Optional[str] = None
    evidence_type: Optional[str] = None
    page: Optional[int] = None
    line_start: Optional[int] = None
    line_end: Optional[int] = None
    anchor_before: Optional[str] = None
    anchor_after: Optional[str] = None
    matched_text: Optional[str] = None
    severity: Severity
    confidence: Decimal
    business_impact: Optional[BusinessImpact] = None
    recommendation: str
    suggested_text: Optional[str] = None
    status: FindingStatus
    assigned_to_user_id: Optional[UUID] = None
    notes: Optional[Any] = None
    created_at: datetime
    updated_at: datetime
