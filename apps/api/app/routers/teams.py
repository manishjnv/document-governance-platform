"""Team API endpoints (T-2071 teams, T-2072 member roles, T-2073 invitations,
T-2074 activity feed, T-2075 settings).

Org-scoped throughout: every team-scoped route resolves the team via
_get_org_team first, which 404s on a team_id from another org -- same
org-isolation gate pattern as routers/comments.py's _get_org_document.
"""

import logging
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.collab.teams import (
    accept_invitation,
    add_team_member,
    create_team,
    get_team_activity,
    invite_to_team,
    list_org_teams,
    remove_team_member,
    update_member_role,
    update_team_settings,
)
from app.db.session import get_db
from app.dependencies import get_current_user
from app.models.team import Team
from app.models.user import User
from app.schemas.auth import TokenData
from app.schemas.team import (
    TeamActivityItem,
    TeamCreate,
    TeamInvitationCreate,
    TeamInvitationRead,
    TeamMemberAdd,
    TeamMemberRead,
    TeamMemberRoleUpdate,
    TeamRead,
    TeamUpdate,
)

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/v1/teams", tags=["teams"])


async def _get_org_team(db: AsyncSession, team_id: UUID, org_id: UUID) -> Team:
    """Fetch a team scoped to the caller's org, or 404. Also the org-isolation gate:
    a team_id from another org never resolves, so no member/invitation/settings
    operation can touch a team outside the caller's tenant."""
    result = await db.execute(
        select(Team).where(
            Team.team_id == team_id,
            Team.org_id == org_id,
            Team.deleted_at.is_(None),
        )
    )
    team = result.scalar_one_or_none()
    if team is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Team not found")
    return team


async def _get_org_user(db: AsyncSession, user_id: UUID, org_id: UUID) -> User:
    """A team member must belong to the same org as the team."""
    result = await db.execute(
        select(User).where(
            User.user_id == user_id,
            User.org_id == org_id,
            User.deleted_at.is_(None),
        )
    )
    user = result.scalar_one_or_none()
    if user is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "User not found in this organization")
    return user


@router.post(
    "", response_model=TeamRead, status_code=status.HTTP_201_CREATED, summary="Create a team"
)
async def create_team_endpoint(
    body: TeamCreate,
    current_user: TokenData = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    org_id = UUID(str(current_user.org_id))
    team = await create_team(db, org_id=org_id, name=body.name, description=body.description)
    return TeamRead.model_validate(team)


@router.get("", response_model=list[TeamRead], summary="List teams in the caller's org")
async def list_teams_endpoint(
    current_user: TokenData = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    org_id = UUID(str(current_user.org_id))
    teams = await list_org_teams(db, org_id=org_id)
    return [TeamRead.model_validate(t) for t in teams]


@router.get("/{team_id}", response_model=TeamRead, summary="Get a team")
async def get_team_endpoint(
    team_id: UUID,
    current_user: TokenData = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    org_id = UUID(str(current_user.org_id))
    team = await _get_org_team(db, team_id, org_id)
    return TeamRead.model_validate(team)


@router.patch(
    "/{team_id}", response_model=TeamRead, summary="Update team settings (name/description)"
)
async def update_team_endpoint(
    team_id: UUID,
    body: TeamUpdate,
    current_user: TokenData = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    org_id = UUID(str(current_user.org_id))
    await _get_org_team(db, team_id, org_id)
    team = await update_team_settings(db, team_id=team_id, **body.model_dump(exclude_unset=True))
    return TeamRead.model_validate(team)


@router.post(
    "/{team_id}/members",
    response_model=TeamMemberRead,
    status_code=status.HTTP_201_CREATED,
    summary="Add an org user to a team",
)
async def add_team_member_endpoint(
    team_id: UUID,
    body: TeamMemberAdd,
    current_user: TokenData = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    org_id = UUID(str(current_user.org_id))
    await _get_org_team(db, team_id, org_id)
    await _get_org_user(db, body.user_id, org_id)
    member = await add_team_member(db, team_id=team_id, user_id=body.user_id, role=body.role)
    return TeamMemberRead.model_validate(member)


@router.patch(
    "/{team_id}/members/{user_id}/role",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Change a member's role",
)
async def update_team_member_role_endpoint(
    team_id: UUID,
    user_id: UUID,
    body: TeamMemberRoleUpdate,
    current_user: TokenData = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    org_id = UUID(str(current_user.org_id))
    await _get_org_team(db, team_id, org_id)
    await update_member_role(db, team_id=team_id, user_id=user_id, new_role=body.role)
    return None


@router.delete(
    "/{team_id}/members/{user_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Remove a member from a team",
)
async def remove_team_member_endpoint(
    team_id: UUID,
    user_id: UUID,
    current_user: TokenData = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    org_id = UUID(str(current_user.org_id))
    await _get_org_team(db, team_id, org_id)
    await remove_team_member(db, team_id=team_id, user_id=user_id)
    return None


@router.post(
    "/{team_id}/invitations",
    response_model=TeamInvitationRead,
    status_code=status.HTTP_201_CREATED,
    summary="Invite an email address to join a team",
)
async def invite_to_team_endpoint(
    team_id: UUID,
    body: TeamInvitationCreate,
    current_user: TokenData = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    org_id = UUID(str(current_user.org_id))
    await _get_org_team(db, team_id, org_id)
    invitation = await invite_to_team(
        db,
        team_id=team_id,
        invited_email=body.invited_email,
        invited_by_user_id=UUID(str(current_user.user_id)),
    )
    return TeamInvitationRead.model_validate(invitation)


@router.post(
    "/invitations/{token}/accept",
    response_model=TeamMemberRead,
    summary="Accept a team invitation by token",
)
async def accept_invitation_endpoint(
    token: str,
    current_user: TokenData = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    member = await accept_invitation(
        db, token=token, accepting_user_id=UUID(str(current_user.user_id))
    )
    return TeamMemberRead.model_validate(member)


@router.get(
    "/{team_id}/activity",
    response_model=list[TeamActivityItem],
    summary="Recent comment/review activity on documents uploaded by this team's members",
)
async def get_team_activity_endpoint(
    team_id: UUID,
    days: int = Query(7, ge=1, le=365),
    current_user: TokenData = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    org_id = UUID(str(current_user.org_id))
    activity = await get_team_activity(db, org_id=org_id, team_id=team_id, days=days)
    return [TeamActivityItem.model_validate(item) for item in activity]
