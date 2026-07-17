"""Reaction management utilities for comments."""

import uuid
from sqlalchemy import delete, select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.comment_reaction import CommentReaction


async def toggle_reaction(
    db: AsyncSession,
    comment_id: uuid.UUID,
    user_id: uuid.UUID,
    emoji: str,
) -> bool:
    """
    Toggle a reaction: insert if absent, delete if present.

    Args:
        db: async database session
        comment_id: comment being reacted to
        user_id: user making the reaction
        emoji: emoji string (e.g., "👍")

    Returns:
        True if reaction now exists (was just inserted), False if was deleted
    """
    # Check if reaction already exists
    result = await db.execute(
        select(CommentReaction).where(
            (CommentReaction.comment_id == comment_id)
            & (CommentReaction.user_id == user_id)
            & (CommentReaction.emoji == emoji)
        )
    )
    existing = result.scalar_one_or_none()

    if existing:
        # Delete it
        await db.delete(existing)
        await db.commit()
        return False
    else:
        # Insert it
        reaction = CommentReaction(
            comment_id=comment_id,
            user_id=user_id,
            emoji=emoji,
        )
        db.add(reaction)
        await db.commit()
        await db.refresh(reaction)
        return True


async def get_reaction_counts(
    db: AsyncSession,
    comment_id: uuid.UUID,
) -> dict[str, int]:
    """
    Get emoji reaction counts for a comment.

    Args:
        db: async database session
        comment_id: comment to fetch reactions for

    Returns:
        Dict mapping emoji -> count. Empty dict if no reactions.
    """
    result = await db.execute(
        select(
            CommentReaction.emoji,
            func.count(CommentReaction.reaction_id).label("count"),
        )
        .where(CommentReaction.comment_id == comment_id)
        .group_by(CommentReaction.emoji)
    )

    counts = {}
    for row in result.all():
        emoji, count = row
        counts[emoji] = count

    return counts
