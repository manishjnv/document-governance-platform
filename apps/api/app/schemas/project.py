"""Project schemas (Phase A of Document Lifecycle plan)."""

from datetime import datetime
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class ProjectCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)


class ProjectRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    project_id: UUID
    org_id: UUID
    name: str
    created_at: datetime
    document_count: int = 0
    average_latest_score: Optional[float] = None
    open_critical_count: int = 0
