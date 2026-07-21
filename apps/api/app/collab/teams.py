"""Team service functions (T-2071 teams, T-2072 member roles, T-2073 invitations,
T-2074 activity feed, T-2075 settings).

Org-tenant isolation for the team_id-only functions below (add_team_member,
update_member_role, remove_team_member, invite_to_team, update_team_settings)
is the caller's job -- the router resolves+verifies the team against
current_user.org_id before calling in (same split as comments.py's
_get_org_document). get_team_activity takes org_id directly and re-checks it
itself since it also uses org_id to scope the underlying document join.
"""

from __future__ import annotations

import secrets
import uuid
from datetime import datetime, timedelta, timezone

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.comment import Comment
from app.models.document import Document
from app.models.review import Review
from app.models.team import Team, TeamInvitation, TeamMember
from app.models.user import User

INVITATION_EXPIRY_DAYS = 7


async def create_team(
    db: AsyncSession, *, org_id: uuid.UUID, name: str, description: str | None = None
) -> Team:
    """Create a team in an org."""
    team = Team(team_id=uuid.uuid4(), org_id=org_id, name=name, description=description)
    db.add(team)
    await db.commit()
    await db.refresh(team)
    return team


async def list_org_teams(db: AsyncSession, *, org_id: uuid.UUID) -> list[Team]:
    """All active teams in an org, newest first."""
    result = await db.execute(
        select(Team)
        .where(Team.org_id == org_id, Team.deleted_at.is_(None))
        .order_by(Team.created_at.desc())
    )
    return list(result.scalars().all())


async def add_team_member(
    db: AsyncSession, *, team_id: uuid.UUID, user_id: uuid.UUID, role: str = "member"
) -> TeamMember:
    """Add an org user to a team."""
    existing = await db.execute(
        select(TeamMember).where(TeamMember.team_id == team_id, TeamMember.user_id == user_id)
    )
    if existing.scalar_one_or_none() is not None:
        raise HTTPException(status.HTTP_409_CONFLICT, "User is already a member of this team")

    member = TeamMember(member_id=uuid.uuid4(), team_id=team_id, user_id=user_id, role=role)
    db.add(member)
    await db.commit()
    await db.refresh(member)
    return member


async def update_member_role(
    db: AsyncSession, *, team_id: uuid.UUID, user_id: uuid.UUID, new_role: str
) -> None:
    """Change a member's role. new_role must be 'lead' or 'member'."""
    if new_role not in ("lead", "member"):
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "role must be 'lead' or 'member'")

    result = await db.execute(
        select(TeamMember).where(TeamMember.team_id == team_id, TeamMember.user_id == user_id)
    )
    member = result.scalar_one_or_none()
    if member is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Team member not found")

    member.role = new_role
    await db.commit()


async def remove_team_member(db: AsyncSession, *, team_id: uuid.UUID, user_id: uuid.UUID) -> None:
    """Remove a member from a team. Hard delete -- membership isn't a record to retain."""
    result = await db.execute(
        select(TeamMember).where(TeamMember.team_id == team_id, TeamMember.user_id == user_id)
    )
    member = result.scalar_one_or_none()
    if member is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Team member not found")

    await db.delete(member)
    await db.commit()


async def invite_to_team(
    db: AsyncSession,
    *,
    team_id: uuid.UUID,
    invited_email: str,
    invited_by_user_id: uuid.UUID | None,
) -> TeamInvitation:
    """Issue a pending invitation to join a team.

    # ponytail: no email provider configured; caller/frontend is responsible
    # for sending this invitation link, this just issues the token
    """
    invitation = TeamInvitation(
        invitation_id=uuid.uuid4(),
        team_id=team_id,
        invited_email=invited_email,
        invited_by_user_id=invited_by_user_id,
        status="pending",
        token=secrets.token_urlsafe(32),
        expires_at=datetime.now(timezone.utc) + timedelta(days=INVITATION_EXPIRY_DAYS),
    )
    db.add(invitation)
    await db.commit()
    await db.refresh(invitation)
    return invitation


async def accept_invitation(
    db: AsyncSession, *, token: str, accepting_user_id: uuid.UUID
) -> TeamMember:
    """Accept an invitation by token: mark it accepted, add the caller to the team.

    The accepting user's own email must match invited_email -- otherwise anyone
    who gets hold of a link (forward, leak) could redeem someone else's invite
    while authenticated as themselves.
    """
    result = await db.execute(select(TeamInvitation).where(TeamInvitation.token == token))
    invitation = result.scalar_one_or_none()
    if invitation is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Invitation not found")

    if invitation.status != "pending":
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Invitation already used")
    if invitation.expires_at < datetime.now(timezone.utc):
        invitation.status = "expired"
        await db.commit()
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Invitation has expired")

    accepting_user = await db.get(User, accepting_user_id)
    if accepting_user is None or (
        accepting_user.email.lower() != invitation.invited_email.lower()
    ):
        raise HTTPException(
            status.HTTP_403_FORBIDDEN, "Invitation email does not match the current user"
        )

    invitation.status = "accepted"

    existing = await db.execute(
        select(TeamMember).where(
            TeamMember.team_id == invitation.team_id, TeamMember.user_id == accepting_user_id
        )
    )
    member = existing.scalar_one_or_none()
    if member is None:
        member = TeamMember(
            member_id=uuid.uuid4(),
            team_id=invitation.team_id,
            user_id=accepting_user_id,
            role="member",
        )
        db.add(member)

    await db.commit()
    await db.refresh(member)
    return member


async def get_team_activity(
    db: AsyncSession, *, org_id: uuid.UUID, team_id: uuid.UUID, days: int = 7
) -> list[dict]:
    """Recent comments/reviews on documents uploaded by this team's members, newest first."""
    team = await db.get(Team, team_id)
    if team is None or team.deleted_at is not None or team.org_id != org_id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Team not found")

    since = datetime.now(timezone.utc) - timedelta(days=days)

    member_ids_result = await db.execute(
        select(TeamMember.user_id).where(TeamMember.team_id == team_id)
    )
    member_ids = [row[0] for row in member_ids_result.all()]
    if not member_ids:
        return []

    activity: list[dict] = []

    comment_rows = await db.execute(
        select(Comment, Document)
        .join(Document, Document.doc_id == Comment.doc_id)
        .where(
            Document.org_id == org_id,
            Document.uploaded_by_user_id.in_(member_ids),
            Document.deleted_at.is_(None),
            Comment.deleted_at.is_(None),
            Comment.created_at >= since,
        )
    )
    for comment, doc in comment_rows.all():
        activity.append(
            {
                "type": "comment",
                "document_id": doc.doc_id,
                "document_filename": doc.filename,
                "actor_user_id": comment.user_id,
                "occurred_at": comment.created_at,
                "summary": comment.content[:200],
            }
        )

    review_rows = await db.execute(
        select(Review, Document)
        .join(Document, Document.doc_id == Review.doc_id)
        .where(
            Document.org_id == org_id,
            Document.uploaded_by_user_id.in_(member_ids),
            Document.deleted_at.is_(None),
            Review.deleted_at.is_(None),
            Review.created_at >= since,
        )
    )
    for review, doc in review_rows.all():
        activity.append(
            {
                "type": "review",
                "document_id": doc.doc_id,
                "document_filename": doc.filename,
                "actor_user_id": review.triggered_by_user_id,
                "occurred_at": review.created_at,
                "summary": f"Review {review.status}",
            }
        )

    activity.sort(key=lambda item: item["occurred_at"], reverse=True)
    return activity


async def update_team_settings(db: AsyncSession, *, team_id: uuid.UUID, **fields) -> Team:
    """Update team name/description (T-2075). Only keys present in `fields` are changed."""
    team = await db.get(Team, team_id)
    if team is None or team.deleted_at is not None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Team not found")

    for key in ("name", "description"):
        if key in fields:
            setattr(team, key, fields[key])

    await db.commit()
    await db.refresh(team)
    return team
