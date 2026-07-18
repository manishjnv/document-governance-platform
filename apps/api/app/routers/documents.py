"""Document management API endpoints.

Implementation: T-301 through T-320
- Document upload (T-303)
- Document list (T-306)
- Document metadata (T-307)
- Document delete (T-308)
- Document parsing (T-313-T-320)
"""

import logging
import re
from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.analytics.aggregator import record_document_view
from app.compliance.audit import log_action
from app.core.cache import invalidate_cache
from app.db.session import get_db
from app.dependencies import get_current_user, verify_org_access
from app.models.document import Document
from app.parser import parse_document
from app.schemas.auth import TokenData
from app.schemas.document import (
    DocumentCreate,
    DocumentRead,
    DocumentUpdate,
)
from app.storage import get_storage_instance

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/v1/documents", tags=["documents"])

# Constants
MAX_UPLOAD_SIZE = 50 * 1024 * 1024  # 50MB
ALLOWED_TYPES = {"pdf", "docx"}
MIME_TO_TYPE = {
    "application/pdf": "pdf",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document": "docx",
}

_UNSAFE_FILENAME_CHARS = re.compile(r"[^A-Za-z0-9._-]")


def _sanitize_filename(raw_filename: str) -> str:
    """Storage-safe filename: strips any path components (../, /, \\) and
    replaces everything but [A-Za-z0-9._-] -- used to build the S3/local
    storage key. The raw, unsanitized name is still preserved separately as
    Document.original_filename for display.

    Without this, a crafted filename like "../../etc/passwd" or an absolute
    path flowed straight into storage_path = f"org/{org_id}/doc/{doc_id}/v1/{filename}",
    a path-traversal risk against local storage and S3 key-prefix isolation.

    Strips '/' and '\\' explicitly (not via os.path.basename, whose
    separator handling is platform-dependent -- ntpath treats '\\' as a
    separator, posixpath doesn't, which would make this function produce a
    different, still-safe-but-inconsistent result depending on which OS the
    API happens to run on).
    """
    name = (raw_filename or "").strip()
    name = name.replace("\\", "/")
    name = name.rsplit("/", 1)[-1]  # basename, separator-consistent across OSes
    name = _UNSAFE_FILENAME_CHARS.sub("_", name)
    name = name.lstrip(".") or "document"
    return name[:255]


@router.post(
    "/upload",
    status_code=status.HTTP_202_ACCEPTED,
    response_model=DocumentRead,
    summary="Upload document",
    responses={
        413: {"description": "File too large (>50MB)"},
        422: {"description": "Invalid file type"},
    },
)
async def upload_document(
    file: UploadFile = File(...),
    org_id: UUID = Query(..., description="Organization ID"),
    project_name: Optional[str] = Query(None, description="Optional project label"),
    current_user: TokenData = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Upload a document for review.

    **T-303: Document upload endpoint**
    - Accepts: DOCX, PDF
    - Max size: 50MB
    - Stores in S3/Blob storage
    - Returns: Document metadata with upload_id
    """
    # Verify user has access to org
    await verify_org_access(str(org_id), current_user)

    # Validate file type
    content_type = file.content_type or ""
    file_type = MIME_TO_TYPE.get(content_type, "").lower()

    if not file_type or file_type not in ALLOWED_TYPES:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Unsupported file type. Allowed: {', '.join(ALLOWED_TYPES)}",
        )

    # Validate file size
    content = await file.read()
    if len(content) > MAX_UPLOAD_SIZE:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=f"File too large. Max size: {MAX_UPLOAD_SIZE / (1024*1024)}MB",
        )

    # Get storage backend
    storage = await get_storage_instance()

    # Create document record
    from uuid import uuid4

    doc_id = uuid4()
    document_group_id = uuid4()
    raw_filename = file.filename or f"document_{doc_id}"
    filename = _sanitize_filename(raw_filename)

    # Generate storage path
    storage_path = f"org/{org_id}/doc/{doc_id}/v1/{filename}"

    # Upload to storage
    try:
        await storage.upload(storage_path, content)
    except Exception as e:
        logger.error(f"Storage upload failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to upload file",
        )

    # Parse document asynchronously
    try:
        parse_result = await parse_document(content, file_type)
        parsed_text = parse_result.raw_text
        parsed_sections = [
            {
                "heading": s.heading,
                "level": s.level,
                "content": s.content,
                "page_number": s.page_number,
            }
            for s in parse_result.sections
        ]
        page_count = parse_result.page_count
        detected_type = parse_result.detected_type.value if parse_result.detected_type else None
    except Exception as e:
        logger.error(f"Parsing failed: {e}")
        parsed_text = None
        parsed_sections = None
        page_count = None
        detected_type = None

    # Create database record
    from datetime import datetime

    doc = Document(
        doc_id=doc_id,
        document_group_id=document_group_id,
        org_id=current_user.org_id,
        uploaded_by_user_id=UUID(str(current_user.user_id)),
        filename=filename,
        original_filename=raw_filename,
        project_name=project_name,
        file_size_bytes=len(content),
        file_type=file_type,
        s3_path=storage_path,
        version=1,
        document_type=detected_type,
        page_count=page_count,
        language="en",
        storage_status="uploaded",
        parsed_text=parsed_text,
        parsed_sections=parsed_sections,
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow(),
    )

    db.add(doc)
    await db.commit()
    await db.refresh(doc)

    # T-2041: audit trail
    await log_action(
        db,
        org_id=doc.org_id,
        user_id=doc.uploaded_by_user_id,
        action="document.uploaded",
        resource_type="document",
        resource_id=doc.doc_id,
    )
    await db.commit()

    # T-3019: this org's cached analytics/dashboard are stale now
    await invalidate_cache(f"cache:*:{doc.org_id}:*")

    logger.info(f"Document {doc_id} uploaded by user {current_user.user_id}")

    return DocumentRead.from_orm(doc)


@router.get(
    "",
    response_model=list[DocumentRead],
    summary="List organization documents",
)
async def list_documents(
    org_id: UUID = Query(..., description="Organization ID"),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=1000),
    document_type: Optional[str] = Query(None),
    current_user: TokenData = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    List documents in organization.

    **T-306: List documents endpoint**
    """
    # Verify access
    await verify_org_access(str(org_id), current_user)

    from sqlalchemy import select

    query = select(Document).where(
        (Document.org_id == org_id) & (Document.deleted_at.is_(None))
    )

    if document_type:
        query = query.where(Document.document_type == document_type)

    query = query.offset(skip).limit(limit).order_by(Document.created_at.desc())

    result = await db.execute(query)
    documents = result.scalars().all()

    # Attach each document's latest review score (accuracy/completeness
    # columns on the dashboard) -- one query for the whole page, not N+1.
    from app.models.review import Review

    doc_ids = [doc.doc_id for doc in documents]
    latest_review_by_doc: dict = {}
    if doc_ids:
        review_result = await db.execute(
            select(Review)
            .where(Review.doc_id.in_(doc_ids) & (Review.deleted_at.is_(None)))
            .order_by(Review.doc_id, Review.created_at.desc())
        )
        for review in review_result.scalars().all():
            latest_review_by_doc.setdefault(review.doc_id, review)

    reads = []
    for doc in documents:
        read = DocumentRead.from_orm(doc)
        latest_review = latest_review_by_doc.get(doc.doc_id)
        if latest_review and latest_review.status == "completed":
            read.latest_overall_score = (
                float(latest_review.overall_score) if latest_review.overall_score is not None else None
            )
            read.latest_completeness_score = (
                float(latest_review.score_completeness)
                if latest_review.score_completeness is not None
                else None
            )
        reads.append(read)

    return reads


@router.get(
    "/batch",
    response_model=list[DocumentRead],
    summary="Get multiple documents by id",
)
async def get_documents_batch(
    ids: str = Query(..., description="Comma-separated document UUIDs"),
    current_user: TokenData = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Fetch multiple documents in one query.

    **T-3010: Batch document fetch**

    Invalid/malformed UUIDs in `ids` are skipped rather than erroring the
    whole request. Only documents in the caller's org are returned.
    """
    from sqlalchemy import select

    doc_ids = []
    for raw in ids.split(","):
        raw = raw.strip()
        if not raw:
            continue
        try:
            doc_ids.append(UUID(raw))
        except ValueError:
            continue

    if not doc_ids:
        return []

    result = await db.execute(
        select(Document).where(
            Document.doc_id.in_(doc_ids)
            & (Document.org_id == current_user.org_id)
            & Document.deleted_at.is_(None)
        )
    )
    documents = result.scalars().all()

    return [DocumentRead.from_orm(doc) for doc in documents]


@router.get(
    "/{doc_id}",
    response_model=DocumentRead,
    summary="Get document metadata",
)
async def get_document(
    doc_id: UUID,
    current_user: TokenData = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Get document metadata and parsing status.

    **T-307: Get document endpoint**
    """
    from sqlalchemy import select

    result = await db.execute(
        select(Document).where(
            (Document.doc_id == doc_id) & (Document.deleted_at.is_(None))
        )
    )
    doc = result.scalar_one_or_none()

    if not doc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Document not found"
        )

    # Verify org access
    await verify_org_access(str(doc.org_id), current_user)

    # T-2006: record this read for document analytics (view_count/unique_viewer_count)
    await record_document_view(db, doc.org_id, doc.doc_id, current_user.user_id)
    await db.commit()

    return DocumentRead.from_orm(doc)


@router.delete(
    "/{doc_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete document",
)
async def delete_document(
    doc_id: UUID,
    current_user: TokenData = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Delete document (soft delete).

    **T-308: Delete document endpoint**
    """
    from datetime import datetime
    from sqlalchemy import select

    if current_user.role == "viewer":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Viewer role cannot delete documents",
        )

    result = await db.execute(
        select(Document).where(
            (Document.doc_id == doc_id) & (Document.deleted_at.is_(None))
        )
    )
    doc = result.scalar_one_or_none()

    if not doc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Document not found"
        )

    # Verify org access
    await verify_org_access(str(doc.org_id), current_user)

    # Soft delete
    doc.deleted_at = datetime.utcnow()
    await db.commit()

    logger.info(f"Document {doc_id} deleted by user {current_user.user_id}")
    return None
