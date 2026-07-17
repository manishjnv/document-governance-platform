"""Tests for fine-grained access control: grants, expiry, revocation, IP allowlist.

T-2056: document-level RBAC (grants)
T-2057: delegation (temporary access grants)
T-2058: access expiry
T-2059: access audit trail (grant/revoke logging + list_access_for_resource)
T-2060: IP whitelisting (optional feature)
"""

import uuid
from datetime import datetime, timedelta, timezone

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.compliance.access_control import (
    check_access,
    grant_access,
    list_access_for_resource,
    purge_expired_grants,
    revoke_access,
)
from app.compliance.ip_policy import add_ip_entry, is_ip_allowed, list_ip_entries, remove_ip_entry
from app.models.audit_log import AuditLog
from app.models.organization import Organization
from app.models.resource_grant import ResourceGrant
from app.models.user import User


async def _make_org_and_users(db_session: AsyncSession, n_users: int = 2):
    org = Organization(name=f"test_org_{uuid.uuid4().hex[:8]}", subscription_tier="pro")
    db_session.add(org)
    await db_session.flush()

    users = []
    for i in range(n_users):
        user = User(org_id=org.org_id, email=f"user{i}_{uuid.uuid4().hex[:8]}@example.com")
        db_session.add(user)
        users.append(user)
    await db_session.flush()
    return org, users


@pytest.mark.asyncio
async def test_grant_check_revoke_round_trip(db_session: AsyncSession):
    org, (granter, grantee) = await _make_org_and_users(db_session)
    resource_id = uuid.uuid4()

    grant = await grant_access(
        db_session,
        org_id=org.org_id,
        resource_type="document",
        resource_id=resource_id,
        grantee_user_id=grantee.user_id,
        permission="edit",
        granted_by_user_id=granter.user_id,
    )
    assert grant.grant_id is not None

    # Access exists for the granted permission ...
    assert await check_access(
        db_session,
        org_id=org.org_id,
        resource_type="document",
        resource_id=resource_id,
        user_id=grantee.user_id,
        required_permission="edit",
    )
    # ... but not for a different permission or a different user.
    assert not await check_access(
        db_session,
        org_id=org.org_id,
        resource_type="document",
        resource_id=resource_id,
        user_id=grantee.user_id,
        required_permission="approve",
    )
    assert not await check_access(
        db_session,
        org_id=org.org_id,
        resource_type="document",
        resource_id=resource_id,
        user_id=granter.user_id,
        required_permission="edit",
    )

    # grant_access audit-logged the grant (T-2059).
    from sqlalchemy import select

    logs = (
        await db_session.execute(select(AuditLog).where(AuditLog.action == "access.granted"))
    ).scalars().all()
    assert len(logs) == 1
    assert logs[0].resource_id == resource_id

    # list_access_for_resource shows the current grantee.
    listing = await list_access_for_resource(
        db_session, org_id=org.org_id, resource_type="document", resource_id=resource_id
    )
    assert len(listing) == 1
    assert listing[0]["grantee_user_id"] == str(grantee.user_id)

    # Revoke: grant disappears, access check now False, revoke was audit-logged.
    await revoke_access(
        db_session, org_id=org.org_id, grant_id=grant.grant_id, revoked_by_user_id=granter.user_id
    )
    assert not await check_access(
        db_session,
        org_id=org.org_id,
        resource_type="document",
        resource_id=resource_id,
        user_id=grantee.user_id,
        required_permission="edit",
    )
    revoke_logs = (
        await db_session.execute(select(AuditLog).where(AuditLog.action == "access.revoked"))
    ).scalars().all()
    assert len(revoke_logs) == 1


@pytest.mark.asyncio
async def test_expired_grant_fails_check_access_and_can_be_purged(db_session: AsyncSession):
    org, (granter, grantee) = await _make_org_and_users(db_session)
    resource_id = uuid.uuid4()

    await grant_access(
        db_session,
        org_id=org.org_id,
        resource_type="document",
        resource_id=resource_id,
        grantee_user_id=grantee.user_id,
        permission="view",
        granted_by_user_id=granter.user_id,
        expires_at=datetime.now(timezone.utc) - timedelta(minutes=1),
    )

    # Expired grant does not satisfy check_access ...
    assert not await check_access(
        db_session,
        org_id=org.org_id,
        resource_type="document",
        resource_id=resource_id,
        user_id=grantee.user_id,
        required_permission="view",
    )
    # ... and doesn't show up as current access either.
    listing = await list_access_for_resource(
        db_session, org_id=org.org_id, resource_type="document", resource_id=resource_id
    )
    assert listing == []

    # A future-dated grant still works (expiry is a ceiling, not a floor).
    await grant_access(
        db_session,
        org_id=org.org_id,
        resource_type="document",
        resource_id=resource_id,
        grantee_user_id=grantee.user_id,
        permission="view",
        granted_by_user_id=granter.user_id,
        expires_at=datetime.now(timezone.utc) + timedelta(hours=1),
    )
    assert await check_access(
        db_session,
        org_id=org.org_id,
        resource_type="document",
        resource_id=resource_id,
        user_id=grantee.user_id,
        required_permission="view",
    )

    # purge_expired_grants only removes the expired row, not the live one.
    deleted = await purge_expired_grants(db_session, org.org_id)
    assert deleted == 1

    from sqlalchemy import select

    remaining = (
        await db_session.execute(select(ResourceGrant).where(ResourceGrant.org_id == org.org_id))
    ).scalars().all()
    assert len(remaining) == 1
    assert remaining[0].expires_at is not None


@pytest.mark.asyncio
async def test_grant_and_revoke_respect_org_isolation(db_session: AsyncSession):
    org1, (granter1, grantee1) = await _make_org_and_users(db_session)
    org2, (granter2, grantee2) = await _make_org_and_users(db_session)
    resource_id = uuid.uuid4()

    grant1 = await grant_access(
        db_session,
        org_id=org1.org_id,
        resource_type="document",
        resource_id=resource_id,
        grantee_user_id=grantee1.user_id,
        permission="view",
        granted_by_user_id=granter1.user_id,
    )

    # org2 checking the same (resource_type, resource_id) sees nothing.
    assert not await check_access(
        db_session,
        org_id=org2.org_id,
        resource_type="document",
        resource_id=resource_id,
        user_id=grantee1.user_id,
        required_permission="view",
    )
    assert await list_access_for_resource(
        db_session, org_id=org2.org_id, resource_type="document", resource_id=resource_id
    ) == []

    # org2 cannot revoke org1's grant by id.
    await revoke_access(
        db_session, org_id=org2.org_id, grant_id=grant1.grant_id, revoked_by_user_id=granter2.user_id
    )
    assert await check_access(
        db_session,
        org_id=org1.org_id,
        resource_type="document",
        resource_id=resource_id,
        user_id=grantee1.user_id,
        required_permission="view",
    )


@pytest.mark.asyncio
async def test_ip_allowlist_empty_allows_everything(db_session: AsyncSession):
    org, _ = await _make_org_and_users(db_session, n_users=1)
    assert await is_ip_allowed(db_session, org.org_id, "203.0.113.5")
    assert await is_ip_allowed(db_session, org.org_id, "10.0.0.1")


@pytest.mark.asyncio
async def test_ip_allowlist_with_entries_only_allows_matching_cidr(db_session: AsyncSession):
    org, _ = await _make_org_and_users(db_session, n_users=1)
    await add_ip_entry(db_session, org.org_id, "203.0.113.0/24", description="office")

    assert await is_ip_allowed(db_session, org.org_id, "203.0.113.42")
    assert not await is_ip_allowed(db_session, org.org_id, "198.51.100.7")

    entries = await list_ip_entries(db_session, org.org_id)
    assert len(entries) == 1

    await remove_ip_entry(db_session, org.org_id, entries[0].entry_id)
    # Back to zero entries -- opt-in feature is off again, everything allowed.
    assert await is_ip_allowed(db_session, org.org_id, "198.51.100.7")


@pytest.mark.asyncio
async def test_ip_allowlist_respects_org_isolation(db_session: AsyncSession):
    org1, _ = await _make_org_and_users(db_session, n_users=1)
    org2, _ = await _make_org_and_users(db_session, n_users=1)

    await add_ip_entry(db_session, org1.org_id, "203.0.113.0/24")

    # org1 is restricted to its CIDR ...
    assert not await is_ip_allowed(db_session, org1.org_id, "10.0.0.1")
    # ... org2 has no entries of its own, so it's unrestricted.
    assert await is_ip_allowed(db_session, org2.org_id, "10.0.0.1")

    entries2 = await list_ip_entries(db_session, org2.org_id)
    assert entries2 == []
