"""Tests for notification service functions (T-2076 T-2080).

Acceptance tests: create/list/mark-read/mark-all-read round-trip with real DB
rows, preferences default+upsert, org/user isolation (a notification for user A
in org X is never visible to user B or in org Y).
"""

import uuid

import pytest
from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.collab.notifications import (
    create_notification,
    get_preferences,
    list_notifications,
    mark_all_read,
    mark_read,
    upsert_preferences,
)
from app.models.kb_article import KBArticle  # noqa: F401 — ensure KBArticle is registered before Organization
from app.models.notification import Notification, NotificationPreference
from app.models.organization import Organization
from app.models.user import User


async def _make_org_user(db_session: AsyncSession, *, email: str = "user@example.com"):
    """Helper: create an org and user for testing."""
    org = Organization(org_id=uuid.uuid4(), name=f"org-{uuid.uuid4()}")
    user = User(user_id=uuid.uuid4(), org_id=org.org_id, email=email)
    db_session.add_all([org, user])
    await db_session.commit()
    return org, user


@pytest.mark.asyncio
async def test_create_and_list_notifications(db_session: AsyncSession):
    """Create notifications and list them, ordered by created_at DESC."""
    org, user = await _make_org_user(db_session)

    notif1 = await create_notification(
        db_session,
        org_id=org.org_id,
        user_id=user.user_id,
        type="document_review",
        content="Document review completed",
    )
    notif2 = await create_notification(
        db_session,
        org_id=org.org_id,
        user_id=user.user_id,
        type="approval_needed",
        content="Approval needed for SOW",
    )

    notifications = await list_notifications(
        db_session,
        org_id=org.org_id,
        user_id=user.user_id,
    )

    assert len(notifications) == 2
    assert notifications[0].notif_id == notif2.notif_id  # Newest first (DESC)
    assert notifications[1].notif_id == notif1.notif_id
    assert notifications[0].read is False
    assert notifications[1].read is False


@pytest.mark.asyncio
async def test_mark_single_notification_read(db_session: AsyncSession):
    """Mark a single notification as read."""
    org, user = await _make_org_user(db_session)

    notif = await create_notification(
        db_session,
        org_id=org.org_id,
        user_id=user.user_id,
        type="test",
        content="Test notification",
    )

    assert notif.read is False

    await mark_read(
        db_session,
        org_id=org.org_id,
        notif_id=notif.notif_id,
        user_id=user.user_id,
    )

    # Re-fetch to verify
    updated_notif = await db_session.get(Notification, notif.notif_id)
    assert updated_notif.read is True


@pytest.mark.asyncio
async def test_mark_read_org_isolation(db_session: AsyncSession):
    """Cannot mark a notification as read with wrong org_id."""
    org_a, user_a = await _make_org_user(db_session, email="a@example.com")
    org_b, user_b = await _make_org_user(db_session, email="b@example.com")

    notif = await create_notification(
        db_session,
        org_id=org_a.org_id,
        user_id=user_a.user_id,
        type="test",
        content="A's notification",
    )

    # Try to mark with wrong org_id
    with pytest.raises(HTTPException):
        await mark_read(
            db_session,
            org_id=org_b.org_id,  # Wrong org
            notif_id=notif.notif_id,
            user_id=user_a.user_id,
        )


@pytest.mark.asyncio
async def test_mark_all_read(db_session: AsyncSession):
    """Mark all unread notifications as read for a user."""
    org, user = await _make_org_user(db_session)

    # Create 3 notifications
    notif1 = await create_notification(
        db_session,
        org_id=org.org_id,
        user_id=user.user_id,
        type="type1",
        content="Content 1",
    )
    notif2 = await create_notification(
        db_session,
        org_id=org.org_id,
        user_id=user.user_id,
        type="type2",
        content="Content 2",
    )
    notif3 = await create_notification(
        db_session,
        org_id=org.org_id,
        user_id=user.user_id,
        type="type3",
        content="Content 3",
    )

    # Mark one as read manually
    await mark_read(
        db_session,
        org_id=org.org_id,
        notif_id=notif1.notif_id,
        user_id=user.user_id,
    )

    # Mark all as read
    count = await mark_all_read(
        db_session,
        org_id=org.org_id,
        user_id=user.user_id,
    )

    # Should have marked 2 (notif2 and notif3 were still unread)
    assert count == 2

    # Verify all are now read
    notifications = await list_notifications(
        db_session,
        org_id=org.org_id,
        user_id=user.user_id,
    )
    assert all(n.read for n in notifications)


@pytest.mark.asyncio
async def test_list_unread_only(db_session: AsyncSession):
    """Filter notifications by unread_only flag."""
    org, user = await _make_org_user(db_session)

    notif1 = await create_notification(
        db_session,
        org_id=org.org_id,
        user_id=user.user_id,
        type="type1",
        content="Unread",
    )
    notif2 = await create_notification(
        db_session,
        org_id=org.org_id,
        user_id=user.user_id,
        type="type2",
        content="Will be read",
    )

    await mark_read(
        db_session,
        org_id=org.org_id,
        notif_id=notif2.notif_id,
        user_id=user.user_id,
    )

    # List all
    all_notifs = await list_notifications(
        db_session,
        org_id=org.org_id,
        user_id=user.user_id,
        unread_only=False,
    )
    assert len(all_notifs) == 2

    # List unread only
    unread_notifs = await list_notifications(
        db_session,
        org_id=org.org_id,
        user_id=user.user_id,
        unread_only=True,
    )
    assert len(unread_notifs) == 1
    assert unread_notifs[0].notif_id == notif1.notif_id


@pytest.mark.asyncio
async def test_list_pagination(db_session: AsyncSession):
    """Pagination with skip and limit."""
    org, user = await _make_org_user(db_session)

    # Create 5 notifications
    for i in range(5):
        await create_notification(
            db_session,
            org_id=org.org_id,
            user_id=user.user_id,
            type=f"type{i}",
            content=f"Content {i}",
        )

    # First page (limit=2)
    page1 = await list_notifications(
        db_session,
        org_id=org.org_id,
        user_id=user.user_id,
        skip=0,
        limit=2,
    )
    assert len(page1) == 2

    # Second page
    page2 = await list_notifications(
        db_session,
        org_id=org.org_id,
        user_id=user.user_id,
        skip=2,
        limit=2,
    )
    assert len(page2) == 2

    # Third page (only 1 left)
    page3 = await list_notifications(
        db_session,
        org_id=org.org_id,
        user_id=user.user_id,
        skip=4,
        limit=2,
    )
    assert len(page3) == 1

    # Verify no overlap
    all_ids = {n.notif_id for n in page1 + page2 + page3}
    assert len(all_ids) == 5


@pytest.mark.asyncio
async def test_notifications_do_not_leak_across_users(db_session: AsyncSession):
    """Notifications for user A never appear in user B's list."""
    org, user_a = await _make_org_user(db_session, email="a@example.com")
    _, user_b = await _make_org_user(db_session, email="b@example.com")

    await create_notification(
        db_session,
        org_id=org.org_id,
        user_id=user_a.user_id,
        type="type1",
        content="A's notification",
    )
    await create_notification(
        db_session,
        org_id=org.org_id,
        user_id=user_b.user_id,
        type="type2",
        content="B's notification",
    )

    a_notifs = await list_notifications(
        db_session,
        org_id=org.org_id,
        user_id=user_a.user_id,
    )
    b_notifs = await list_notifications(
        db_session,
        org_id=org.org_id,
        user_id=user_b.user_id,
    )

    assert len(a_notifs) == 1
    assert len(b_notifs) == 1
    assert a_notifs[0].notif_id != b_notifs[0].notif_id


@pytest.mark.asyncio
async def test_notifications_do_not_leak_across_orgs(db_session: AsyncSession):
    """Notifications for org A never appear in org B."""
    org_a, user_a = await _make_org_user(db_session, email="a@example.com")
    org_b, user_b = await _make_org_user(db_session, email="b@example.com")

    await create_notification(
        db_session,
        org_id=org_a.org_id,
        user_id=user_a.user_id,
        type="type1",
        content="Org A notification",
    )
    await create_notification(
        db_session,
        org_id=org_b.org_id,
        user_id=user_b.user_id,
        type="type2",
        content="Org B notification",
    )

    org_a_notifs = await list_notifications(
        db_session,
        org_id=org_a.org_id,
        user_id=user_a.user_id,
    )
    org_b_notifs = await list_notifications(
        db_session,
        org_id=org_b.org_id,
        user_id=user_b.user_id,
    )

    assert len(org_a_notifs) == 1
    assert len(org_b_notifs) == 1

    # Wrong org_id for real user should return empty
    cross_org = await list_notifications(
        db_session,
        org_id=org_b.org_id,
        user_id=user_a.user_id,
    )
    assert len(cross_org) == 0


@pytest.mark.asyncio
async def test_get_preferences_none_when_not_set(db_session: AsyncSession):
    """get_preferences returns None if no row exists."""
    org, user = await _make_org_user(db_session)

    prefs = await get_preferences(db_session, user_id=user.user_id)
    assert prefs is None


@pytest.mark.asyncio
async def test_upsert_preferences_creates_with_defaults(db_session: AsyncSession):
    """upsert_preferences creates a row with soft defaults if none exists."""
    org, user = await _make_org_user(db_session)

    prefs = await upsert_preferences(
        db_session,
        org_id=org.org_id,
        user_id=user.user_id,
    )

    assert prefs.user_id == user.user_id
    assert prefs.org_id == org.org_id
    assert prefs.email_enabled is True
    assert prefs.in_app_enabled is True
    assert prefs.digest_frequency == "daily"


@pytest.mark.asyncio
async def test_upsert_preferences_creates_with_custom_values(db_session: AsyncSession):
    """upsert_preferences can set custom values on create."""
    org, user = await _make_org_user(db_session)

    prefs = await upsert_preferences(
        db_session,
        org_id=org.org_id,
        user_id=user.user_id,
        email_enabled=False,
        digest_frequency="weekly",
    )

    assert prefs.email_enabled is False
    assert prefs.in_app_enabled is True  # Default
    assert prefs.digest_frequency == "weekly"


@pytest.mark.asyncio
async def test_upsert_preferences_updates_existing(db_session: AsyncSession):
    """upsert_preferences updates existing rows with new values."""
    org, user = await _make_org_user(db_session)

    # Create with defaults
    prefs1 = await upsert_preferences(
        db_session,
        org_id=org.org_id,
        user_id=user.user_id,
    )

    # Update
    prefs2 = await upsert_preferences(
        db_session,
        org_id=org.org_id,
        user_id=user.user_id,
        email_enabled=False,
        digest_frequency="never",
    )

    # Should be the same row, updated
    assert prefs2.user_id == prefs1.user_id
    assert prefs2.email_enabled is False
    assert prefs2.in_app_enabled is True  # Unchanged
    assert prefs2.digest_frequency == "never"


@pytest.mark.asyncio
async def test_preferences_partial_update(db_session: AsyncSession):
    """upsert_preferences can update only specific fields."""
    org, user = await _make_org_user(db_session)

    # Create
    await upsert_preferences(
        db_session,
        org_id=org.org_id,
        user_id=user.user_id,
        email_enabled=True,
        in_app_enabled=True,
        digest_frequency="daily",
    )

    # Update only digest_frequency
    prefs = await upsert_preferences(
        db_session,
        org_id=org.org_id,
        user_id=user.user_id,
        digest_frequency="weekly",
    )

    assert prefs.email_enabled is True  # Unchanged
    assert prefs.in_app_enabled is True  # Unchanged
    assert prefs.digest_frequency == "weekly"


@pytest.mark.asyncio
async def test_preferences_org_isolation(db_session: AsyncSession):
    """Preferences are scoped to user + org correctly."""
    org_a, user_a = await _make_org_user(db_session, email="a@example.com")
    org_b, user_b = await _make_org_user(db_session, email="b@example.com")

    prefs_a = await upsert_preferences(
        db_session,
        org_id=org_a.org_id,
        user_id=user_a.user_id,
        email_enabled=False,
    )
    prefs_b = await upsert_preferences(
        db_session,
        org_id=org_b.org_id,
        user_id=user_b.user_id,
        email_enabled=True,
    )

    # Fetch and verify
    fetched_a = await get_preferences(db_session, user_id=user_a.user_id)
    fetched_b = await get_preferences(db_session, user_id=user_b.user_id)

    assert fetched_a.email_enabled is False
    assert fetched_b.email_enabled is True
