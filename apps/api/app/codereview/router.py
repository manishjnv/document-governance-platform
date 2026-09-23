"""Code Security Review API (module reference §4).

Fully isolated: mounted by one line in main.py; every query is org-scoped
and soft-delete-aware. No LLM anywhere — ingest is pure/deterministic
(app/codereview/ingest.py).
"""

import io
import logging
import os
from datetime import datetime, timezone
from typing import Optional
from uuid import UUID, uuid4

from fastapi import APIRouter, Body, Depends, File, Form, HTTPException, UploadFile, status
from fastapi.responses import StreamingResponse
from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from starlette.concurrency import run_in_threadpool

from app.codereview import ingest, kit, report_pptx, report_xlsx
from app.codereview.ingest import IngestError
from app.compliance.audit import log_action
from app.core.cache import invalidate_cache
from app.db.session import get_db
from app.dependencies import get_current_user, require_role
from app.models.code_review import CodeReview
from app.routers.documents import _sanitize_filename
from app.schemas.auth import TokenData
from app.storage import get_storage_instance

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/v1/codereview", tags=["codereview"])


def _demo_ids() -> set:
    """Reviews every signed-in user may view and export (read-only), e.g. the
    NodeGoat demo. Comma-separated UUIDs in CODEREVIEW_DEMO_REVIEW_IDS; read
    per request so a container restart is the only deploy step."""
    raw = os.getenv("CODEREVIEW_DEMO_REVIEW_IDS", "")
    out = set()
    for part in raw.split(","):
        part = part.strip()
        if part:
            try:
                out.add(UUID(part))
            except ValueError:
                logger.warning("CODEREVIEW_DEMO_REVIEW_IDS: ignoring non-UUID %r", part)
    return out


def _list_item(row: CodeReview, org_id: UUID | None = None) -> dict:
    report = row.report or {}
    counts = report.get("counts") or {}
    return {
        "review_id": str(row.review_id),
        "demo": row.review_id in _demo_ids(),
        "editable": org_id is None or row.org_id == org_id,
        "name": row.name,
        "repo_label": row.repo_label,
        "git_sha": row.git_sha,
        "source_format": row.source_format,
        "created_at": row.created_at.isoformat() if row.created_at else None,
        "counts": {
            "total": counts.get("total", 0),
            "by_severity": counts.get("by_severity", {}),
        },
    }


def _detail(row: CodeReview, org_id: UUID | None = None) -> dict:
    return {
        "review_id": str(row.review_id),
        "demo": row.review_id in _demo_ids(),
        "editable": org_id is None or row.org_id == org_id,
        "name": row.name,
        "repo_label": row.repo_label,
        "git_sha": row.git_sha,
        "source_format": row.source_format,
        "created_at": row.created_at.isoformat() if row.created_at else None,
        "updated_at": row.updated_at.isoformat() if row.updated_at else None,
        "report": row.report,
    }


async def _get_review(db: AsyncSession, review_id: UUID, org_id: UUID, allow_demo: bool = False) -> CodeReview:
    """Org-scoped lookup. With allow_demo (read-only endpoints only), a review
    listed in CODEREVIEW_DEMO_REVIEW_IDS is visible to any org."""
    conditions = [CodeReview.review_id == review_id, CodeReview.deleted_at.is_(None)]
    if not (allow_demo and review_id in _demo_ids()):
        conditions.append(CodeReview.org_id == org_id)
    result = await db.execute(select(CodeReview).where(*conditions))
    row = result.scalar_one_or_none()
    if row is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Review not found")
    return row


@router.get("/kit.zip", summary="Download the consultant scan kit")
async def download_kit(current_user: TokenData = Depends(get_current_user)):
    version = kit.kit_version().get("vvah_version", "")
    data = await run_in_threadpool(kit.build_kit_zip)
    return StreamingResponse(
        io.BytesIO(data),
        media_type="application/zip",
        headers={"Content-Disposition": f'attachment; filename="scopewise-scan-kit-v{version}.zip"'},
    )


@router.post("/reviews", status_code=status.HTTP_201_CREATED, summary="Import a scan report")
async def create_review(
    report: UploadFile = File(...),
    manifest: Optional[UploadFile] = File(None),
    name: Optional[str] = Form(None),
    current_user: TokenData = Depends(require_role("admin", "reviewer")),
    db: AsyncSession = Depends(get_db),
):
    org_id = UUID(str(current_user.org_id))
    user_id = UUID(str(current_user.user_id)) if getattr(current_user, "user_id", None) else None

    report_bytes = await report.read()
    if len(report_bytes) > ingest.MAX_REPORT_BYTES:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=f"File too large. Max size: {ingest.MAX_REPORT_BYTES / (1024 * 1024)}MB",
        )

    report_filename_hint = report.filename or "report.json"
    zip_manifest_bytes = None
    zip_manifest_name = None
    original_zip_bytes = None
    if report_filename_hint.lower().endswith(".zip") or report_bytes[:4] == b"PK\x03\x04":
        original_zip_bytes = report_bytes
        try:
            report_bytes, report_filename_hint, zip_manifest_bytes, zip_manifest_name = (
                ingest.unpack_scan_zip(report_bytes)
            )
        except IngestError as exc:
            raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc))

    try:
        parsed = ingest.parse_report(report_bytes)
    except IngestError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc))

    if original_zip_bytes is not None:
        # Best-effort: a real scan-run zip carries triage.json/finding_case.json/
        # report.md/JUnit/Maven output alongside the report. Never let a bad
        # extra file turn a successful import into a 4xx/5xx.
        try:
            extras = ingest.read_run_extras(original_zip_bytes)
            if extras is not None:
                ingest.apply_run_extras(parsed, extras)
        except Exception as exc:  # noqa: BLE001
            logger.warning(f"Code review run-extras skipped: {exc}")
            parsed["assumptions"] = [*(parsed.get("assumptions") or []), "scan run extras could not be read"]

    manifest_bytes = None
    manifest_parsed = None
    manifest_filename_hint = None
    if manifest is not None:
        manifest_bytes = await manifest.read()
        manifest_filename_hint = manifest.filename or "run_manifest.json"
        if len(manifest_bytes) > ingest.MAX_REPORT_BYTES:
            raise HTTPException(
                status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                detail=f"Manifest too large. Max size: {ingest.MAX_REPORT_BYTES / (1024 * 1024)}MB",
            )
    elif zip_manifest_bytes is not None:
        manifest_bytes = zip_manifest_bytes
        manifest_filename_hint = zip_manifest_name

    if manifest_bytes is not None:
        try:
            manifest_parsed = ingest.parse_manifest(manifest_bytes)
        except IngestError as exc:
            raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc))
        parsed["manifest"] = manifest_parsed
        if not parsed.get("tool_version"):  # findings.json carries no version; the manifest does
            parsed["tool_version"] = manifest_parsed.get("tool_version")

    review_id = uuid4()
    storage = await get_storage_instance()

    report_filename = _sanitize_filename(report_filename_hint)
    source_path = f"org/{org_id}/codereview/{review_id}/{report_filename}"
    try:
        await storage.upload(source_path, report_bytes)
    except Exception as exc:  # noqa: BLE001
        logger.error(f"Code review report upload failed: {exc}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to store uploaded file",
        )

    manifest_path = None
    if manifest_bytes is not None:
        manifest_filename = _sanitize_filename(manifest_filename_hint or "run_manifest.json")
        manifest_path = f"org/{org_id}/codereview/{review_id}/{manifest_filename}"
        try:
            await storage.upload(manifest_path, manifest_bytes)
        except Exception as exc:  # noqa: BLE001
            logger.error(f"Code review manifest upload failed: {exc}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to store uploaded file",
            )

    resolved_name = (name or "").strip() or parsed.get("repo_name") or report_filename
    resolved_git_sha = (manifest_parsed or {}).get("target_git_sha") or parsed.get("git_sha")

    row = CodeReview(
        review_id=review_id,
        org_id=org_id,
        name=resolved_name[:255],
        repo_label=parsed.get("repo_name"),
        git_sha=resolved_git_sha,
        source_format=parsed["source_format"],
        source_path=source_path,
        manifest_path=manifest_path,
        report=parsed,
        created_by=user_id,
    )
    db.add(row)
    await db.commit()
    await db.refresh(row)

    await log_action(
        db,
        org_id=org_id,
        user_id=user_id,
        action="codereview.review_created",
        resource_type="code_review",
        resource_id=review_id,
    )
    await db.commit()
    await invalidate_cache(f"cache:*:{org_id}:*")

    return _detail(row)


@router.get("/reviews", summary="List imported reviews")
async def list_reviews(
    current_user: TokenData = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    org_id = UUID(str(current_user.org_id))
    demo = _demo_ids()
    scope = CodeReview.org_id == org_id
    if demo:
        scope = or_(scope, CodeReview.review_id.in_(demo))
    result = await db.execute(
        select(CodeReview)
        .where(scope, CodeReview.deleted_at.is_(None))
        .order_by(CodeReview.created_at.desc())
    )
    return [_list_item(row, org_id) for row in result.scalars().all()]


@router.get("/reviews/{review_id}", summary="Review detail")
async def get_review(
    review_id: UUID,
    current_user: TokenData = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    org_id = UUID(str(current_user.org_id))
    row = await _get_review(db, review_id, org_id, allow_demo=True)
    return _detail(row, org_id)


@router.patch("/reviews/{review_id}", summary="Rename a review")
async def rename_review(
    review_id: UUID,
    payload: dict = Body(...),
    current_user: TokenData = Depends(require_role("admin", "reviewer")),
    db: AsyncSession = Depends(get_db),
):
    org_id = UUID(str(current_user.org_id))
    row = await _get_review(db, review_id, org_id)
    new_name = (payload.get("name") or "").strip()
    if not new_name:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="name is required")
    row.name = new_name[:255]
    await db.commit()
    await db.refresh(row)
    await invalidate_cache(f"cache:*:{org_id}:*")
    return _detail(row)


@router.delete("/reviews/{review_id}", status_code=status.HTTP_204_NO_CONTENT, summary="Soft-delete a review")
async def delete_review(
    review_id: UUID,
    current_user: TokenData = Depends(require_role("admin", "reviewer")),
    db: AsyncSession = Depends(get_db),
):
    org_id = UUID(str(current_user.org_id))
    user_id = UUID(str(current_user.user_id)) if getattr(current_user, "user_id", None) else None
    row = await _get_review(db, review_id, org_id)
    row.deleted_at = datetime.now(timezone.utc)
    await db.commit()

    await log_action(
        db,
        org_id=org_id,
        user_id=user_id,
        action="codereview.review_deleted",
        resource_type="code_review",
        resource_id=review_id,
    )
    await db.commit()
    await invalidate_cache(f"cache:*:{org_id}:*")


@router.get("/reviews/{review_id}/export.xlsx", summary="Findings register (XLSX)")
async def export_xlsx(
    review_id: UUID,
    current_user: TokenData = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    org_id = UUID(str(current_user.org_id))
    row = await _get_review(db, review_id, org_id, allow_demo=True)
    content = await run_in_threadpool(report_xlsx.build_xlsx_export, row)
    filename = _sanitize_filename(row.name)[:80] or "review"
    return StreamingResponse(
        io.BytesIO(content),
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f'attachment; filename="{filename}-code-review.xlsx"'},
    )


@router.get("/reviews/{review_id}/export.pptx", summary="Briefing deck (PPTX)")
async def export_pptx(
    review_id: UUID,
    current_user: TokenData = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    org_id = UUID(str(current_user.org_id))
    row = await _get_review(db, review_id, org_id, allow_demo=True)
    content = await run_in_threadpool(report_pptx.build_pptx_export, row)
    filename = _sanitize_filename(row.name)[:80] or "review"
    return StreamingResponse(
        io.BytesIO(content),
        media_type="application/vnd.openxmlformats-officedocument.presentationml.presentation",
        headers={"Content-Disposition": f'attachment; filename="{filename}-briefing-deck.pptx"'},
    )
