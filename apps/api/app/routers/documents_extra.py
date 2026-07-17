"""Extra document endpoints: similarity (T-2026), duplicate detection
(T-2027), and version history/diff (T-2028, T-2029).

Separate router file from app/routers/documents.py by convention this wave.
No new schema -- document_group_id/version already exist on Document (Phase
1); similarity math lives in app/insights/similarity.py.

# ponytail: GET /duplicates is a static path under the same prefix as
# documents.py's GET /{doc_id}. Starlette matches routes in registration
# order across the whole app, so if documents.router is included before this
# router in main.py, a request to /api/v1/documents/duplicates will match
# documents.py's /{doc_id} first and 422 (invalid UUID) instead of reaching
# this route. Fix at integration time: include this router before
# documents.router in main.py (out of scope here -- main.py is off limits
# for this task).
"""

import difflib
import logging
import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.dependencies import get_current_user
from app.insights.similarity import find_duplicates, find_similar_documents
from app.models.document import Document
from app.schemas.auth import TokenData

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/documents", tags=["documents-extra"])


async def _get_org_document(db: AsyncSession, doc_id: uuid.UUID, org_id: uuid.UUID) -> Document:
    result = await db.execute(
        select(Document).where(
            and_(
                Document.doc_id == doc_id,
                Document.org_id == org_id,
                Document.deleted_at.is_(None),
            )
        )
    )
    doc = result.scalar_one_or_none()
    if doc is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Document not found")
    return doc


@router.get("/duplicates", summary="Find near-duplicate documents in the org")
async def get_duplicates(
    threshold: float = Query(0.9, ge=0.0, le=1.0),
    current_user: TokenData = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> list[dict]:
    """T-2027."""
    return await find_duplicates(db, current_user.org_id, threshold=threshold)


@router.get("/{doc_id}/similar", summary="Find documents similar to this one")
async def get_similar_documents(
    doc_id: uuid.UUID,
    threshold: float = Query(0.5, ge=0.0, le=1.0),
    limit: int = Query(10, ge=1, le=100),
    current_user: TokenData = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> list[dict]:
    """T-2026."""
    await _get_org_document(db, doc_id, current_user.org_id)
    return await find_similar_documents(
        db, current_user.org_id, doc_id, threshold=threshold, limit=limit
    )


@router.get("/{doc_id}/versions", summary="List versions of this document")
async def get_document_versions(
    doc_id: uuid.UUID,
    current_user: TokenData = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> list[dict]:
    """T-2028: every Document row sharing doc_id's document_group_id, newest first."""
    target = await _get_org_document(db, doc_id, current_user.org_id)

    result = await db.execute(
        select(Document)
        .where(
            and_(
                Document.document_group_id == target.document_group_id,
                Document.org_id == current_user.org_id,
                Document.deleted_at.is_(None),
            )
        )
        .order_by(Document.version.desc())
    )
    versions = result.scalars().all()

    return [
        {
            "doc_id": str(v.doc_id),
            "version": v.version,
            "created_at": v.created_at.isoformat(),
            "filename": v.filename,
        }
        for v in versions
    ]


@router.get(
    "/{doc_id}/versions/{other_version}/changes",
    summary="Line-level diff between this document and another version",
)
async def get_version_changes(
    doc_id: uuid.UUID,
    other_version: int,
    current_user: TokenData = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """T-2029: parsed_text diff between doc_id and other_version within the
    same document_group_id, via stdlib difflib. Line-level, not semantic."""
    doc_a = await _get_org_document(db, doc_id, current_user.org_id)

    other_result = await db.execute(
        select(Document).where(
            and_(
                Document.document_group_id == doc_a.document_group_id,
                Document.version == other_version,
                Document.org_id == current_user.org_id,
                Document.deleted_at.is_(None),
            )
        )
    )
    doc_b = other_result.scalar_one_or_none()
    if doc_b is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Version {other_version} not found for this document",
        )

    lines_a = (doc_a.parsed_text or "").splitlines()
    lines_b = (doc_b.parsed_text or "").splitlines()
    diff = list(difflib.ndiff(lines_a, lines_b))
    added = [line[2:] for line in diff if line.startswith("+ ")]
    removed = [line[2:] for line in diff if line.startswith("- ")]

    return {
        "doc_a_version": doc_a.version,
        "doc_b_version": doc_b.version,
        "added": added,
        "removed": removed,
    }
