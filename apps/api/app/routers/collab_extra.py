"""Collaboration extras: threaded comments, reactions, digest.

Separate from comments.py and approvals.py routers (owned by parallel agent).
T-2063: comment threads
T-2065: comment emoji reactions
T-2077: daily digest
"""

import logging
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.collab.digest import build_daily_digest
from app.collab.reactions import get_reaction_counts, toggle_reaction
from app.collab.threads import build_comment_tree
from app.db.session import get_db
from app.dependencies import get_current_user, verify_org_access
from app.models.document import Document
from app.schemas.auth import TokenData

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/v1", tags=["collab-extra"])

# Assume Comment model will be available at app.models.comment
try:
    from app.models.comment import Comment
except ImportError:
    Comment = None


@router.get(
    "/documents/{doc_id}/comments/threaded",
    status_code=status.HTTP_200_OK,
    summary="Fetch comments as nested tree",
)
async def get_threaded_comments(
    doc_id: UUID,
    current_user: TokenData = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Fetch all comments for a document, nested by reply threads.

    Returns tree of top-level comments with 'children' key for replies.
    """
    if not Comment:
        raise HTTPException(
            status_code=status.HTTP_501_NOT_IMPLEMENTED,
            detail="Comment model not yet available",
        )

    # Get document and verify org access
    result = await db.execute(
        select(Document).where(
            (Document.doc_id == doc_id) & (Document.deleted_at.is_(None))
        )
    )
    doc = result.scalar_one_or_none()

    if not doc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Document not found",
        )

    await verify_org_access(str(doc.org_id), current_user)

    # Fetch all non-deleted comments
    comments_result = await db.execute(
        select(Comment)
        .where(
            (Comment.doc_id == doc_id) & (Comment.deleted_at.is_(None))
        )
        .order_by(Comment.created_at.asc())
    )
    comments = comments_result.scalars().all()

    # Convert to dicts for tree building
    comment_dicts = [
        {
            "comment_id": str(comment.comment_id),
            "doc_id": str(comment.doc_id),
            "user_id": str(comment.user_id) if comment.user_id else None,
            "parent_comment_id": str(comment.parent_comment_id)
            if comment.parent_comment_id
            else None,
            "content": comment.content,
            "anchor_start": comment.anchor_start,
            "anchor_end": comment.anchor_end,
            "created_at": comment.created_at.isoformat(),
            "updated_at": comment.updated_at.isoformat(),
        }
        for comment in comments
    ]

    # Build tree
    tree = build_comment_tree(comment_dicts)

    return {"doc_id": str(doc_id), "comments": tree}


@router.post(
    "/comments/{comment_id}/reactions",
    status_code=status.HTTP_200_OK,
    summary="Toggle emoji reaction",
)
async def toggle_comment_reaction(
    comment_id: UUID,
    body: dict,
    current_user: TokenData = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Toggle emoji reaction on a comment.

    Body: {"emoji": "👍"}

    Returns: {"reaction_present": true/false, "emoji": "👍"}
    """
    if not Comment:
        raise HTTPException(
            status_code=status.HTTP_501_NOT_IMPLEMENTED,
            detail="Comment model not yet available",
        )

    emoji = body.get("emoji")
    if not emoji:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Missing 'emoji' field",
        )

    # Verify comment exists and user has access to its document
    comment_result = await db.execute(
        select(Comment, Document).where(
            (Comment.comment_id == comment_id) & (Comment.deleted_at.is_(None))
        )
    )
    comment_row = comment_result.first()

    if not comment_row:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Comment not found",
        )

    comment, doc = comment_row
    await verify_org_access(str(doc.org_id), current_user)

    # Toggle reaction
    now_present = await toggle_reaction(
        db, comment_id, UUID(str(current_user.user_id)), emoji
    )

    return {
        "comment_id": str(comment_id),
        "emoji": emoji,
        "reaction_present": now_present,
    }


@router.get(
    "/comments/{comment_id}/reactions",
    status_code=status.HTTP_200_OK,
    summary="Get reaction counts",
)
async def get_comment_reactions(
    comment_id: UUID,
    current_user: TokenData = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Get emoji reaction counts for a comment.

    Returns: {"comment_id": "...", "reactions": {"👍": 3, "❤️": 1}}
    """
    if not Comment:
        raise HTTPException(
            status_code=status.HTTP_501_NOT_IMPLEMENTED,
            detail="Comment model not yet available",
        )

    # Verify comment exists and user has access
    comment_result = await db.execute(
        select(Comment, Document).where(
            (Comment.comment_id == comment_id) & (Comment.deleted_at.is_(None))
        )
    )
    comment_row = comment_result.first()

    if not comment_row:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Comment not found",
        )

    comment, doc = comment_row
    await verify_org_access(str(doc.org_id), current_user)

    # Get counts
    counts = await get_reaction_counts(db, comment_id)

    return {"comment_id": str(comment_id), "reactions": counts}


@router.get(
    "/users/me/digest",
    status_code=status.HTTP_200_OK,
    summary="Get current user's daily digest",
)
async def get_user_digest(
    current_user: TokenData = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Get plain-text digest of last 24h activity (comments, reviews, findings).

    Returns: {"digest": "..."}
    """
    digest_content = await build_daily_digest(
        db, UUID(str(current_user.user_id)), UUID(str(current_user.org_id))
    )

    return {"digest": digest_content}
