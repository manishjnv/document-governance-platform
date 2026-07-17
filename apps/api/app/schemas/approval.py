"""Approval workflow request/response schemas (T-2066)."""

from datetime import datetime
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class ApprovalCreateRequest(BaseModel):
    """Request approval from a list of users — one pending Approval row per approver."""

    approver_ids: list[UUID] = Field(..., min_length=1)


class ApprovalDecisionRequest(BaseModel):
    """An approver's decision on their own approval row."""

    status: str = Field(..., pattern="^(approved|rejected)$")
    notes: Optional[str] = None


class ApprovalRead(BaseModel):
    """Approval as returned by the API."""

    model_config = ConfigDict(from_attributes=True)

    approval_id: UUID
    org_id: UUID
    review_id: UUID
    approver_id: UUID
    status: str
    notes: Optional[str] = None
    created_at: datetime
    updated_at: datetime
