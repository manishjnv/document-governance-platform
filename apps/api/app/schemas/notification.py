"""Notification request/response schemas (T-2076, T-2080)."""

from datetime import datetime
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class NotificationRead(BaseModel):
    """Notification as returned by the API."""

    model_config = ConfigDict(from_attributes=True)

    notif_id: UUID
    org_id: UUID
    user_id: UUID
    type: str
    content: str
    read: bool
    created_at: datetime


class NotificationPreferenceRead(BaseModel):
    """Notification preferences as returned by the API."""

    model_config = ConfigDict(from_attributes=True)

    user_id: UUID
    org_id: UUID
    email_enabled: bool
    in_app_enabled: bool
    digest_frequency: str


class NotificationPreferenceUpdate(BaseModel):
    """Update notification preferences request body."""

    email_enabled: Optional[bool] = None
    in_app_enabled: Optional[bool] = None
    digest_frequency: Optional[str] = Field(None, pattern="^(realtime|daily|weekly|never)$")
