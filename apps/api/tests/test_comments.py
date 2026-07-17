"""Tests for the comment service functions (T-2061 comments, T-2062 inline annotations).

Acceptance test: creating a reply (parent_comment_id set) then fetching all
comments for a doc returns both; comments never leak across orgs.
"""

import uuid

import pytest
from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.collab.comments import create_comment, delete_comment, list_comments_for_doc
from app.models.document import Document
from app.models.organization import Organization
from app.models.user import User


async def _make_org_user_doc(db_session: AsyncSession, *, email: str = "user@example.com"):
    # org_id/user_id set explicitly: the model's default=uuid.uuid4 is a
    # flush-time default, so reading org.org_id before add()+commit() would
    # otherwise still be None here.
    org = Organization(org_id=uuid.uuid4(), name=f"org-{uuid.uuid4()}")
    user = User(user_id=uuid.uuid4(), org_id=org.org_id, email=email)
    doc = Document(
        org_id=org.org_id,
        filename="test.pdf",
        original_filename="test.pdf",
        file_size_bytes=1024,
        file_type="pdf",
        s3_path="s3://bucket/test.pdf",
    )
    db_session.add_all([org, user, doc])
    await db_session.commit()
    return org, user, doc


@pytest.mark.asyncio
async def test_reply_comment_included_in_doc_list(db_session: AsyncSession):
    """Acceptance test: reply + parent both come back from list_comments_for_doc."""
    org, user, doc = await _make_org_user_doc(db_session)

    parent = await create_comment(
        db_session, org_id=org.org_id, doc_id=doc.doc_id, user_id=user.user_id, content="Parent"
    )
    reply = await create_comment(
        db_session,
        org_id=org.org_id,
        doc_id=doc.doc_id,
        user_id=user.user_id,
        content="Reply",
        parent_comment_id=parent.comment_id,
    )

    comments = await list_comments_for_doc(db_session, org_id=org.org_id, doc_id=doc.doc_id)

    ids = {c.comment_id for c in comments}
    assert parent.comment_id in ids
    assert reply.comment_id in ids
    assert len(comments) == 2
    # Flat list, created_at ascending.
    assert comments[0].comment_id == parent.comment_id
    assert comments[1].parent_comment_id == parent.comment_id


@pytest.mark.asyncio
async def test_comments_do_not_leak_across_orgs(db_session: AsyncSession):
    org_a, user_a, doc_a = await _make_org_user_doc(db_session, email="a@example.com")
    org_b, user_b, doc_b = await _make_org_user_doc(db_session, email="b@example.com")

    await create_comment(
        db_session,
        org_id=org_a.org_id,
        doc_id=doc_a.doc_id,
        user_id=user_a.user_id,
        content="A's comment",
    )
    await create_comment(
        db_session,
        org_id=org_b.org_id,
        doc_id=doc_b.doc_id,
        user_id=user_b.user_id,
        content="B's comment",
    )

    a_comments = await list_comments_for_doc(db_session, org_id=org_a.org_id, doc_id=doc_a.doc_id)
    b_comments = await list_comments_for_doc(db_session, org_id=org_b.org_id, doc_id=doc_b.doc_id)

    assert [c.content for c in a_comments] == ["A's comment"]
    assert [c.content for c in b_comments] == ["B's comment"]

    # Wrong org_id for a real doc_id must not leak the other org's comments.
    cross = await list_comments_for_doc(db_session, org_id=org_b.org_id, doc_id=doc_a.doc_id)
    assert cross == []


@pytest.mark.asyncio
async def test_anchor_range_persisted(db_session: AsyncSession):
    org, user, doc = await _make_org_user_doc(db_session)
    comment = await create_comment(
        db_session,
        org_id=org.org_id,
        doc_id=doc.doc_id,
        user_id=user.user_id,
        content="Inline note",
        anchor_start=10,
        anchor_end=25,
    )
    assert comment.anchor_start == 10
    assert comment.anchor_end == 25


@pytest.mark.asyncio
async def test_delete_comment_by_author(db_session: AsyncSession):
    org, user, doc = await _make_org_user_doc(db_session)
    comment = await create_comment(
        db_session, org_id=org.org_id, doc_id=doc.doc_id, user_id=user.user_id, content="Delete me"
    )

    await delete_comment(
        db_session,
        org_id=org.org_id,
        doc_id=doc.doc_id,
        comment_id=comment.comment_id,
        user_id=user.user_id,
        role="viewer",
    )

    comments = await list_comments_for_doc(db_session, org_id=org.org_id, doc_id=doc.doc_id)
    assert comments == []


@pytest.mark.asyncio
async def test_delete_comment_by_other_user_forbidden(db_session: AsyncSession):
    org, author, doc = await _make_org_user_doc(db_session, email="author@example.com")
    other = User(org_id=org.org_id, email="other@example.com")
    db_session.add(other)
    await db_session.commit()

    comment = await create_comment(
        db_session, org_id=org.org_id, doc_id=doc.doc_id, user_id=author.user_id, content="Mine"
    )

    with pytest.raises(HTTPException) as exc_info:
        await delete_comment(
            db_session,
            org_id=org.org_id,
            doc_id=doc.doc_id,
            comment_id=comment.comment_id,
            user_id=other.user_id,
            role="viewer",
        )
    assert exc_info.value.status_code == 403


@pytest.mark.asyncio
async def test_delete_comment_by_admin_allowed(db_session: AsyncSession):
    org, author, doc = await _make_org_user_doc(db_session, email="author2@example.com")
    admin = User(org_id=org.org_id, email="admin@example.com", role="admin")
    db_session.add(admin)
    await db_session.commit()

    comment = await create_comment(
        db_session, org_id=org.org_id, doc_id=doc.doc_id, user_id=author.user_id, content="Mine"
    )

    await delete_comment(
        db_session,
        org_id=org.org_id,
        doc_id=doc.doc_id,
        comment_id=comment.comment_id,
        user_id=admin.user_id,
        role="admin",
    )

    comments = await list_comments_for_doc(db_session, org_id=org.org_id, doc_id=doc.doc_id)
    assert comments == []


@pytest.mark.asyncio
async def test_reply_to_missing_parent_404(db_session: AsyncSession):
    org, user, doc = await _make_org_user_doc(db_session)

    with pytest.raises(HTTPException) as exc_info:
        await create_comment(
            db_session,
            org_id=org.org_id,
            doc_id=doc.doc_id,
            user_id=user.user_id,
            content="Orphan reply",
            parent_comment_id=uuid.uuid4(),
        )
    assert exc_info.value.status_code == 404
