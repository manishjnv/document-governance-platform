"""Tests for team management (T-2071 teams, T-2072 roles, T-2073 invitations,
T-2074 activity feed, T-2075 settings).

Acceptance test: an invitation issued for a user's email can be accepted by
that user (and only that user) and turns into team membership; a team's
activity feed surfaces real comment/review rows scoped by both org and the
lookback window; a team in org A is invisible/inaccessible from org B, both
at the service layer and through the HTTP router.
"""

import uuid
from datetime import datetime, timedelta, timezone

import pytest
from fastapi import HTTPException
from httpx import ASGITransport, AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth import create_access_token
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
from app.models.comment import Comment
from app.models.document import Document
from app.models.organization import Organization
from app.models.review import Review
from app.models.team import TeamInvitation, TeamMember
from app.models.user import User
from main import app


async def _make_org_and_user(db_session: AsyncSession, *, email: str = "user@example.com"):
    org = Organization(org_id=uuid.uuid4(), name=f"org-{uuid.uuid4()}")
    user = User(user_id=uuid.uuid4(), org_id=org.org_id, email=email)
    db_session.add_all([org, user])
    await db_session.commit()
    return org, user


# ---------------------------------------------------------------------------
# T-2071: create / list teams
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_create_team(db_session: AsyncSession):
    org, _ = await _make_org_and_user(db_session)
    team = await create_team(
        db_session, org_id=org.org_id, name="Platform", description="Core team"
    )
    assert team.team_id is not None
    assert team.org_id == org.org_id
    assert team.name == "Platform"
    assert team.description == "Core team"


@pytest.mark.asyncio
async def test_list_org_teams_scoped_to_org(db_session: AsyncSession):
    org_a, _ = await _make_org_and_user(db_session, email="a@example.com")
    org_b, _ = await _make_org_and_user(db_session, email="b@example.com")

    await create_team(db_session, org_id=org_a.org_id, name="A Team")
    await create_team(db_session, org_id=org_b.org_id, name="B Team")

    a_teams = await list_org_teams(db_session, org_id=org_a.org_id)
    b_teams = await list_org_teams(db_session, org_id=org_b.org_id)

    assert [t.name for t in a_teams] == ["A Team"]
    assert [t.name for t in b_teams] == ["B Team"]


# ---------------------------------------------------------------------------
# T-2072: members + roles
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_add_team_member_and_duplicate_conflict(db_session: AsyncSession):
    org, user = await _make_org_and_user(db_session)
    team = await create_team(db_session, org_id=org.org_id, name="Team")

    member = await add_team_member(db_session, team_id=team.team_id, user_id=user.user_id)
    assert member.role == "member"

    with pytest.raises(HTTPException) as exc_info:
        await add_team_member(db_session, team_id=team.team_id, user_id=user.user_id)
    assert exc_info.value.status_code == 409


@pytest.mark.asyncio
async def test_update_member_role(db_session: AsyncSession):
    org, user = await _make_org_and_user(db_session)
    team = await create_team(db_session, org_id=org.org_id, name="Team")
    await add_team_member(db_session, team_id=team.team_id, user_id=user.user_id, role="member")

    await update_member_role(
        db_session, team_id=team.team_id, user_id=user.user_id, new_role="lead"
    )

    result = await db_session.execute(
        select(TeamMember).where(TeamMember.team_id == team.team_id)
    )
    refreshed = result.scalar_one()
    assert refreshed.role == "lead"


@pytest.mark.asyncio
async def test_update_member_role_invalid_value_rejected(db_session: AsyncSession):
    org, user = await _make_org_and_user(db_session)
    team = await create_team(db_session, org_id=org.org_id, name="Team")
    await add_team_member(db_session, team_id=team.team_id, user_id=user.user_id)

    with pytest.raises(HTTPException) as exc_info:
        await update_member_role(
            db_session, team_id=team.team_id, user_id=user.user_id, new_role="owner"
        )
    assert exc_info.value.status_code == 400


@pytest.mark.asyncio
async def test_remove_team_member(db_session: AsyncSession):
    org, user = await _make_org_and_user(db_session)
    team = await create_team(db_session, org_id=org.org_id, name="Team")
    await add_team_member(db_session, team_id=team.team_id, user_id=user.user_id)

    await remove_team_member(db_session, team_id=team.team_id, user_id=user.user_id)

    with pytest.raises(HTTPException) as exc_info:
        await remove_team_member(db_session, team_id=team.team_id, user_id=user.user_id)
    assert exc_info.value.status_code == 404


# ---------------------------------------------------------------------------
# T-2073: invitations
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_invite_and_accept_round_trip(db_session: AsyncSession):
    org, inviter = await _make_org_and_user(db_session, email="lead@example.com")
    invitee = User(user_id=uuid.uuid4(), org_id=org.org_id, email="invitee@example.com")
    db_session.add(invitee)
    await db_session.commit()

    team = await create_team(db_session, org_id=org.org_id, name="Team")

    invitation = await invite_to_team(
        db_session,
        team_id=team.team_id,
        invited_email="invitee@example.com",
        invited_by_user_id=inviter.user_id,
    )
    assert invitation.status == "pending"
    assert invitation.token
    assert invitation.expires_at > datetime.now(timezone.utc)

    member = await accept_invitation(
        db_session, token=invitation.token, accepting_user_id=invitee.user_id
    )
    assert member.team_id == team.team_id
    assert member.user_id == invitee.user_id
    assert member.role == "member"

    await db_session.refresh(invitation)
    assert invitation.status == "accepted"


@pytest.mark.asyncio
async def test_accept_invitation_wrong_email_forbidden(db_session: AsyncSession):
    org, inviter = await _make_org_and_user(db_session, email="lead2@example.com")
    other_user = User(user_id=uuid.uuid4(), org_id=org.org_id, email="someone-else@example.com")
    db_session.add(other_user)
    await db_session.commit()

    team = await create_team(db_session, org_id=org.org_id, name="Team")
    invitation = await invite_to_team(
        db_session,
        team_id=team.team_id,
        invited_email="intended@example.com",
        invited_by_user_id=inviter.user_id,
    )

    with pytest.raises(HTTPException) as exc_info:
        await accept_invitation(
            db_session, token=invitation.token, accepting_user_id=other_user.user_id
        )
    assert exc_info.value.status_code == 403


@pytest.mark.asyncio
async def test_accept_invitation_expired(db_session: AsyncSession):
    org, inviter = await _make_org_and_user(db_session, email="lead3@example.com")
    invitee = User(user_id=uuid.uuid4(), org_id=org.org_id, email="expired@example.com")
    db_session.add(invitee)
    await db_session.commit()

    team = await create_team(db_session, org_id=org.org_id, name="Team")
    invitation = TeamInvitation(
        invitation_id=uuid.uuid4(),
        team_id=team.team_id,
        invited_email="expired@example.com",
        invited_by_user_id=inviter.user_id,
        status="pending",
        token="expired-token",
        expires_at=datetime.now(timezone.utc) - timedelta(days=1),
    )
    db_session.add(invitation)
    await db_session.commit()

    with pytest.raises(HTTPException) as exc_info:
        await accept_invitation(
            db_session, token="expired-token", accepting_user_id=invitee.user_id
        )
    assert exc_info.value.status_code == 400

    await db_session.refresh(invitation)
    assert invitation.status == "expired"


@pytest.mark.asyncio
async def test_accept_invitation_already_used(db_session: AsyncSession):
    org, inviter = await _make_org_and_user(db_session, email="lead4@example.com")
    invitee = User(user_id=uuid.uuid4(), org_id=org.org_id, email="reused@example.com")
    db_session.add(invitee)
    await db_session.commit()

    team = await create_team(db_session, org_id=org.org_id, name="Team")
    invitation = await invite_to_team(
        db_session,
        team_id=team.team_id,
        invited_email="reused@example.com",
        invited_by_user_id=inviter.user_id,
    )
    await accept_invitation(db_session, token=invitation.token, accepting_user_id=invitee.user_id)

    with pytest.raises(HTTPException) as exc_info:
        await accept_invitation(
            db_session, token=invitation.token, accepting_user_id=invitee.user_id
        )
    assert exc_info.value.status_code == 400


# ---------------------------------------------------------------------------
# T-2074: activity feed
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_team_activity_returns_real_data(db_session: AsyncSession):
    org, member_user = await _make_org_and_user(db_session, email="uploader@example.com")
    commenter = User(user_id=uuid.uuid4(), org_id=org.org_id, email="commenter@example.com")
    db_session.add(commenter)
    await db_session.commit()

    team = await create_team(db_session, org_id=org.org_id, name="Team")
    await add_team_member(db_session, team_id=team.team_id, user_id=member_user.user_id)

    doc = Document(
        org_id=org.org_id,
        uploaded_by_user_id=member_user.user_id,
        filename="sow.pdf",
        original_filename="sow.pdf",
        file_size_bytes=1024,
        file_type="pdf",
        s3_path="s3://bucket/sow.pdf",
    )
    db_session.add(doc)
    await db_session.commit()

    now = datetime.now(timezone.utc)
    recent_comment = Comment(
        org_id=org.org_id,
        doc_id=doc.doc_id,
        user_id=commenter.user_id,
        content="Looks good to me",
        created_at=now - timedelta(hours=1),
        updated_at=now - timedelta(hours=1),
    )
    old_comment = Comment(
        org_id=org.org_id,
        doc_id=doc.doc_id,
        user_id=commenter.user_id,
        content="Ancient comment outside the window",
        created_at=now - timedelta(days=10),
        updated_at=now - timedelta(days=10),
    )
    review = Review(
        org_id=org.org_id,
        doc_id=doc.doc_id,
        triggered_by_user_id=member_user.user_id,
        status="pending",
        created_at=now - timedelta(hours=2),
        updated_at=now - timedelta(hours=2),
    )
    db_session.add_all([recent_comment, old_comment, review])
    await db_session.commit()

    activity = await get_team_activity(db_session, org_id=org.org_id, team_id=team.team_id, days=7)

    assert len(activity) == 2  # old_comment falls outside the 7-day window
    types = {item["type"] for item in activity}
    assert types == {"comment", "review"}
    assert all(item["document_filename"] == "sow.pdf" for item in activity)
    # Newest first.
    assert activity[0]["occurred_at"] >= activity[1]["occurred_at"]


@pytest.mark.asyncio
async def test_team_activity_wrong_org_404(db_session: AsyncSession):
    org_a, _ = await _make_org_and_user(db_session, email="a2@example.com")
    org_b, _ = await _make_org_and_user(db_session, email="b2@example.com")
    team = await create_team(db_session, org_id=org_a.org_id, name="A Team")

    with pytest.raises(HTTPException) as exc_info:
        await get_team_activity(db_session, org_id=org_b.org_id, team_id=team.team_id)
    assert exc_info.value.status_code == 404


# ---------------------------------------------------------------------------
# T-2075 + cross-cutting: org isolation through the HTTP router
# ---------------------------------------------------------------------------


@pytest.fixture
async def client():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as c:
        yield c


@pytest.mark.asyncio
async def test_update_team_settings(db_session: AsyncSession):
    org, _ = await _make_org_and_user(db_session)
    team = await create_team(db_session, org_id=org.org_id, name="Old Name", description="Old")

    updated = await update_team_settings(db_session, team_id=team.team_id, name="New Name")
    assert updated.name == "New Name"
    assert updated.description == "Old"  # untouched field is left alone


@pytest.mark.asyncio
async def test_http_team_invisible_and_inaccessible_across_orgs(client, db_session: AsyncSession):
    org_a, user_a = await _make_org_and_user(db_session, email="httpa@example.com")
    org_b, user_b = await _make_org_and_user(db_session, email="httpb@example.com")

    team_a = await create_team(db_session, org_id=org_a.org_id, name="Org A Team")

    token_b, _ = create_access_token(
        user_id=user_b.user_id, email=user_b.email, org_id=org_b.org_id, role="admin"
    )
    headers_b = {"Authorization": f"Bearer {token_b}"}

    # org B's list never includes org A's team.
    list_resp = await client.get("/api/v1/teams", headers=headers_b)
    assert list_resp.status_code == 200
    assert str(team_a.team_id) not in {item["team_id"] for item in list_resp.json()}

    # org B cannot fetch org A's team directly by id.
    get_resp = await client.get(f"/api/v1/teams/{team_a.team_id}", headers=headers_b)
    assert get_resp.status_code == 404

    # org B cannot add a member to org A's team either.
    add_resp = await client.post(
        f"/api/v1/teams/{team_a.team_id}/members",
        json={"user_id": str(user_b.user_id), "role": "member"},
        headers=headers_b,
    )
    assert add_resp.status_code == 404

    # org A's own token can see and fetch it fine.
    token_a, _ = create_access_token(
        user_id=user_a.user_id, email=user_a.email, org_id=org_a.org_id, role="admin"
    )
    headers_a = {"Authorization": f"Bearer {token_a}"}
    get_ok = await client.get(f"/api/v1/teams/{team_a.team_id}", headers=headers_a)
    assert get_ok.status_code == 200
    assert get_ok.json()["team_id"] == str(team_a.team_id)
