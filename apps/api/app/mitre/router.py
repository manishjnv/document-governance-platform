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
from sqlalchemy import delete, func, select, update
from sqlalchemy.ext.asyncio import AsyncSession
from starlette.concurrency import run_in_threadpool

from app.compliance.audit import log_action
from app.core.cache import invalidate_cache
from app.db.session import get_db
from app.dependencies import get_current_user, require_role
from app.mitre import attack_data, ingest, navigator, plain_language, ranking, service
from app.mitre.connectors import base as connectors
from app.mitre.connectors import vault
from app.mitre.connectors.base import ConnectorConfigError, ConnectorError
from app.mitre.connectors.egress import EgressError
from app.models.mitre_connection import MitreConnection
from app.mitre import report as mitre_report
from app.mitre import report_common
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

_MAX_CUSTOMER_CHARS = 200


@router.get("/attack/groups", summary="ATT&CK threat groups (static catalog)")
async def list_attack_groups(current_user: TokenData = Depends(get_current_user)):
    """The pinned release's group -> technique catalog for the coverage tab's
    threat-group overlay. Static per ATT&CK version — no org data involved."""
    return {
        "attack_version": attack_data.DEFAULT.version,
        "groups": attack_data.DEFAULT.groups,
    }


def _sanitize_customer(value: Optional[str]) -> Optional[str]:
    """Trim + cap (Phase A12 trend scoping key). Empty means "not set" — the
    JSONB key is omitted rather than stored as ''."""
    if not isinstance(value, str):
        return None
    cleaned = value.strip()[:_MAX_CUSTOMER_CHARS]
    return cleaned or None


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
    # Phase 11: optional threat actors of concern — validated against the
    # curated catalog (the wizard only offers curated names; anything else
    # is a client bug or tampering, so reject rather than silently drop).
    actors = intake.get("threat_actors") or []
    if not isinstance(actors, list) or not all(isinstance(a, str) for a in actors):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="threat_actors must be a list of actor names",
        )
    if len(actors) > 10:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="at most 10 threat actors can be selected",
        )
    # order-preserving dedupe: the UI can't send duplicates, a raw API call can
    actors = list(dict.fromkeys(a.strip() for a in actors if a.strip()))
    known_actors = attack_data.load_threat_profiles()["actors"]
    unknown = sorted(set(actors) - set(known_actors))
    if unknown:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=(
                "Unknown threat actors: "
                + ", ".join(a[:50] for a in unknown[:5])
                + ". Use names from GET /api/v1/mitre/threat-catalog."
            ),
        )
    return {
        # length-capped: these flow into the narrative LLM prompt
        # (2026-08-01 adversarial review, non-blocking finding #5)
        "industry": str(intake.get("industry") or "").strip()[:200] or None,
        "region": str(intake.get("region") or "").strip()[:200] or None,
        "count_disabled_as_coverage": disabled,
        "exclusions": exclusions,
        "threat_actors": actors,
        # Phase 14d: optional project metadata — display-only (header, report
        # cover, XLSX Summary); never sent to any LLM. All optional so
        # pre-14d assessments and minimal API calls behave unchanged.
        "project_name": str(intake.get("project_name") or "").strip()[:200] or None,
        "scope_label": str(intake.get("scope_label") or "").strip()[:200] or None,
        "prepared_by": str(intake.get("prepared_by") or "").strip()[:200] or None,
        "purpose_note": str(intake.get("purpose_note") or "").strip()[:500] or None,
    }


def _build_use_case_rows(parsed_rows: list) -> tuple:
    """Parsed ingest rows -> (models_data, tagged, unmapped, invalid, notes).
    Shared by create and remap so tag validation stays identical."""
    tagged = unmapped = invalid = 0
    models_data, notes = [], []
    for row in parsed_rows:
        mappings, mapping_status, row_notes = service.build_mappings(row["tags"])
        notes.extend(f"{row['row_ref']}: {note}" for note in row_notes)
        if mapping_status == "customer_tagged":
            tagged += 1
        elif mapping_status == "invalid":
            invalid += 1
        else:
            unmapped += 1
        models_data.append(
            {"row": row, "mappings": mappings, "mapping_status": mapping_status}
        )
    return models_data, tagged, unmapped, invalid, notes


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
    customer: Optional[str] = Form(
        None, description="Customer/engagement label — scopes the trend block to same-customer runs (Phase A12)"
    ),
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
            "headers": [],
            "sample_rows": [],
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

    return await _persist_new_assessment(
        db,
        current_user,
        name=name,
        files_to_store=files_to_store,
        parsed=parsed,
        intake_data=intake_data,
        environment_dict=environment_dict,
        env_parsed=env_parsed,
        extraction_text=extraction_text,
        warnings=warnings,
        parse_assumptions=parse_assumptions,
        extra_params=(
            {"customer": clean} if (clean := _sanitize_customer(customer)) else None
        ),
    )


async def _persist_new_assessment(
    db,
    current_user,
    *,
    name,
    files_to_store,
    parsed,
    intake_data,
    environment_dict,
    env_parsed,
    extraction_text,
    warnings,
    parse_assumptions,
    extra_params: dict = None,
):
    """Shared tail of assessment creation (upload AND from-siem): store the
    source file(s), persist the assessment + validated use-case rows, audit,
    and return the parse-preview response. Phase 13a extracted this so the
    SIEM pull reuses tag validation/preview/caps byte-for-byte."""
    org_id = UUID(str(current_user.org_id))
    # user_id may be absent for worker-triggered runs whose connection
    # creator was deleted (created_by SET NULL) — audit tolerates None.
    user_id = (
        UUID(str(current_user.user_id))
        if getattr(current_user, "user_id", None)
        else None
    )
    assessment_id = uuid4()
    storage = await get_storage_instance()

    use_case_models, tagged, unmapped, invalid, row_notes = _build_use_case_rows(
        parsed["rows"]
    )
    parse_assumptions = list(parse_assumptions)
    parse_assumptions.extend(row_notes)

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
        name=(name or "").strip()
        or (files_to_store[0][1] or "MITRE assessment")[:255],
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
                # Phase 14g: per-entry evidence trail from the parser
                "interpretations": env_parsed.get("interpretations", []) if env_parsed else [],
            },
            "parse_assumptions": parse_assumptions,
            "warnings": warnings,
            **({"extraction_text": extraction_text} if extraction_text else {}),
            **(extra_params or {}),
        },
        created_by=user_id,
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
                description=row["description"],
                # Phase 7 (migration 032): logic persisted as its own field —
                # no longer folded into description. Cap stays: an XLSX cell
                # may legally hold 32K chars (2026-08-02 adversarial V2).
                logic=(row["logic"] or "")[:2000] or None,
                log_source=row["log_source"],
                enabled=row["enabled"],
                # Phase A6: optional health columns, already capped/leniently
                # parsed by ingest.py.
                severity=row.get("severity"),
                last_triggered=row.get("last_triggered"),
                mappings=item["mappings"],
                mapping_status=item["mapping_status"],
            )
        )
    await db.commit()

    await log_action(
        db,
        org_id=org_id,
        user_id=user_id,
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
        "headers": parsed["headers"],
        "sample_rows": parsed["sample_rows"],
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


_MAX_SECRET_CHARS = 4096


@router.post(
    "/assessments/from-siem",
    status_code=status.HTTP_201_CREATED,
    summary="Create assessment by pulling rules from a SIEM (Phase 13a)",
)
async def create_assessment_from_siem(
    payload: dict = Body(...),
    current_user: TokenData = Depends(require_role("admin", "reviewer")),
    db: AsyncSession = Depends(get_db),
):
    """Token-at-trigger pull (plan §2.1/§2.2): body =
    {"platform": "sentinel", "config": {...}, "secret": "...", "name"?,
    "intake"?}. The secret is used once for this pull and NEVER persisted,
    logged, or echoed. The connector emits a canonical template CSV that
    runs through the EXACT upload create path (tag validation, preview,
    caps, stored artifact); provenance lands in params.siem."""
    intake_raw = payload.get("intake")
    if intake_raw is not None and not isinstance(intake_raw, dict):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="intake must be a JSON object",
        )
    intake_data = _parse_intake(json.dumps(intake_raw) if intake_raw else None)

    secret = payload.pop("secret", None)  # no reference left on the payload dict
    if not isinstance(secret, str) or not secret.strip():
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="secret is required (it is used once and never stored)",
        )
    if len(secret) > _MAX_SECRET_CHARS:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="secret is implausibly long",
        )

    platform = str(payload.get("platform") or "")
    try:
        return await _create_assessment_from_pull(
            db,
            current_user,
            platform=platform,
            config=payload.get("config"),
            secret=secret,
            name=str(payload.get("name") or ""),
            intake_data=intake_data,
            connection=None,
        )
    finally:
        del secret  # best-effort: no lingering reference in this frame


async def _create_assessment_from_pull(
    db,
    current_user,
    *,
    platform,
    config,
    secret,
    name,
    intake_data,
    connection,
    trigger="manual",
):
    """Shared pull→CSV→create path for token-at-trigger (13a) AND saved
    connections (13b). The secret is a transient argument only — callers
    own its lifetime; nothing here stores, logs, or returns it."""
    try:
        # Blocking network pull — off the event loop (house pattern).
        result = await run_in_threadpool(
            connectors.pull_rules, platform, config, secret
        )
    except ConnectorConfigError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)
        )
    except (ConnectorError, EgressError) as exc:
        # Actionable, secret-free message from the connector layer.
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=str(exc))

    try:
        parsed = await run_in_threadpool(
            ingest.parse_use_case_file, result["csv_bytes"], "csv"
        )
    except ingest.IngestError as exc:  # defensive — our own CSV should parse
        logger.error(f"SIEM pull CSV failed to parse: {exc.detail}")
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="the pulled rules could not be parsed — report this",
        )

    environment_dict = {
        "platforms": [],
        "has_ics_assets": False,
        "has_managed_mobile": False,
        # Phase A7: auto-imported log sources count as "provided" for Log
        # Sources feasibility/cross-check purposes only — NOT for Assets/
        # platform filtering (no platforms are derived here), so the
        # lower-bound coverage assumption stays honest.
        "inventory_provided": False,
        "exclusions": intake_data.get("exclusions", []),
    }
    pulled_at = datetime.now(timezone.utc)
    default_name = f"Sentinel pull {pulled_at.strftime('%Y-%m-%d %H:%M')}"
    config = config or {}
    # Phase A12: auto-stamp the trend-scoping customer key — a saved
    # connection's name (reused across scheduled re-runs) beats the raw
    # workspace, so recurring pulls group naturally without user input.
    customer_clean = _sanitize_customer(
        connection.name if connection is not None else config.get("workspace")
    )

    # Phase A7: best-effort auto-import of onboarded Sentinel data
    # connectors into Log Sources — only when the pull actually derived
    # some (an empty/failed inventory pull is a silent no-op, never an
    # error; there is also no environment-workbook upload path on this
    # endpoint today, so "explicit beats derived" has nothing to merge
    # under yet).
    env_parsed = None
    siem_assumptions = []
    derived_sources = result.get("derived_log_sources") or []
    if derived_sources:
        env_parsed = {
            "log_sources": derived_sources,
            "tooling": [],
            "crown_jewels": [],
            "sheets_found": {"log_sources": "Microsoft Sentinel data connectors (auto-imported)"},
            "interpretations": [
                {"entry": s, "sheet": "Log Sources",
                 "interpretation": "auto-imported from a Sentinel data connector"}
                for s in derived_sources
            ],
        }
        siem_assumptions.append(
            f"log sources auto-imported from Sentinel ({len(derived_sources)} data "
            "connectors) — upload an environment workbook to override"
        )
    unmapped_connectors = result.get("unmapped_connectors") or []
    if unmapped_connectors:
        shown = ", ".join(unmapped_connectors[:10])
        more = f" (+{len(unmapped_connectors) - 10} more)" if len(unmapped_connectors) > 10 else ""
        siem_assumptions.append(
            f"{len(unmapped_connectors)} Sentinel data connector kind(s) not "
            f"recognized (not counted as log sources): {shown}{more}"
        )

    response = await _persist_new_assessment(
        db,
        current_user,
        name=name or default_name,
        files_to_store=[
            (
                "use_cases",
                f"sentinel-pull-{pulled_at.strftime('%Y%m%dT%H%M%SZ')}.csv",
                "csv",
                result["csv_bytes"],
                parsed["row_count"],
            )
        ],
        parsed=parsed,
        intake_data=intake_data,
        environment_dict=environment_dict,
        env_parsed=env_parsed,
        extraction_text=None,
        warnings=list(parsed["warnings"]) + result["warnings"],
        parse_assumptions=[
            f"rules were pulled read-only from Microsoft Sentinel "
            f"({result['rule_count']} rules) rather than uploaded"
        ] + siem_assumptions,
        extra_params={
            **({"customer": customer_clean} if customer_clean else {}),
            "siem": {
                "platform": "sentinel",
                "trigger": trigger,
                "pulled_at": pulled_at.isoformat(),
                "rule_count": result["rule_count"],
                # non-secret workspace reference only — never the secret
                "workspace_ref": {
                    k: str(config.get(k) or "")
                    for k in ("subscription_id", "resource_group", "workspace")
                },
                "stats": result["stats"],
                **(
                    {
                        "connection_id": str(connection.connection_id),
                        "connection_name": connection.name,
                    }
                    if connection is not None
                    else {}
                ),
            }
        },
    )
    response["siem"] = {"platform": "sentinel", "rule_count": result["rule_count"]}
    return response


def _connection_out(connection: MitreConnection) -> dict:
    """API shape for a saved connection. The secret is WRITE-ONLY: no field
    here ever carries it (only the fact that one is set)."""
    return {
        "connection_id": str(connection.connection_id),
        "name": connection.name,
        "platform": connection.platform,
        "config": connection.config,
        "key_version": connection.key_version,
        "secret_set": True,  # a row cannot exist without one (NOT NULL)
        # Phase 13c schedule (null cadence = auto-runs off)
        "schedule_cadence": connection.schedule_cadence,
        "schedule_hour_utc": connection.schedule_hour_utc,
        "schedule_weekday": connection.schedule_weekday,
        "last_scheduled_at": (
            connection.last_scheduled_at.isoformat()
            if connection.last_scheduled_at
            else None
        ),
        "created_at": connection.created_at.isoformat() if connection.created_at else None,
        "updated_at": connection.updated_at.isoformat() if connection.updated_at else None,
    }


def _apply_schedule_fields(connection: MitreConnection, payload: dict) -> None:
    """Validate + apply the Phase 13c schedule trio as a unit. Rules:
    cadence null clears everything; daily needs hour; weekly needs hour +
    weekday; weekday is meaningless outside weekly."""
    cadence = payload.get("schedule_cadence", connection.schedule_cadence)
    hour = payload.get("schedule_hour_utc", connection.schedule_hour_utc)
    weekday = payload.get("schedule_weekday", connection.schedule_weekday)

    def bad(detail):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=detail
        )

    if cadence is None:
        connection.schedule_cadence = None
        connection.schedule_hour_utc = None
        connection.schedule_weekday = None
        return
    if cadence not in ("daily", "weekly"):
        bad("schedule_cadence must be null, 'daily' or 'weekly'")
    if not isinstance(hour, int) or isinstance(hour, bool) or not 0 <= hour <= 23:
        bad("schedule_hour_utc must be an integer 0-23")
    if cadence == "weekly":
        if not isinstance(weekday, int) or isinstance(weekday, bool) or not 0 <= weekday <= 6:
            bad("schedule_weekday must be an integer 0-6 (0=Monday) for weekly schedules")
    else:
        weekday = None
    connection.schedule_cadence = cadence
    connection.schedule_hour_utc = hour
    connection.schedule_weekday = weekday


async def _get_connection(db, connection_id: UUID, org_id) -> MitreConnection:
    result = await db.execute(
        select(MitreConnection).where(
            (MitreConnection.connection_id == connection_id)
            & (MitreConnection.org_id == org_id)
            & (MitreConnection.deleted_at.is_(None))
        )
    )
    connection = result.scalar_one_or_none()
    if connection is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Connection not found"
        )
    return connection


def _validate_connection_secret(secret) -> str:
    if not isinstance(secret, str) or not secret.strip():
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="secret is required (it is stored encrypted and never shown again)",
        )
    if len(secret) > _MAX_SECRET_CHARS:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="secret is implausibly long",
        )
    return secret


def _encrypt_or_503(secret: str, *, aad: str) -> tuple:
    try:
        return vault.encrypt_secret(secret, aad=aad)
    except vault.VaultError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(exc)
        )


def _decrypt_or_error(connection: MitreConnection) -> str:
    """Decrypt for immediate in-process connector use ONLY — the caller
    must del the value after the pull and never log/store/return it."""
    try:
        return vault.decrypt_secret(
            connection.secret_ciphertext,
            connection.key_version,
            aad=str(connection.connection_id),
        )
    except vault.VaultError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(exc)
        )


def _validated_platform_config(payload: dict) -> tuple:
    platform = str(payload.get("platform") or "")
    if platform != "sentinel":
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Unknown SIEM platform {platform[:30]!r}. Supported: sentinel",
        )
    from app.mitre.connectors import sentinel

    try:
        return platform, sentinel.validate_config(payload.get("config"))
    except ConnectorConfigError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)
        )


@router.get("/connections", summary="List saved SIEM connections + health (Phase 13b/13d)")
async def list_connections(
    current_user: TokenData = Depends(require_role("admin")),
    db: AsyncSession = Depends(get_db),
):
    from app.mitre.tasks import connection_health

    result = await db.execute(
        select(MitreConnection)
        .where(
            (MitreConnection.org_id == UUID(str(current_user.org_id)))
            & (MitreConnection.deleted_at.is_(None))
        )
        .order_by(MitreConnection.created_at.desc())
    )
    out = []
    for connection in result.scalars().all():
        # Phase 13d: last pull/error + scheduled-failure streak per row.
        # Per-connection query is fine at admin-view scale.
        out.append(
            {**_connection_out(connection), "health": await connection_health(db, connection)}
        )
    return out


@router.post("/connections", status_code=status.HTTP_201_CREATED, summary="Save a SIEM connection (secret stored encrypted)")
async def create_connection(
    payload: dict = Body(...),
    current_user: TokenData = Depends(require_role("admin")),
    db: AsyncSession = Depends(get_db),
):
    """Body = {"platform": "sentinel", "config": {...}, "secret": "...",
    "name"?}. The secret is AES-256-GCM-encrypted at rest (vault.py) and
    WRITE-ONLY from here on: no endpoint ever returns it."""
    org_id = UUID(str(current_user.org_id))
    platform, config = _validated_platform_config(payload)
    secret = _validate_connection_secret(payload.pop("secret", None))

    connection_id = uuid4()
    ciphertext, key_version = _encrypt_or_503(secret, aad=str(connection_id))
    del secret
    # collapse ALL whitespace incl. CRLF — the name reaches an email
    # Subject header in 13d (header-injection hardening)
    clean_name = " ".join(str(payload.get("name") or "").split())
    connection = MitreConnection(
        connection_id=connection_id,
        org_id=org_id,
        name=(clean_name or f"Sentinel · {config['workspace']}")[:255],
        platform=platform,
        config=config,
        secret_ciphertext=ciphertext,
        key_version=key_version,
        created_by=UUID(str(current_user.user_id)),
    )
    db.add(connection)
    await db.commit()

    await log_action(
        db,
        org_id=org_id,
        user_id=UUID(str(current_user.user_id)),
        action="mitre.connection_created",
        resource_type="organization",  # org-level config, like mitre.settings_updated
        resource_id=connection_id,
    )
    await db.commit()
    return _connection_out(connection)


@router.patch("/connections/{connection_id}", summary="Update a SIEM connection (secret replace-only)")
async def update_connection(
    connection_id: UUID,
    payload: dict = Body(...),
    current_user: TokenData = Depends(require_role("admin")),
    db: AsyncSession = Depends(get_db),
):
    """name/config/secret each optional; a supplied secret REPLACES the old
    one (there is no way to read either). Config is revalidated whole."""
    org_id = UUID(str(current_user.org_id))
    connection = await _get_connection(db, connection_id, org_id)

    if "config" in payload:
        _, connection.config = _validated_platform_config(
            {"platform": connection.platform, "config": payload["config"]}
        )
    if "name" in payload:
        # whitespace-collapsed incl. CRLF (email Subject hardening, 13d)
        name = " ".join(str(payload.get("name") or "").split())
        if name:
            connection.name = name[:255]
    if "secret" in payload:
        secret = _validate_connection_secret(payload.pop("secret", None))
        connection.secret_ciphertext, connection.key_version = _encrypt_or_503(
            secret, aad=str(connection.connection_id)
        )
        del secret
    if any(
        k in payload
        for k in ("schedule_cadence", "schedule_hour_utc", "schedule_weekday")
    ):
        _apply_schedule_fields(connection, payload)
    connection.updated_at = datetime.now(timezone.utc)
    await db.commit()

    await log_action(
        db,
        org_id=org_id,
        user_id=UUID(str(current_user.user_id)),
        action="mitre.connection_updated",
        resource_type="organization",
        resource_id=connection_id,
    )
    await db.commit()
    return _connection_out(connection)


@router.delete("/connections/{connection_id}", status_code=status.HTTP_204_NO_CONTENT, summary="Delete a SIEM connection")
async def delete_connection(
    connection_id: UUID,
    current_user: TokenData = Depends(require_role("admin")),
    db: AsyncSession = Depends(get_db),
):
    org_id = UUID(str(current_user.org_id))
    connection = await _get_connection(db, connection_id, org_id)
    connection.deleted_at = datetime.now(timezone.utc)
    connection.updated_at = datetime.now(timezone.utc)
    await db.commit()

    await log_action(
        db,
        org_id=org_id,
        user_id=UUID(str(current_user.user_id)),
        action="mitre.connection_deleted",
        resource_type="organization",
        resource_id=connection_id,
    )
    await db.commit()
    return None


@router.post("/connections/{connection_id}/test", summary="Dry-run a saved connection (rule count only)")
async def test_connection(
    connection_id: UUID,
    current_user: TokenData = Depends(require_role("admin")),
    db: AsyncSession = Depends(get_db),
):
    """Decrypts in-process, pulls, and reports the reachable rule count —
    creates nothing, returns no rule content and never the secret."""
    org_id = UUID(str(current_user.org_id))
    connection = await _get_connection(db, connection_id, org_id)
    secret = _decrypt_or_error(connection)
    try:
        result = await run_in_threadpool(
            connectors.pull_rules, connection.platform, connection.config, secret
        )
    except ConnectorConfigError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc))
    except (ConnectorError, EgressError) as exc:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=str(exc))
    finally:
        del secret

    await log_action(
        db,
        org_id=org_id,
        user_id=UUID(str(current_user.user_id)),
        action="mitre.connection_tested",
        resource_type="organization",
        resource_id=connection_id,
    )
    await db.commit()
    return {"ok": True, "rule_count": result["rule_count"], "warnings": result["warnings"]}


@router.post(
    "/assessments/from-connection/{connection_id}",
    status_code=status.HTTP_201_CREATED,
    summary="Create assessment from a saved SIEM connection (Phase 13b)",
)
async def create_assessment_from_connection(
    connection_id: UUID,
    payload: dict = Body(default={}),
    current_user: TokenData = Depends(require_role("admin", "reviewer")),
    db: AsyncSession = Depends(get_db),
):
    """Same pipeline as /assessments/from-siem, but the secret comes from
    the encrypted vault (decrypted in-process for this pull only). Body =
    {"name"?, "intake"?}."""
    org_id = UUID(str(current_user.org_id))
    connection = await _get_connection(db, connection_id, org_id)

    intake_raw = payload.get("intake")
    if intake_raw is not None and not isinstance(intake_raw, dict):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="intake must be a JSON object",
        )
    intake_data = _parse_intake(json.dumps(intake_raw) if intake_raw else None)

    secret = _decrypt_or_error(connection)
    try:
        return await _create_assessment_from_pull(
            db,
            current_user,
            platform=connection.platform,
            config=connection.config,
            secret=secret,
            name=str(payload.get("name") or ""),
            intake_data=intake_data,
            connection=connection,
        )
    finally:
        del secret


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


@router.post("/assessments/{assessment_id}/remap", summary="Re-parse the dump with an explicit column mapping")
async def remap_assessment_columns(
    assessment_id: UUID,
    payload: dict = Body(...),
    current_user: TokenData = Depends(require_role("admin", "reviewer")),
    db: AsyncSession = Depends(get_db),
):
    """Phase 9 wizard: body = {"columns": {field: 0-based column index}}.
    Re-parses the STORED use-case dump with the user's mapping (auto-
    detection bypassed), replaces the parsed rows, and returns a fresh
    parse preview. Only while status is 'pending' — a run freezes the rows."""
    import re as _re

    org_id = UUID(str(current_user.org_id))
    assessment = await _get_assessment(db, assessment_id, org_id)
    if assessment.status != "pending":
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Columns can only be adjusted before the assessment runs.",
        )

    files = (
        await db.execute(
            select(MitreFile).where(
                (MitreFile.assessment_id == assessment_id)
                & (MitreFile.org_id == org_id)
                & (MitreFile.deleted_at.is_(None))
            )
        )
    ).scalars().all()
    uc_file = next((f for f in files if f.kind == "use_cases"), None)
    if uc_file is None or uc_file.file_type not in ("xlsx", "xls", "csv"):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Column mapping applies to spreadsheet dumps only.",
        )

    storage = await get_storage_instance()
    try:
        content = await storage.download(uc_file.s3_path)
    except Exception as exc:  # noqa: BLE001
        logger.error(f"MITRE remap download failed: {exc}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Could not load the stored file",
        )
    try:
        # CPU-bound parse off the event loop (house pattern: report/xlsx
        # builders in this file do the same).
        parsed = await run_in_threadpool(
            ingest.parse_use_case_file,
            content,
            uc_file.file_type,
            payload.get("columns"),
        )
    except ingest.IngestError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=exc.detail
        )

    use_case_models, tagged, unmapped, invalid, row_notes = _build_use_case_rows(
        parsed["rows"]
    )

    # TOCTOU guard: the pending-check above ran BEFORE the (slow) download
    # + parse — a concurrent /run could have started the pipeline since.
    # This conditional UPDATE re-asserts 'pending' atomically in the same
    # transaction as the row replacement: 0 rows -> a run won the race.
    guard = await db.execute(
        update(MitreAssessment)
        .where(
            (MitreAssessment.assessment_id == assessment_id)
            & (MitreAssessment.org_id == org_id)
            & (MitreAssessment.status == "pending")
        )
        .values(updated_at=datetime.now(timezone.utc))
    )
    if guard.rowcount == 0:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Columns can only be adjusted before the assessment runs.",
        )

    # Replace the parse artifacts wholesale (assessment is pending — rows
    # only exist as preview state until a run freezes them).
    await db.execute(
        delete(MitreUseCase).where(
            (MitreUseCase.assessment_id == assessment_id)
            & (MitreUseCase.org_id == org_id)
        )
    )
    for item in use_case_models:
        row = item["row"]
        db.add(
            MitreUseCase(
                use_case_id=uuid4(),
                assessment_id=assessment_id,
                org_id=org_id,
                file_id=uc_file.file_id,
                row_ref=row["row_ref"],
                name=row["name"],
                description=row["description"],
                logic=(row["logic"] or "")[:2000] or None,
                log_source=row["log_source"],
                enabled=row["enabled"],
                # Phase A6: optional health columns, already capped/leniently
                # parsed by ingest.py.
                severity=row.get("severity"),
                last_triggered=row.get("last_triggered"),
                mappings=item["mappings"],
                mapping_status=item["mapping_status"],
            )
        )

    params = dict(assessment.params or {})
    # parse_assumptions mixes env-workbook notes with per-row tag notes;
    # row notes are "<sheet>:<row>: ..." — drop the stale ones, keep env.
    old_sheet = params.get("sheet")
    kept = [
        a
        for a in params.get("parse_assumptions", [])
        if not (old_sheet and _re.match(rf"^{_re.escape(old_sheet)}:\d+: ", a))
    ]
    params.update(
        {
            "columns": parsed["columns"],
            "sheet": parsed["sheet"],
            "parse_assumptions": kept + row_notes,
            "warnings": parsed["warnings"],
        }
    )
    assessment.params = params
    assessment.updated_at = datetime.now(timezone.utc)
    uc_file.parse_status = "parsed"
    uc_file.row_count = parsed["row_count"]
    await db.commit()

    await log_action(
        db,
        org_id=org_id,
        user_id=UUID(str(current_user.user_id)),
        action="mitre.assessment_remapped",
        resource_type="mitre_assessment",
        resource_id=assessment_id,
    )
    await db.commit()
    await invalidate_cache(f"cache:*:{org_id}:*")

    environment_dict = params.get("environment") or {}
    return {
        "assessment_id": str(assessment_id),
        "name": assessment.name,
        "status": assessment.status,
        "attack_version": assessment.attack_version,
        "row_count": parsed["row_count"],
        "columns": parsed["columns"],
        "sheet": parsed["sheet"],
        "headers": parsed["headers"],
        "sample_rows": parsed["sample_rows"],
        "tagged": tagged,
        "untagged": unmapped,
        "invalid": invalid,
        "extraction_pending": False,
        "environment_provided": any(f.kind == "environment" for f in files),
        "environment": environment_dict,
        "sheets_found": params.get("environment_lists", {}).get("sheets_found", {}),
        "warnings": parsed["warnings"],
        "assumptions": kept + row_notes,
    }


@router.get("/assessments", summary="List assessments")
async def list_assessments(
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    include_archived: bool = Query(False),
    current_user: TokenData = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    conditions = (
        (MitreAssessment.org_id == UUID(str(current_user.org_id)))
        & (MitreAssessment.deleted_at.is_(None))
    )
    if not include_archived:
        # Phase 14f soft archive flag rides the params JSONB (no migration).
        conditions = conditions & (
            MitreAssessment.params["archived"].astext.is_(None)
            | (MitreAssessment.params["archived"].astext != "true")
        )
    result = await db.execute(
        select(MitreAssessment)
        .where(conditions)
        .order_by(MitreAssessment.created_at.desc())
        .offset(skip)
        .limit(limit)
    )
    items = []
    for a in result.scalars().all():
        summary = a.summary or {}
        overall = summary.get("overall", {})
        siem = (a.params or {}).get("siem") or {}
        items.append(
            {
                "assessment_id": str(a.assessment_id),
                "name": a.name,
                "status": a.status,
                # Phase 14f: archive flag + 14d project name on list rows
                "archived": bool((a.params or {}).get("archived")),
                "project_name": ((a.params or {}).get("intake") or {}).get("project_name"),
                # Phase A12: trend-scoping customer label, shown alongside the name
                "customer": (a.params or {}).get("customer"),
                # Phase 13d provenance chip: platform + trigger only
                "siem": (
                    {"platform": siem.get("platform"), "trigger": siem.get("trigger")}
                    if siem
                    else None
                ),
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


@router.patch("/assessments/{assessment_id}", summary="Rename / archive an assessment (Phase 14f)")
async def update_assessment(
    assessment_id: UUID,
    payload: dict = Body(...),
    current_user: TokenData = Depends(require_role("admin", "reviewer")),
    db: AsyncSession = Depends(get_db),
):
    """Housekeeping only: {"name"?: str, "archived"?: bool}. Archive is a
    soft JSONB flag — hidden from the default list, still selectable in
    Compare; there is deliberately no delete here."""
    org_id = UUID(str(current_user.org_id))
    assessment = await _get_assessment(db, assessment_id, org_id)

    if "name" in payload:
        new_name = str(payload.get("name") or "").strip()
        if not new_name or len(new_name) > 255:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="name must be 1-255 characters",
            )
        assessment.name = new_name
    if "archived" in payload:
        if not isinstance(payload["archived"], bool):
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="archived must be true/false",
            )
        params = dict(assessment.params or {})
        params["archived"] = payload["archived"]
        assessment.params = params
    if "name" not in payload and "archived" not in payload:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="nothing to update — send name and/or archived",
        )
    assessment.updated_at = datetime.now(timezone.utc)
    await db.commit()
    await log_action(
        db,
        org_id=org_id,
        user_id=UUID(str(current_user.user_id)),
        action="mitre.assessment_updated",
        resource_type="mitre_assessment",
        resource_id=assessment_id,
    )
    await db.commit()
    await invalidate_cache(f"cache:*:{org_id}:*")
    return {
        "assessment_id": str(assessment.assessment_id),
        "name": assessment.name,
        "archived": bool((assessment.params or {}).get("archived")),
    }


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

    # Phase 14b: enrich stored results with technique names at read time
    # (drill-down panels need names for non-gap techniques; names live in the
    # pinned index, never in the JSONB — computed, not stored).
    technique_results = assessment.technique_results
    if technique_results:
        technique_results = [
            {
                **r,
                "name": (attack_data.DEFAULT.get(r.get("technique_id")) or {}).get("name"),
                # platforms feed the on-page search ("is linux/asset X covered?")
                "platforms": (attack_data.DEFAULT.get(r.get("technique_id")) or {}).get("platforms") or [],
            }
            for r in technique_results
        ]

    # Phase 14d: the uploaded files behind this assessment (feeds the
    # "what this assessment is based on" card; exists for all assessments).
    files_result = await db.execute(
        select(MitreFile).where(
            (MitreFile.assessment_id == assessment_id)
            & (MitreFile.org_id == UUID(str(current_user.org_id)))
            & (MitreFile.deleted_at.is_(None))
        )
    )
    files = [
        {
            "kind": f.kind,
            "filename": f.filename,
            "file_type": f.file_type,
            "row_count": f.row_count,
        }
        for f in files_result.scalars().all()
    ]

    # Phase A10 piece 3: "coverage by log source" grouping — computed at
    # read time from the same stored data every other view uses (no
    # pipeline change); only worth the extra query once the run is
    # complete (polling while running never reaches this branch).
    log_source_coverage = None
    if assessment.status == "completed":
        use_cases = await _load_use_case_dicts(
            db, assessment_id, UUID(str(current_user.org_id))
        )
        log_source_coverage = report_common.compute_log_source_coverage(
            use_cases, assessment.technique_results or [], attack_data.DEFAULT
        )

    return {
        "files": files,
        "assessment_id": str(assessment.assessment_id),
        "name": assessment.name,
        "status": assessment.status,
        "attack_version": assessment.attack_version,
        "params": assessment.params,
        "summary": assessment.summary,
        "technique_results": technique_results,
        "log_source_coverage": log_source_coverage,
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


def _closest_covered_rule(technique_id, result, results, use_cases, index):
    """A starting-point rule the SIEM team can copy (Phase 14a): the first
    covered sibling sub-technique / parent / same-tactic technique that has
    mapped rules. Deterministic; None when nothing qualifies."""
    if result.get("state") == "covered":
        return None
    by_id = {r.get("technique_id"): r for r in results}
    name_by_ref = {uc["row_ref"]: uc["name"] for uc in use_cases}
    tech = index.get(technique_id) or {}
    candidates = []
    parent = tech.get("parent_id")
    if parent:
        candidates.extend(
            c["id"] for c in index.children.get(parent, []) if c["id"] != technique_id
        )
        candidates.append(parent)
    else:
        candidates.extend(c["id"] for c in index.children.get(technique_id, []))
    tactics = set(result.get("tactics") or [])
    candidates.extend(
        r["technique_id"]
        for r in results
        if r.get("domain") == result.get("domain")
        and r.get("state") == "covered"
        and tactics & set(r.get("tactics") or [])
    )
    for candidate_id in candidates:
        candidate = by_id.get(candidate_id)
        if not candidate or candidate.get("state") != "covered":
            continue
        for ref in candidate.get("use_case_refs") or []:
            rule_name = name_by_ref.get(ref)
            if rule_name:
                return {
                    "technique_id": candidate_id,
                    "technique_name": (index.get(candidate_id) or {}).get("name"),
                    "rule_name": rule_name,
                }
    return None


@router.get(
    "/assessments/{assessment_id}/techniques/{technique_id}/explain",
    summary="Plain-language four-block explanation for one technique (Phase 14a)",
)
async def explain_technique(
    assessment_id: UUID,
    technique_id: str,
    current_user: TokenData = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """What is this / where is the gap / why / what would good look like —
    all deterministic: curated data files + stored result data. No LLM."""
    org_id = UUID(str(current_user.org_id))
    assessment = await _completed_assessment(db, assessment_id, org_id)
    results = assessment.technique_results or []
    result = next(
        (r for r in results if r.get("technique_id") == technique_id), None
    )
    if result is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Technique not found in this assessment",
        )
    index = attack_data.DEFAULT
    tech = index.get(technique_id) or {}
    summary = assessment.summary or {}
    params = assessment.params or {}

    use_cases = await _load_use_case_dicts(db, assessment_id, org_id)
    mapped = []
    for uc in use_cases:
        mapping = next(
            (m for m in uc["mappings"] if m.get("technique_id") == technique_id),
            None,
        )
        if mapping:
            mapped.append(
                {
                    "name": uc["name"],
                    "enabled": uc["enabled"],
                    "source": mapping.get("source"),
                    "confidence": mapping.get("confidence"),
                }
            )

    # Parent-rollup case: partial with no direct rules -> list sub states.
    sub_states = plain_language.sub_states_for(
        result,
        mapped,
        {r.get("technique_id"): r.get("state") for r in results},
        index,
    )

    thresholds = params.get("thresholds") or {}
    why = plain_language.derive_why(
        result,
        mapped,
        total_rules=(summary.get("counts") or {}).get("use_cases"),
        sub_states=sub_states,
        confidence_covered=thresholds.get("confidence_covered", 0.7),
    )

    gap = next(
        (g for g in summary.get("gaps") or [] if g.get("technique_id") == technique_id),
        None,
    )
    if gap:
        feasibility, via, hint = gap.get("feasibility"), gap.get("via"), gap.get("hint")
    else:
        env_lists = params.get("environment_lists") or {}
        feasibility, via, _category, hint = ranking.technique_feasibility(
            tech, env_lists.get("log_sources") or [], env_lists.get("tooling") or []
        )

    # Phase 14g: evidence for "why is this technique in scope for you" —
    # the environment entries whose parsed interpretation put its domain or
    # platforms in play (empty for pre-14g assessments).
    env_lists = params.get("environment_lists") or {}
    interpretations = env_lists.get("interpretations") or []
    platforms = tech.get("platforms") or []
    domain_markers = {
        "ics": "enabled the ICS/OT matrix",
        "mobile": "enabled the Mobile matrix",
    }
    in_scope_because = [
        {"entry": i.get("entry"), "interpretation": i.get("interpretation")}
        for i in interpretations
        if (
            any(f"counted as platform {p}" in (i.get("interpretation") or "") for p in platforms)
            or domain_markers.get(result.get("domain"), "\x00") in (i.get("interpretation") or "")
        )
    ][:5]

    described = plain_language.describe_technique(technique_id, index)
    tactic_by_id = {t["id"]: t for t in index.tactics(result.get("domain"))}
    tactic_lines = [
        {
            "id": tid,
            "name": tactic_by_id[tid]["name"],
            "line": plain_language.TACTIC_LINES.get(tactic_by_id[tid]["shortname"]),
        }
        for tid in result.get("tactics") or []
        if tid in tactic_by_id
    ]

    return {
        "technique_id": technique_id,
        "name": tech.get("name"),
        "state": result.get("state"),
        "what": {
            "definition": described["definition"],
            "attacker_use": described["attacker_use"],
            "curated": described["curated"],
        },
        "where": {
            "domain": result.get("domain"),
            "tactics": tactic_lines,
            "platforms": tech.get("platforms") or [],
            "via": via,
            "feasibility": feasibility,
            "feasibility_hint": hint,
            # Phase 14g evidence trail
            "expected_telemetry": tech.get("data_sources") or [],
            "in_scope_because": in_scope_because,
        },
        "why": why,
        "good": {
            "sketch": plain_language.detection_sketch(technique_id, via),
            "detection_hint": described["detection_hint"],
            "closest_rule": _closest_covered_rule(
                technique_id, result, results, use_cases, index
            ),
            # Phase 14h: per-data-source-component query field guidance.
            "telemetry": plain_language.telemetry_requirements(technique_id, index),
        },
    }


_MAX_MAPPINGS_PER_RULE = 20  # a rule genuinely mapping to more is noise


@router.patch(
    "/assessments/{assessment_id}/use-cases/{use_case_id}/mappings",
    summary="Manually correct one rule's technique mappings",
)
async def edit_use_case_mappings(
    assessment_id: UUID,
    use_case_id: UUID,
    payload: dict = Body(...),
    current_user: TokenData = Depends(require_role("admin", "reviewer")),
    db: AsyncSession = Depends(get_db),
):
    """Phase 10: reviewer override of a rule's mappings. Body =
    {"technique_ids": [...]} — the FULL new list for the rule (empty list =
    "this rule maps to nothing"). Every ID is validated through
    attack_data.resolve(); the row gets mapping_status='manual' with each
    mapping source='manual' @ confidence 1.0, and coverage/gaps/roadmap are
    recomputed inline from the pure engines (no LLM). Only on completed
    assessments — before a run there is nothing to recompute, and a running
    pipeline would overwrite the edit."""
    org_id = UUID(str(current_user.org_id))

    ids = payload.get("technique_ids")
    if not isinstance(ids, list) or not all(isinstance(t, str) for t in ids):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="technique_ids must be a list of ATT&CK technique ID strings",
        )
    if len(ids) > _MAX_MAPPINGS_PER_RULE:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"a rule can map to at most {_MAX_MAPPINGS_PER_RULE} techniques",
        )

    index = attack_data.DEFAULT
    canonical_ids, invalid_ids, notes = [], [], []
    for raw in ids:
        canonical, resolve_status = index.resolve(raw.strip().upper())
        if resolve_status in ("malformed", "unknown", "deprecated"):
            invalid_ids.append(raw)
            continue
        if resolve_status == "remapped":
            notes.append(
                f"'{raw}' is revoked in ATT&CK v{index.version} — "
                f"remapped to {canonical}"
            )
        if canonical not in canonical_ids:
            canonical_ids.append(canonical)
    if invalid_ids:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=(
                f"Not valid ATT&CK v{index.version} technique IDs: "
                + ", ".join(str(t)[:20] for t in invalid_ids[:10])
            ),
        )

    # Row lock: serializes concurrent edits on the same assessment so the
    # recompute below always sees a consistent full row set.
    result = await db.execute(
        select(MitreAssessment)
        .where(
            (MitreAssessment.assessment_id == assessment_id)
            & (MitreAssessment.org_id == org_id)
            & (MitreAssessment.deleted_at.is_(None))
        )
        .with_for_update()
    )
    assessment = result.scalar_one_or_none()
    if assessment is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Assessment not found"
        )
    if assessment.status != "completed":
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Mappings can be edited once the assessment has completed",
        )

    uc_result = await db.execute(
        select(MitreUseCase).where(
            (MitreUseCase.use_case_id == use_case_id)
            & (MitreUseCase.assessment_id == assessment_id)
            & (MitreUseCase.org_id == org_id)
            & (MitreUseCase.deleted_at.is_(None))
        )
    )
    use_case = uc_result.scalar_one_or_none()
    if use_case is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Use case not found"
        )

    use_case.mappings = [
        {"technique_id": tid, "source": "manual", "confidence": 1.0}
        for tid in canonical_ids
    ]
    use_case.mapping_status = "manual"
    use_case.updated_at = datetime.now(timezone.utc)

    rows = await db.execute(
        select(MitreUseCase)
        .where(
            (MitreUseCase.assessment_id == assessment_id)
            & (MitreUseCase.org_id == org_id)
            & (MitreUseCase.deleted_at.is_(None))
        )
        .order_by(MitreUseCase.row_ref)
    )
    service.recompute_results(assessment, rows.scalars().all())
    await db.commit()

    await log_action(
        db,
        org_id=org_id,
        user_id=UUID(str(current_user.user_id)),
        action="mitre.mappings_edited",
        resource_type="mitre_assessment",  # migration 030
        resource_id=assessment_id,
    )
    await db.commit()
    await invalidate_cache(f"cache:*:{org_id}:*")

    return {
        "use_case": {
            "use_case_id": str(use_case.use_case_id),
            "row_ref": use_case.row_ref,
            "name": use_case.name,
            "description": use_case.description,
            "log_source": use_case.log_source,
            "enabled": use_case.enabled,
            "mappings": use_case.mappings,
            "mapping_status": use_case.mapping_status,
        },
        "notes": notes,
        "overall": (assessment.summary or {}).get("overall"),
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
            "logic": uc.logic,
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
    scope: str = Query("full", description="full | executive (1-3 page leadership summary) | coverage | gaps | assumptions (single tab)"),
    current_user: TokenData = Depends(get_current_user),  # viewers may read (plan §15 Q1)
    db: AsyncSession = Depends(get_db),
):
    """Mirrors reviews.py's report shape: {"format", "data"} with PDF as
    base64-in-JSON so the existing frontend blob pattern works."""
    if scope not in ("full", "executive", "coverage", "gaps", "assumptions"):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="scope must be one of: full, executive, coverage, gaps, assumptions",
        )
    org_id = UUID(str(current_user.org_id))
    assessment = await _completed_assessment(db, assessment_id, org_id)
    use_cases = await _load_use_case_dicts(db, assessment_id, org_id)
    files_result = await db.execute(
        select(MitreFile).where(
            (MitreFile.assessment_id == assessment_id)
            & (MitreFile.org_id == org_id)
            & (MitreFile.deleted_at.is_(None))
        )
    )
    report_files = [
        {"kind": f.kind, "filename": f.filename, "row_count": f.row_count}
        for f in files_result.scalars().all()
    ]
    # Phase 14e: trend block — diff against the most recent completed run
    # before this one, when one exists (pure compare, no extra cost at scale).
    # Phase A12: scoped to the same customer (NULL-safe — orgs with no
    # customer set on either run still match, preserving pre-A12 behavior).
    assessment_customer = (assessment.params or {}).get("customer")
    previous_result = await db.execute(
        select(MitreAssessment)
        .where(
            (MitreAssessment.org_id == org_id)
            & (MitreAssessment.status == "completed")
            & (MitreAssessment.assessment_id != assessment_id)
            & (MitreAssessment.completed_at < assessment.completed_at)
            & (MitreAssessment.deleted_at.is_(None))
            & (MitreAssessment.params["customer"].astext.is_not_distinct_from(assessment_customer))
        )
        .order_by(MitreAssessment.completed_at.desc())
        .limit(1)
    )
    previous = previous_result.scalars().first()
    compare = None
    if previous is not None:
        try:
            compare = service.compare_assessments(assessment, previous)
            compare["baseline_name"] = previous.name
            compare["baseline_completed_at"] = (
                previous.completed_at.isoformat() if previous.completed_at else None
            )
        except Exception:  # noqa: BLE001 — trend is optional decoration
            compare = None
    # Phase 14h: per-org report branding (display name/accent/watermark) —
    # backend keys only, no admin UI, merged over platform defaults.
    settings = await service.get_mitre_settings(db, org_id)
    branding = {
        "report_display_name": settings["report_display_name"],
        "report_accent_color": settings["report_accent_color"],
        "report_watermark_text": settings["report_watermark_text"],
    }
    # Report/xlsx generation is CPU-bound and unbounded on large assessments;
    # offload so it can't stall the single-worker event loop (2026-08-02
    # adversarial review, non-blocking finding #2).
    html = await run_in_threadpool(
        mitre_report.build_html_report, assessment, use_cases, compare,
        report_files, scope, branding,
    )

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
    scope: str = Query("full", description="full | coverage | gaps | assumptions (single tab's sheets)"),
    current_user: TokenData = Depends(get_current_user),  # viewers may download (plan §15 Q1)
    db: AsyncSession = Depends(get_db),
):
    """StreamingResponse with the real xlsx content-type — deliberately NOT
    the base64-in-JSON shape (plan §10)."""
    if scope not in ("full", "coverage", "gaps", "assumptions"):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="scope must be one of: full, coverage, gaps, assumptions",
        )
    org_id = UUID(str(current_user.org_id))
    assessment = await _completed_assessment(db, assessment_id, org_id)
    use_cases = await _load_use_case_dicts(db, assessment_id, org_id)
    settings = await service.get_mitre_settings(db, org_id)
    branding = {
        "report_display_name": settings["report_display_name"],
        "report_accent_color": settings["report_accent_color"],
        "report_watermark_text": settings["report_watermark_text"],
    }
    content = await run_in_threadpool(
        mitre_report.build_xlsx_export, assessment, use_cases, scope, branding
    )
    filename = _sanitize_filename(assessment.name)[:80] or "assessment"
    suffix = "attack-coverage" if scope == "full" else scope
    return StreamingResponse(
        io.BytesIO(content),
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={
            "Content-Disposition": f'attachment; filename="{filename}-{suffix}.xlsx"'
        },
    )


@router.get("/assessments/{assessment_id}/navigator", summary="ATT&CK Navigator layer export (json/zip)")
async def assessment_navigator_export(
    assessment_id: UUID,
    current_user: TokenData = Depends(get_current_user),  # viewers may download (report policy)
    db: AsyncSession = Depends(get_db),
):
    """One Navigator 4.5 layer per applicable domain (Phase 8): a single
    applicable domain downloads as plain layer JSON; multiple domains as a
    zip with one layer file each. Open at mitre-attack.github.io/attack-navigator."""
    import zipfile

    org_id = UUID(str(current_user.org_id))
    assessment = await _completed_assessment(db, assessment_id, org_id)
    layers = navigator.build_navigator_layers(assessment)
    if not layers:  # defensive — completed assessments always have >=1 domain
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="No applicable domains to export",
        )
    base = _sanitize_filename(assessment.name)[:80] or "assessment"

    if len(layers) == 1:
        domain, layer = layers[0]
        return StreamingResponse(
            io.BytesIO(json.dumps(layer, indent=2).encode("utf-8")),
            media_type="application/json",
            headers={
                "Content-Disposition": f'attachment; filename="{base}-navigator-{domain}.json"'
            },
        )

    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        for domain, layer in layers:
            zf.writestr(f"{base}-navigator-{domain}.json", json.dumps(layer, indent=2))
    buf.seek(0)
    return StreamingResponse(
        buf,
        media_type="application/zip",
        headers={
            "Content-Disposition": f'attachment; filename="{base}-navigator-layers.zip"'
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


@router.get("/threat-catalog", summary="Curated threat actors + profiled industries (Phase 11)")
async def threat_catalog(
    current_user: TokenData = Depends(get_current_user),
):
    """The curated threat_profiles.json surface the wizard needs: selectable
    actor names (with ATT&CK group IDs for reference) and which industries
    carry a profile. Static curated data — no per-org content."""
    profiles = attack_data.load_threat_profiles()
    return {
        "actors": [
            {"name": name, "attack_id": entry.get("attack_id"), "note": entry.get("note")}
            for name, entry in profiles["actors"].items()
        ],
        "industries": sorted(
            entry["label"] for entry in profiles["industries"].values()
        ),
    }


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
