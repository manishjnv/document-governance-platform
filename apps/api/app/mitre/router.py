"""MITRE assessment API (Phase 1). Fully isolated: mounted by one line in
main.py; every query is org-scoped and soft-delete-aware.

Report/export/compare endpoints are Phase 4; AI tagging is Phase 2.
"""

import asyncio
import base64
import io
import json
import logging
from datetime import datetime, timedelta, timezone
from typing import Optional
from uuid import UUID, uuid4

from fastapi import APIRouter, Body, Depends, File, Form, HTTPException, Query, UploadFile, status
from fastapi.responses import StreamingResponse
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from starlette.concurrency import run_in_threadpool

from app.compliance.audit import log_action
from app.core.cache import invalidate_cache
from app.db.session import get_db
from app.dependencies import get_current_user, require_role
from app.mitre import attack_data, ingest, service
from app.mitre import report as mitre_report
from app.models.mitre_assessment import MitreAssessment
from app.models.mitre_file import MitreFile
from app.models.mitre_use_case import MitreUseCase
from app.routers.documents import MAX_UPLOAD_SIZE, MIME_TO_TYPE, _sanitize_filename
from app.schemas.auth import TokenData
from app.storage import get_storage_instance

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/v1/mitre", tags=["mitre"])

STALE_RUN_MINUTES = 30
STALE_RUN_MESSAGE = "interrupted — likely a restart; re-run"

USE_CASE_FILE_TYPES = {"xlsx", "xls", "csv", "pdf", "docx"}
ENVIRONMENT_FILE_TYPES = {"xlsx", "xls"}

# Keep strong references to fire-and-forget tasks (asyncio only holds weak ones).
_RUNNING_TASKS: set = set()


def _resolve_file_type(upload: UploadFile, allowed: set) -> str:
    """MIME allowlist first (documents.py map), filename extension as the
    fallback for generic MIME types (curl/Excel exports often send
    application/octet-stream)."""
    file_type = MIME_TO_TYPE.get(upload.content_type or "", "")
    if not file_type:
        ext = (upload.filename or "").rsplit(".", 1)[-1].lower()
        file_type = ext if ext in USE_CASE_FILE_TYPES else ""
    if file_type not in allowed:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Unsupported file type. Allowed: {', '.join(sorted(allowed))}",
        )
    return file_type


def _read_upload(content: bytes) -> bytes:
    if len(content) > MAX_UPLOAD_SIZE:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=f"File too large. Max size: {MAX_UPLOAD_SIZE / (1024 * 1024)}MB",
        )
    return content


def _parse_intake(raw: Optional[str]) -> dict:
    if not raw:
        return {}
    try:
        intake = json.loads(raw)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="intake must be valid JSON",
        )
    if not isinstance(intake, dict):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="intake must be a JSON object",
        )
    exclusions = []
    for row in intake.get("exclusions") or []:
        target = str((row or {}).get("target", "")).strip()
        reason = str((row or {}).get("reason", "")).strip()
        if not target or not reason:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="every scope exclusion needs both a target and a reason",
            )
        exclusions.append({"target": target, "reason": reason})
    disabled = intake.get("count_disabled_as_coverage")
    if disabled is not None and not isinstance(disabled, bool):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="count_disabled_as_coverage must be true/false",
        )
    return {
        # length-capped: these flow into the narrative LLM prompt
        # (2026-08-01 adversarial review, non-blocking finding #5)
        "industry": str(intake.get("industry") or "").strip()[:200] or None,
        "region": str(intake.get("region") or "").strip()[:200] or None,
        "count_disabled_as_coverage": disabled,
        "exclusions": exclusions,
    }


async def _get_assessment(
    db: AsyncSession, assessment_id: UUID, org_id
) -> MitreAssessment:
    result = await db.execute(
        select(MitreAssessment).where(
            (MitreAssessment.assessment_id == assessment_id)
            & (MitreAssessment.org_id == org_id)
            & (MitreAssessment.deleted_at.is_(None))
        )
    )
    assessment = result.scalar_one_or_none()
    if assessment is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Assessment not found"
        )
    return assessment


@router.post("/assessments", status_code=status.HTTP_201_CREATED, summary="Create MITRE assessment (upload + parse)")
async def create_assessment(
    use_cases: UploadFile = File(..., description="Use-case/detection-rule dump"),
    environment: Optional[UploadFile] = File(None, description="Environment workbook (xlsx)"),
    intake: Optional[str] = Form(None, description="Intake JSON: industry/region/count_disabled_as_coverage/exclusions"),
    name: Optional[str] = Form(None, description="Assessment name (defaults to the dump filename)"),
    current_user: TokenData = Depends(require_role("admin", "reviewer")),
    db: AsyncSession = Depends(get_db),
):
    """Create + parse synchronously; returns the parse preview. Run is a
    separate POST /assessments/{id}/run."""
    org_id = UUID(str(current_user.org_id))
    intake_data = _parse_intake(intake)

    uc_type = _resolve_file_type(use_cases, USE_CASE_FILE_TYPES)
    uc_content = _read_upload(await use_cases.read())
    extraction_text = None
    if uc_type in ("pdf", "docx"):
        # Phase 2: text is parsed now (synchronous, fast); the AI extracts
        # use-case rows during the run (LLM calls don't fit a sync request).
        from app.parser import parse_document

        try:
            parse_result = await parse_document(uc_content, uc_type)
            text = parse_result.raw_text or ""
        except Exception:  # noqa: BLE001
            text = ""
        if len(text.strip()) < 200:  # mirror reviews.py's unreadable guard
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=(
                    "This document could not be read (it may be a scanned/"
                    "image-only file with no extractable text). Re-upload a "
                    "text-based PDF/DOCX, or use the XLSX template."
                ),
            )
        extraction_text = text
        parsed = {
            "rows": [],
            "columns": {},
            "sheet": None,
            "row_count": 0,
            "warnings": [
                "rules will be AI-extracted from this document when the "
                "assessment runs — lower fidelity than the XLSX template"
            ],
        }
    else:
        try:
            parsed = ingest.parse_use_case_file(uc_content, uc_type)
        except ingest.IngestError as exc:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=exc.detail
            )

    env_parsed, env_content, env_type = None, None, None
    if environment is not None:
        env_type = _resolve_file_type(environment, ENVIRONMENT_FILE_TYPES)
        env_content = _read_upload(await environment.read())
        try:
            env_parsed = ingest.parse_environment_file(env_content, env_type)
        except ingest.IngestError as exc:
            raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=exc.detail)

    assessment_id = uuid4()
    storage = await get_storage_instance()
    files_to_store = [
        (
            "use_cases",
            use_cases.filename,
            uc_type,
            uc_content,
            None if extraction_text else parsed["row_count"],
        )
    ]
    if env_parsed is not None:
        files_to_store.append(("environment", environment.filename, env_type, env_content, None))

    parse_assumptions, warnings = [], list(parsed["warnings"])
    if env_parsed is not None:
        environment_dict = dict(env_parsed["environment"])
        parse_assumptions.extend(env_parsed["assumptions"])
        warnings.extend(env_parsed["warnings"])
    else:
        environment_dict = {
            "platforms": [],
            "has_ics_assets": False,
            "has_managed_mobile": False,
            "inventory_provided": False,
            "exclusions": [],
        }
    environment_dict["exclusions"] = intake_data.get("exclusions", [])

    tagged = unmapped = invalid = 0
    use_case_models = []
    for row in parsed["rows"]:
        mappings, mapping_status, notes = service.build_mappings(row["tags"])
        parse_assumptions.extend(f"{row['row_ref']}: {note}" for note in notes)
        if mapping_status == "customer_tagged":
            tagged += 1
        elif mapping_status == "invalid":
            invalid += 1
        else:
            unmapped += 1
        use_case_models.append(
            {
                "row": row,
                "mappings": mappings,
                "mapping_status": mapping_status,
            }
        )

    file_rows = []
    for kind, raw_filename, file_type, content, row_count in files_to_store:
        filename = _sanitize_filename(raw_filename or f"{kind}.{file_type}")
        storage_path = f"org/{org_id}/mitre/{assessment_id}/{filename}"
        try:
            await storage.upload(storage_path, content)
        except Exception as exc:  # noqa: BLE001
            logger.error(f"MITRE file upload failed: {exc}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to store uploaded file",
            )
        file_rows.append(
            MitreFile(
                file_id=uuid4(),
                assessment_id=assessment_id,
                org_id=org_id,
                kind=kind,
                filename=filename,
                file_type=file_type,
                s3_path=storage_path,
                parse_status=(
                    "extraction_pending"
                    if kind == "use_cases" and extraction_text
                    else "parsed"
                ),
                row_count=row_count,
            )
        )

    assessment = MitreAssessment(
        assessment_id=assessment_id,
        org_id=org_id,
        name=(name or "").strip() or (use_cases.filename or "MITRE assessment")[:255],
        status="pending",
        attack_version=attack_data.DEFAULT.version,
        params={
            "intake": intake_data,
            "columns": parsed["columns"],
            "sheet": parsed["sheet"],
            "environment": environment_dict,
            "environment_lists": {
                "log_sources": env_parsed["log_sources"] if env_parsed else [],
                "tooling": env_parsed["tooling"] if env_parsed else [],
                "crown_jewels": env_parsed["crown_jewels"] if env_parsed else [],
                "sheets_found": env_parsed["sheets_found"] if env_parsed else {},
            },
            "parse_assumptions": parse_assumptions,
            "warnings": warnings,
            **({"extraction_text": extraction_text} if extraction_text else {}),
        },
        created_by=UUID(str(current_user.user_id)),
    )
    db.add(assessment)
    db.add_all(file_rows)
    uc_file_id = next(f.file_id for f in file_rows if f.kind == "use_cases")
    for item in use_case_models:
        row = item["row"]
        db.add(
            MitreUseCase(
                use_case_id=uuid4(),
                assessment_id=assessment_id,
                org_id=org_id,
                file_id=uc_file_id,
                row_ref=row["row_ref"],
                name=row["name"],
                # logic-fallback capped like ingest's description cap — an
                # XLSX cell may legally hold 32K chars (2026-08-02
                # adversarial review, blocking finding V2).
                description=row["description"] or (row["logic"] or "")[:2000] or None,
                log_source=row["log_source"],
                enabled=row["enabled"],
                mappings=item["mappings"],
                mapping_status=item["mapping_status"],
            )
        )
    await db.commit()

    await log_action(
        db,
        org_id=org_id,
        user_id=UUID(str(current_user.user_id)),
        action="mitre.assessment_created",
        resource_type="mitre_assessment",  # migration 030
        resource_id=assessment_id,
    )
    await db.commit()
    await invalidate_cache(f"cache:*:{org_id}:*")

    return {
        "assessment_id": str(assessment_id),
        "name": assessment.name,
        "status": "pending",
        "attack_version": assessment.attack_version,
        "row_count": parsed["row_count"],
        "columns": parsed["columns"],
        "sheet": parsed["sheet"],
        "tagged": tagged,
        "untagged": unmapped,
        "invalid": invalid,
        "extraction_pending": bool(extraction_text),
        "environment_provided": env_parsed is not None,
        "environment": environment_dict,
        "sheets_found": env_parsed["sheets_found"] if env_parsed else {},
        "warnings": warnings,
        "assumptions": parse_assumptions,
    }


@router.post("/assessments/{assessment_id}/run", status_code=status.HTTP_202_ACCEPTED, summary="Run assessment")
async def run_assessment(
    assessment_id: UUID,
    current_user: TokenData = Depends(require_role("admin", "reviewer")),
    db: AsyncSession = Depends(get_db),
):
    """202 + fire-and-forget pipeline task; poll GET /assessments/{id}."""
    org_id = UUID(str(current_user.org_id))
    assessment = await _get_assessment(db, assessment_id, org_id)
    if assessment.status in ("running", "completed"):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Assessment is already {assessment.status}",
        )
    assessment.status = "running"
    assessment.updated_at = datetime.now(timezone.utc)
    await db.commit()

    task = asyncio.create_task(service.run_assessment_pipeline(assessment_id, org_id))
    _RUNNING_TASKS.add(task)
    task.add_done_callback(_RUNNING_TASKS.discard)

    return {"assessment_id": str(assessment_id), "status": "running"}


@router.get("/assessments", summary="List assessments")
async def list_assessments(
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    current_user: TokenData = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(MitreAssessment)
        .where(
            (MitreAssessment.org_id == UUID(str(current_user.org_id)))
            & (MitreAssessment.deleted_at.is_(None))
        )
        .order_by(MitreAssessment.created_at.desc())
        .offset(skip)
        .limit(limit)
    )
    items = []
    for a in result.scalars().all():
        summary = a.summary or {}
        overall = summary.get("overall", {})
        items.append(
            {
                "assessment_id": str(a.assessment_id),
                "name": a.name,
                "status": a.status,
                "attack_version": a.attack_version,
                "created_at": a.created_at.isoformat() if a.created_at else None,
                "completed_at": a.completed_at.isoformat() if a.completed_at else None,
                "strict_pct": overall.get("strict_pct"),
                "weighted_pct": overall.get("weighted_pct"),
                # Phase 4: per-domain mini-bars on the list page without N+1
                # detail fetches — read from the stored summary JSONB.
                "domains_brief": {
                    key: {
                        "strict_pct": d.get("strict_pct"),
                        "covered": d.get("covered"),
                        "applicable": d.get("applicable"),
                    }
                    for key, d in (summary.get("domains") or {}).items()
                },
            }
        )
    return items


@router.get("/assessments/{assessment_id}", summary="Get assessment (status + results)")
async def get_assessment(
    assessment_id: UUID,
    current_user: TokenData = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    assessment = await _get_assessment(db, assessment_id, UUID(str(current_user.org_id)))

    # Stale-run guard: a fire-and-forget task dies with its container; flip
    # long-stuck 'running' rows to failed so the UI can offer a re-run.
    if assessment.status == "running" and assessment.updated_at is not None:
        age = datetime.now(timezone.utc) - assessment.updated_at
        if age > timedelta(minutes=STALE_RUN_MINUTES):
            assessment.status = "failed"
            assessment.error_message = STALE_RUN_MESSAGE
            assessment.updated_at = datetime.now(timezone.utc)
            await db.commit()

    return {
        "assessment_id": str(assessment.assessment_id),
        "name": assessment.name,
        "status": assessment.status,
        "attack_version": assessment.attack_version,
        "params": assessment.params,
        "summary": assessment.summary,
        "technique_results": assessment.technique_results,
        "error_message": assessment.error_message,
        "created_at": assessment.created_at.isoformat() if assessment.created_at else None,
        "completed_at": assessment.completed_at.isoformat() if assessment.completed_at else None,
    }


@router.get("/assessments/{assessment_id}/use-cases", summary="List parsed use cases")
async def list_use_cases(
    assessment_id: UUID,
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
    mapping_status: Optional[str] = Query(None),
    current_user: TokenData = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    org_id = UUID(str(current_user.org_id))
    await _get_assessment(db, assessment_id, org_id)

    conditions = (
        (MitreUseCase.assessment_id == assessment_id)
        & (MitreUseCase.org_id == org_id)
        & (MitreUseCase.deleted_at.is_(None))
    )
    if mapping_status:
        conditions = conditions & (MitreUseCase.mapping_status == mapping_status)

    total = (await db.execute(select(func.count()).select_from(MitreUseCase).where(conditions))).scalar()
    result = await db.execute(
        select(MitreUseCase).where(conditions).order_by(MitreUseCase.row_ref).offset(skip).limit(limit)
    )
    return {
        "total": total,
        "items": [
            {
                "use_case_id": str(uc.use_case_id),
                "row_ref": uc.row_ref,
                "name": uc.name,
                "description": uc.description,
                "log_source": uc.log_source,
                "enabled": uc.enabled,
                "mappings": uc.mappings,
                "mapping_status": uc.mapping_status,
            }
            for uc in result.scalars().all()
        ],
    }


async def _completed_assessment(db, assessment_id: UUID, org_id) -> MitreAssessment:
    assessment = await _get_assessment(db, assessment_id, org_id)
    if assessment.status != "completed":
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Available once the assessment has completed",
        )
    return assessment


async def _load_use_case_dicts(db, assessment_id: UUID, org_id) -> list:
    result = await db.execute(
        select(MitreUseCase)
        .where(
            (MitreUseCase.assessment_id == assessment_id)
            & (MitreUseCase.org_id == org_id)
            & (MitreUseCase.deleted_at.is_(None))
        )
        .order_by(MitreUseCase.row_ref)
    )
    return [
        {
            "row_ref": uc.row_ref,
            "name": uc.name,
            "description": uc.description,
            "log_source": uc.log_source,
            "enabled": uc.enabled,
            "mappings": uc.mappings or [],
            "mapping_status": uc.mapping_status,
        }
        for uc in result.scalars().all()
    ]


@router.get("/assessments/{assessment_id}/report", summary="Executive + detailed report (html/pdf)")
async def assessment_report(
    assessment_id: UUID,
    format: str = Query("html"),
    current_user: TokenData = Depends(get_current_user),  # viewers may read (plan §15 Q1)
    db: AsyncSession = Depends(get_db),
):
    """Mirrors reviews.py's report shape: {"format", "data"} with PDF as
    base64-in-JSON so the existing frontend blob pattern works."""
    org_id = UUID(str(current_user.org_id))
    assessment = await _completed_assessment(db, assessment_id, org_id)
    use_cases = await _load_use_case_dicts(db, assessment_id, org_id)
    # Report/xlsx generation is CPU-bound and unbounded on large assessments;
    # offload so it can't stall the single-worker event loop (2026-08-02
    # adversarial review, non-blocking finding #2).
    html = await run_in_threadpool(mitre_report.build_html_report, assessment, use_cases)

    if format.lower() == "pdf":
        try:
            pdf_bytes = await run_in_threadpool(mitre_report.generate_pdf, html)
        except Exception as exc:  # noqa: BLE001 — WeasyPrint native libs absent locally
            logger.error(f"MITRE PDF rendering failed: {exc}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="PDF rendering is unavailable in this environment — use format=html",
            )
        return {"format": "pdf", "data": base64.b64encode(pdf_bytes).decode("ascii")}
    return {"format": "html", "data": html}


@router.get("/assessments/{assessment_id}/export.xlsx", summary="Detailed XLSX gap register")
async def assessment_export_xlsx(
    assessment_id: UUID,
    current_user: TokenData = Depends(get_current_user),  # viewers may download (plan §15 Q1)
    db: AsyncSession = Depends(get_db),
):
    """StreamingResponse with the real xlsx content-type — deliberately NOT
    the base64-in-JSON shape (plan §10)."""
    org_id = UUID(str(current_user.org_id))
    assessment = await _completed_assessment(db, assessment_id, org_id)
    use_cases = await _load_use_case_dicts(db, assessment_id, org_id)
    content = await run_in_threadpool(mitre_report.build_xlsx_export, assessment, use_cases)
    filename = _sanitize_filename(assessment.name)[:80] or "assessment"
    return StreamingResponse(
        io.BytesIO(content),
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={
            "Content-Disposition": f'attachment; filename="{filename}-attack-coverage.xlsx"'
        },
    )


@router.get("/assessments/{assessment_id}/compare/{other_id}", summary="Trend diff vs an older run")
async def compare_assessments_endpoint(
    assessment_id: UUID,
    other_id: UUID,
    current_user: TokenData = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """{assessment_id} is the run being viewed, {other_id} the baseline.
    Both must belong to the caller's org (cross-org -> 404) and be
    completed (else 409)."""
    org_id = UUID(str(current_user.org_id))
    current = await _completed_assessment(db, assessment_id, org_id)
    baseline = await _completed_assessment(db, other_id, org_id)
    return service.compare_assessments(current, baseline)


@router.get("/settings", summary="Get org MITRE tunables")
async def get_settings(
    current_user: TokenData = Depends(require_role("admin")),
    db: AsyncSession = Depends(get_db),
):
    return await service.get_mitre_settings(db, UUID(str(current_user.org_id)))


@router.patch("/settings", summary="Update org MITRE tunables")
async def patch_settings(
    payload: dict = Body(...),
    current_user: TokenData = Depends(require_role("admin")),
    db: AsyncSession = Depends(get_db),
):
    org_id = UUID(str(current_user.org_id))
    try:
        validated = {key: service.validate_setting(key, value) for key, value in payload.items()}
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc))

    merged = {**(await service.get_mitre_settings(db, org_id)), **validated}
    if merged["confidence_partial_floor"] >= merged["confidence_covered"]:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="confidence_partial_floor must be below confidence_covered",
        )
    for key, value in validated.items():
        await service.set_mitre_setting(db, org_id, key, value)

    await log_action(
        db,
        org_id=org_id,
        user_id=UUID(str(current_user.user_id)),
        action="mitre.settings_updated",
        resource_type="organization",  # org-level config change, not an assessment
        resource_id=org_id,
    )
    await db.commit()
    return await service.get_mitre_settings(db, org_id)


@router.delete("/assessments/{assessment_id}", status_code=status.HTTP_204_NO_CONTENT, summary="Soft-delete assessment")
async def delete_assessment(
    assessment_id: UUID,
    current_user: TokenData = Depends(require_role("admin", "reviewer")),
    db: AsyncSession = Depends(get_db),
):
    org_id = UUID(str(current_user.org_id))
    assessment = await _get_assessment(db, assessment_id, org_id)
    assessment.deleted_at = datetime.now(timezone.utc)
    assessment.updated_at = datetime.now(timezone.utc)
    await db.commit()

    await log_action(
        db,
        org_id=org_id,
        user_id=UUID(str(current_user.user_id)),
        action="mitre.assessment_deleted",
        resource_type="mitre_assessment",  # migration 030
        resource_id=assessment_id,
    )
    await db.commit()
    await invalidate_cache(f"cache:*:{org_id}:*")
    return None
