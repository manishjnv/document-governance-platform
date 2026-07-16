"""Audit log schemas. Read-only from the API's perspective — rows are written
internally by services/repositories on every tracked action, never via a
client-facing create endpoint."""

from datetime import datetime
from typing import Any, Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict

from app.models.enums import AuditResourceType


class AuditLogRead(BaseModel):
    """Audit log entry as returned by the API."""

    model_config = ConfigDict(from_attributes=True)

    log_id: int
    org_id: UUID
    user_id: Optional[UUID] = None
    action: str
    resource_type: AuditResourceType
    resource_id: Optional[UUID] = None
    details: Any
    ip_address: Optional[str] = None
    user_agent: Optional[str] = None
    created_at: datetime
