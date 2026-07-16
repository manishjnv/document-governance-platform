"""Organization request/response schemas."""

from datetime import datetime
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.models.enums import SubscriptionTier


class OrganizationCreate(BaseModel):
    """Create a new organization (tenant)."""

    name: str = Field(..., min_length=1, max_length=255)
    subscription_tier: SubscriptionTier = SubscriptionTier.FREE


class OrganizationUpdate(BaseModel):
    """Partial update of an organization."""

    name: Optional[str] = Field(None, min_length=1, max_length=255)
    subscription_tier: Optional[SubscriptionTier] = None


class OrganizationRead(BaseModel):
    """Organization as returned by the API."""

    model_config = ConfigDict(from_attributes=True)

    org_id: UUID
    name: str
    subscription_tier: SubscriptionTier
    created_at: datetime
    updated_at: datetime
