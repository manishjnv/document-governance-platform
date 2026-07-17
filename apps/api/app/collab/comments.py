"""Comment service functions (T-2061 comments, T-2062 inline annotations).

Nesting/threading of replies is a different agent's job (see threads.py's
build_comment_tree) — list_comments_for_doc here returns a flat,
created_at-ordered list only.
"""

from __future__ import annotations

import uuid
from datetime import datetime

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.comment import Comment


async def create_comment(
    db: AsyncSession,
    *,
    org_id: uuid.UUID,
    doc_id: uuid.UUID,
    user_id: uuid.UUID,
    content: str,
    parent_comment_id: uuid.UUID | None = None,
    anchor_start: int | None = None,
    anchor_end: int | None = None,
) -> Comment:
    """Create a top-level comment or a reply, optionally anchored to a text range."""
    if parent_comment_id is not None:
        parent = await db.get(Comment, parent_comment_id)
        if (
            parent is None
            or parent.deleted_at is not None
            or parent.org_id != org_id
            or parent.doc_id != doc_id
        ):
            raise HTTPException(status.HTTP_404_NOT_FOUND, "Parent comment not found")

    comment = Comment(
        comment_id=uuid.uuid4(),
        org_id=org_id,
        doc_id=doc_id,
        user_id=user_id,
        parent_comment_id=parent_comment_id,
        content=content,
        anchor_start=anchor_start,
        anchor_end=anchor_end,
    )
    db.add(comment)
    await db.commit()
    await db.refresh(comment)
    return comment


async def list_comments_for_doc(
    db: AsyncSession, *, org_id: uuid.UUID, doc_id: uuid.UUID
) -> list[Comment]:
    """Flat list of a document's comments, oldest first."""
    result = await db.execute(
        select(Comment)
        .where(
            Comment.org_id == org_id,
            Comment.doc_id == doc_id,
            Comment.deleted_at.is_(None),
        )
        .order_by(Comment.created_at.asc())
    )
    return list(result.scalars().all())


async def delete_comment(
    db: AsyncSession,
    *,
    org_id: uuid.UUID,
    doc_id: uuid.UUID,
    comment_id: uuid.UUID,
    user_id: uuid.UUID,
    role: str,
) -> None:
    """Soft delete a comment. Only its author or an org admin may delete it."""
    result = await db.execute(
        select(Comment).where(
            Comment.comment_id == comment_id,
            Comment.org_id == org_id,
            Comment.doc_id == doc_id,
            Comment.deleted_at.is_(None),
        )
    )
    comment = result.scalar_one_or_none()
    if comment is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Comment not found")

    if comment.user_id != user_id and role != "admin":
        raise HTTPException(
            status.HTTP_403_FORBIDDEN, "Only the author or an admin can delete this comment"
        )

    comment.deleted_at = datetime.utcnow()
    await db.commit()
