"""Comment API endpoints (T-2061 comments, T-2062 inline annotations).

Flat create/list/delete only. Threaded fetch (/comments/threaded), reactions,
and digest live in routers/collab_extra.py (a parallel agent's routes).
"""

import logging
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.collab.comments import create_comment, delete_comment, list_comments_for_doc
from app.db.session import get_db
from app.dependencies import get_current_user
from app.models.document import Document
from app.schemas.auth import TokenData
from app.schemas.comment import CommentCreate, CommentRead

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/v1/documents", tags=["comments"])


async def _get_org_document(db: AsyncSession, doc_id: UUID, org_id: UUID) -> Document:
    """Fetch a document scoped to the caller's org, or 404. Also the org-isolation gate:
    a doc_id from another org never resolves, so no comment can be attached to or
    listed from a document outside the caller's tenant."""
    result = await db.execute(
        select(Document).where(
            Document.doc_id == doc_id,
            Document.org_id == org_id,
            Document.deleted_at.is_(None),
        )
    )
    doc = result.scalar_one_or_none()
    if doc is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Document not found")
    return doc


@router.post(
    "/{doc_id}/comments",
    response_model=CommentRead,
    status_code=status.HTTP_201_CREATED,
    summary="Add a comment or reply",
)
async def add_comment(
    doc_id: UUID,
    body: CommentCreate,
    current_user: TokenData = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    org_id = UUID(str(current_user.org_id))
    await _get_org_document(db, doc_id, org_id)

    comment = await create_comment(
        db,
        org_id=org_id,
        doc_id=doc_id,
        user_id=UUID(str(current_user.user_id)),
        content=body.content,
        parent_comment_id=body.parent_comment_id,
        anchor_start=body.anchor_start,
        anchor_end=body.anchor_end,
    )
    return CommentRead.model_validate(comment)


@router.get(
    "/{doc_id}/comments",
    response_model=list[CommentRead],
    summary="List comments for a document (flat, oldest first)",
)
async def get_comments(
    doc_id: UUID,
    current_user: TokenData = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    org_id = UUID(str(current_user.org_id))
    await _get_org_document(db, doc_id, org_id)

    comments = await list_comments_for_doc(db, org_id=org_id, doc_id=doc_id)
    return [CommentRead.model_validate(c) for c in comments]


@router.delete(
    "/{doc_id}/comments/{comment_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a comment (author or admin only)",
)
async def remove_comment(
    doc_id: UUID,
    comment_id: UUID,
    current_user: TokenData = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    org_id = UUID(str(current_user.org_id))
    await delete_comment(
        db,
        org_id=org_id,
        doc_id=doc_id,
        comment_id=comment_id,
        user_id=UUID(str(current_user.user_id)),
        role=current_user.role,
    )
    return None
