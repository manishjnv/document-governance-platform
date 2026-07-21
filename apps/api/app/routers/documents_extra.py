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

from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile, status
from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.dependencies import get_current_user, verify_org_access
from app.insights.similarity import find_duplicates, find_similar_documents
from app.models.document import Document
from app.models.document_link_suggestion import DocumentLinkSuggestion
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


@router.get(
    "/suggestions",
    summary="List pending version-link suggestions for this org",
)
async def list_link_suggestions(
    org_id: uuid.UUID = Query(...),
    current_user: TokenData = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> list[dict]:
    """Phase B: suggestions persist here (not just a one-time upload toast)
    so they're visible later on the Documents page too."""
    await verify_org_access(str(org_id), current_user)

    result = await db.execute(
        select(DocumentLinkSuggestion, Document)
        .join(Document, Document.doc_id == DocumentLinkSuggestion.doc_id)
        .where(
            and_(
                DocumentLinkSuggestion.org_id == org_id,
                DocumentLinkSuggestion.status == "pending",
                Document.deleted_at.is_(None),
            )
        )
        .order_by(DocumentLinkSuggestion.created_at.desc())
    )

    suggestions = []
    for suggestion, doc in result.all():
        suggested_doc = await db.scalar(
            select(Document).where(
                and_(
                    Document.doc_id == suggestion.suggested_doc_id,
                    Document.org_id == org_id,
                    Document.deleted_at.is_(None),
                )
            )
        )
        if suggested_doc is None:
            continue
        suggestions.append(
            {
                "suggestion_id": str(suggestion.suggestion_id),
                "doc_id": str(doc.doc_id),
                "filename": doc.original_filename,
                "suggested_doc_id": str(suggested_doc.doc_id),
                "suggested_filename": suggested_doc.original_filename,
                "suggested_version": suggested_doc.version,
                "similarity_score": float(suggestion.similarity_score),
            }
        )
    return suggestions


@router.patch(
    "/suggestions/{suggestion_id}",
    summary="Accept or dismiss a version-link suggestion",
)
async def resolve_link_suggestion(
    suggestion_id: uuid.UUID,
    body: dict,
    current_user: TokenData = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict:
    action = body.get("action")
    if action not in {"accept", "dismiss"}:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="action must be 'accept' or 'dismiss'",
        )

    result = await db.execute(
        select(DocumentLinkSuggestion).where(
            DocumentLinkSuggestion.suggestion_id == suggestion_id
        )
    )
    suggestion = result.scalar_one_or_none()
    if suggestion is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Suggestion not found")

    await verify_org_access(str(suggestion.org_id), current_user)

    if action == "dismiss":
        suggestion.status = "dismissed"
        await db.commit()
        return {"suggestion_id": str(suggestion_id), "status": "dismissed"}

    # Accept: link doc into the suggested document's group, as the next version.
    doc = await _get_org_document(db, suggestion.doc_id, suggestion.org_id)
    target = await _get_org_document(db, suggestion.suggested_doc_id, suggestion.org_id)
    await _link_document_to_group(db, doc, target.document_group_id)
    suggestion.status = "accepted"
    await db.commit()
    return {"suggestion_id": str(suggestion_id), "status": "accepted", "new_version": doc.version}


async def _link_document_to_group(
    db: AsyncSession, doc: Document, target_group_id: uuid.UUID
) -> None:
    """Sets doc's document_group_id to target_group_id and version to
    max(existing versions in that group) + 1. Shared by suggestion-accept
    and the retroactive "link to existing document" action -- never called
    silently/automatically, always from an explicit user action."""
    max_version_result = await db.execute(
        select(Document.version)
        .where(
            and_(
                Document.document_group_id == target_group_id,
                Document.org_id == doc.org_id,
                Document.deleted_at.is_(None),
            )
        )
        .order_by(Document.version.desc())
    )
    max_version = max_version_result.scalars().first() or 0

    doc.document_group_id = target_group_id
    doc.version = max_version + 1
    await db.flush()


@router.post(
    "/{doc_id}/link",
    summary="Retroactively link a standalone document into an existing document's version group",
)
async def link_document(
    doc_id: uuid.UUID,
    body: dict,
    current_user: TokenData = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Phase B: the searchable 'Link to existing document' picker's backing
    endpoint -- an explicit user action, never automatic."""
    target_doc_id = body.get("target_doc_id")
    if not target_doc_id:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="target_doc_id is required"
        )

    doc = await _get_org_document(db, doc_id, current_user.org_id)
    target = await _get_org_document(db, uuid.UUID(str(target_doc_id)), current_user.org_id)

    if doc.document_group_id == target.document_group_id:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Document is already in this version group",
        )

    await _link_document_to_group(db, doc, target.document_group_id)
    await db.commit()
    await db.refresh(doc)

    return {"doc_id": str(doc.doc_id), "document_group_id": str(doc.document_group_id), "version": doc.version}


@router.post(
    "/{doc_id}/versions",
    status_code=status.HTTP_202_ACCEPTED,
    summary="Upload a new version of an existing document",
)
async def upload_new_version(
    doc_id: uuid.UUID,
    file: UploadFile = File(...),
    current_user: TokenData = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Phase B explicit versioning action: sets document_group_id to the
    source document's and version to max+1, unlike a normal upload (which
    always starts a fresh document_group_id)."""
    # Imported here (not at module load) to avoid a circular import --
    # documents.py doesn't import this router, but this endpoint reuses its
    # upload internals rather than duplicating ~80 lines of storage/parsing
    # logic.
    from app.routers.documents import (
        ALLOWED_TYPES,
        MAX_UPLOAD_SIZE,
        MIME_TO_TYPE,
        _store_uploaded_document,
    )

    source = await _get_org_document(db, doc_id, current_user.org_id)

    content_type = file.content_type or ""
    file_type = MIME_TO_TYPE.get(content_type, "").lower()
    if not file_type or file_type not in ALLOWED_TYPES:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Unsupported file type. Allowed: {', '.join(ALLOWED_TYPES)}",
        )

    content = await file.read()
    if len(content) > MAX_UPLOAD_SIZE:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=f"File too large. Max size: {MAX_UPLOAD_SIZE / (1024*1024)}MB",
        )

    max_version_result = await db.execute(
        select(Document.version)
        .where(
            and_(
                Document.document_group_id == source.document_group_id,
                Document.org_id == current_user.org_id,
                Document.deleted_at.is_(None),
            )
        )
        .order_by(Document.version.desc())
    )
    next_version = (max_version_result.scalars().first() or 0) + 1

    doc = await _store_uploaded_document(
        db,
        current_user,
        current_user.org_id,
        content,
        file_type,
        file.filename or f"document_{doc_id}",
        document_group_id=source.document_group_id,
        version=next_version,
        project_id=source.project_id,
        project_name=source.project_name,
    )

    return {"doc_id": str(doc.doc_id), "document_group_id": str(doc.document_group_id), "version": doc.version}


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


def _serialize_finding(f) -> dict:
    return {
        "finding_id": str(f.finding_id),
        "category": f.category,
        "title": f.title,
        "severity": f.severity,
        "section_ref": f.section_ref,
        "status": f.status,
    }


@router.get(
    "/{doc_id}/versions/{other_version}/finding-diff",
    summary="Resolved/New/Persisted finding diff between this document and another version",
)
async def get_finding_diff(
    doc_id: uuid.UUID,
    other_version: int,
    current_user: TokenData = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Phase C (Document Lifecycle plan): compares the two versions'
    latest completed reviews' findings. doc_id's version is treated as the
    newer side if it has a higher version number than other_version,
    otherwise the two are swapped so "resolved"/"new" read naturally
    regardless of which doc_id the caller passed."""
    from app.insights.fix_verification import diff_findings
    from app.models.finding import Finding
    from app.models.review import Review

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

    older, newer = (doc_a, doc_b) if doc_a.version < doc_b.version else (doc_b, doc_a)

    async def _latest_completed_review_findings(doc: Document) -> list:
        review_result = await db.execute(
            select(Review)
            .where(
                and_(
                    Review.doc_id == doc.doc_id,
                    Review.status == "completed",
                    Review.deleted_at.is_(None),
                )
            )
            .order_by(Review.created_at.desc())
        )
        review = review_result.scalars().first()
        if review is None:
            return []
        findings_result = await db.execute(
            select(Finding).where(
                and_(Finding.review_id == review.review_id, Finding.deleted_at.is_(None))
            )
        )
        return list(findings_result.scalars().all())

    older_findings = await _latest_completed_review_findings(older)
    newer_findings = await _latest_completed_review_findings(newer)

    diff = diff_findings(older_findings, newer_findings)

    return {
        "older_version": older.version,
        "newer_version": newer.version,
        "resolved": [_serialize_finding(f) for f in diff["resolved"]],
        "new": [_serialize_finding(f) for f in diff["new"]],
        "persisted": [_serialize_finding(f) for f in diff["persisted"]],
    }
