"""Team request/response schemas (T-2071..T-2075)."""

from datetime import datetime
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class TeamCreate(BaseModel):
    """New team."""

    name: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = None


class TeamUpdate(BaseModel):
    """Team settings update (T-2075). Only supplied fields are changed."""

    name: Optional[str] = Field(None, min_length=1, max_length=255)
    description: Optional[str] = None


class TeamRead(BaseModel):
    """Team as returned by the API."""

    model_config = ConfigDict(from_attributes=True)

    team_id: UUID
    org_id: UUID
    name: str
    description: Optional[str] = None
    created_at: datetime
    updated_at: datetime


class TeamMemberAdd(BaseModel):
    """Add an existing org user to a team."""

    user_id: UUID
    role: str = Field("member", pattern="^(lead|member)$")


class TeamMemberRoleUpdate(BaseModel):
    """Change a member's role (T-2072)."""

    role: str = Field(..., pattern="^(lead|member)$")


class TeamMemberRead(BaseModel):
    """Team member as returned by the API."""

    model_config = ConfigDict(from_attributes=True)

    member_id: UUID
    team_id: UUID
    user_id: UUID
    role: str
    created_at: datetime


class TeamInvitationCreate(BaseModel):
    """Invite an email address to join a team (T-2073)."""

    invited_email: str = Field(..., min_length=3, max_length=255)


class TeamInvitationRead(BaseModel):
    """Invitation as returned by the API.

    Includes `token` -- ponytail: no email provider is configured, so the
    caller/frontend is responsible for delivering the invitation link
    (e.g. `https://app.example.com/invitations/{token}/accept`) themselves.
    """

    model_config = ConfigDict(from_attributes=True)

    invitation_id: UUID
    team_id: UUID
    invited_email: str
    status: str
    token: str
    created_at: datetime
    expires_at: datetime


class TeamActivityItem(BaseModel):
    """One activity feed entry (T-2074): a comment or review on a document
    uploaded by a team member."""

    type: str  # "comment" | "review"
    document_id: UUID
    document_filename: str
    actor_user_id: Optional[UUID] = None
    occurred_at: datetime
    summary: str
