"""MITRE assessment pipeline driver + org tunables (Phase 1, tagged-only).

Pipeline stages at run time: applicability -> coverage -> persist. Tag
validation happens at CREATE time (router) so the parse preview can report
the tagged/untagged/invalid split; its assumption lines ride in
params["parse_assumptions"] and are merged into the final summary here.

AI tagging and narrative are Phase 2 — untagged rows stay 'unmapped' with an
assumption line.
"""

import json
import logging
from datetime import datetime, timezone
from uuid import UUID

from sqlalchemy import select, text

from app.compliance.audit import log_action
from app.core.cache import invalidate_cache
from app.db.session import AsyncSessionLocal
from app.mitre import attack_data
from app.mitre.applicability import compute_applicability
from app.mitre.coverage import compute_coverage
from app.models.mitre_assessment import MitreAssessment
from app.models.mitre_use_case import MitreUseCase

logger = logging.getLogger(__name__)

SETTING_DEFAULTS = {
    "confidence_covered": 0.7,
    "confidence_partial_floor": 0.4,
    "partial_credit": 0.5,
    "count_disabled_as_coverage": False,
}


def validate_setting(key: str, value):
    """Normalize/validate one tunable. Raises ValueError on bad key/value."""
    if key not in SETTING_DEFAULTS:
        raise ValueError(f"Unknown setting: {key!r}. Valid: {sorted(SETTING_DEFAULTS)}")
    if key == "count_disabled_as_coverage":
        if not isinstance(value, bool):
            raise ValueError(f"{key} must be true/false")
        return value
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError(f"{key} must be a number between 0 and 1")
    value = float(value)
    if not 0.0 <= value <= 1.0:
        raise ValueError(f"{key} must be between 0 and 1")
    return value


async def get_mitre_settings(db, org_id: UUID) -> dict:
    """The 4 tunables, org overrides merged over code defaults."""
    result = await db.execute(
        text("SELECT setting_key, setting_value FROM mitre_settings WHERE org_id = :org_id"),
        {"org_id": org_id},
    )
    overrides = {}
    for key, value in result.all():
        overrides[key] = json.loads(value) if isinstance(value, str) else value
    return {key: overrides.get(key, default) for key, default in SETTING_DEFAULTS.items()}


async def set_mitre_setting(db, org_id: UUID, key: str, value) -> None:
    """Upsert one validated tunable (customization.py pattern)."""
    value = validate_setting(key, value)
    await db.execute(
        text(
            """
            INSERT INTO mitre_settings (org_id, setting_key, setting_value)
            VALUES (:org_id, :key, CAST(:value AS jsonb))
            ON CONFLICT (org_id, setting_key) DO UPDATE SET setting_value = CAST(:value AS jsonb)
            """
        ),
        {"org_id": org_id, "key": key, "value": json.dumps(value)},
    )
    await db.commit()


def build_mappings(tags: list[str]) -> tuple[list[dict], str, list[str]]:
    """Customer tags -> (mappings, mapping_status, assumption notes).

    Valid IDs become {technique_id, source: 'customer', confidence: 1.0};
    revoked IDs remap to their successor; invalid/deprecated IDs are noted.
    Status: customer_tagged (>=1 valid) | invalid (tags, none valid) |
    unmapped (no tags at all).
    """
    index = attack_data.DEFAULT
    mappings, notes, seen = [], [], set()
    for tag in tags:
        canonical, status = index.resolve(tag)
        if status in ("malformed", "unknown"):
            notes.append(f"tag '{tag}' is not a valid ATT&CK v{index.version} technique")
            continue
        if status == "deprecated":
            notes.append(
                f"tag '{tag}' resolves to a technique deprecated in ATT&CK "
                f"v{index.version} — not counted"
            )
            continue
        if status == "remapped":
            notes.append(
                f"tag '{tag}' is revoked in ATT&CK v{index.version} — "
                f"remapped to {canonical}"
            )
        if canonical not in seen:
            seen.add(canonical)
            mappings.append(
                {"technique_id": canonical, "source": "customer", "confidence": 1.0}
            )
    if mappings:
        return mappings, "customer_tagged", notes
    return [], ("invalid" if tags else "unmapped"), notes


async def run_assessment_pipeline(assessment_id: UUID, org_id: UUID) -> None:
    """Fire-and-forget task body. Own AsyncSession; any failure lands the
    assessment in status=failed with error_message (lifecycle CHECKs)."""
    async with AsyncSessionLocal() as db:
        try:
            result = await db.execute(
                select(MitreAssessment).where(
                    (MitreAssessment.assessment_id == assessment_id)
                    & (MitreAssessment.org_id == org_id)
                    & (MitreAssessment.deleted_at.is_(None))
                )
            )
            assessment = result.scalar_one_or_none()
            if assessment is None or assessment.status != "running":
                return

            rows = await db.execute(
                select(MitreUseCase).where(
                    (MitreUseCase.assessment_id == assessment_id)
                    & (MitreUseCase.deleted_at.is_(None))
                )
            )
            use_case_rows = rows.scalars().all()
            use_cases = [
                {
                    "row_ref": uc.row_ref,
                    "name": uc.name,
                    "enabled": uc.enabled,
                    "mappings": uc.mappings or [],
                }
                for uc in use_case_rows
            ]

            params = dict(assessment.params or {})
            environment = params.get("environment") or {
                "platforms": [],
                "has_ics_assets": False,
                "has_managed_mobile": False,
                "inventory_provided": False,
                "exclusions": params.get("intake", {}).get("exclusions", []),
            }

            settings = await get_mitre_settings(db, org_id)
            intake = params.get("intake", {})
            disabled_policy = intake.get("count_disabled_as_coverage")
            if disabled_policy is None:
                disabled_policy = settings["count_disabled_as_coverage"]

            applicability = compute_applicability(environment)
            applicability["assumptions"] = (
                list(params.get("parse_assumptions", [])) + applicability["assumptions"]
            )
            unmapped = sum(1 for uc in use_case_rows if uc.mapping_status == "unmapped")
            invalid = sum(1 for uc in use_case_rows if uc.mapping_status == "invalid")
            if unmapped or invalid:
                applicability["assumptions"].append(
                    f"{unmapped + invalid} untagged rules not yet AI-mapped — "
                    "tagging lands in the next release"
                )

            coverage = compute_coverage(
                use_cases,
                applicability,
                disabled_counts_as_coverage=bool(disabled_policy),
                covered_confidence=settings["confidence_covered"],
                partial_confidence=settings["confidence_partial_floor"],
                partial_weight=settings["partial_credit"],
            )

            assessment.technique_results = coverage["techniques"]
            assessment.summary = {
                "overall": coverage["overall"],
                "domains": coverage["domains"],
                "assumptions": coverage["assumptions"],
                "not_applicable": [
                    {
                        "technique_id": r["technique_id"],
                        "domain": r["domain"],
                        "reason": r["na_reason"],
                    }
                    for r in coverage["techniques"]
                    if r["state"] == "not_applicable"
                ],
                "applicable_domains": applicability["applicable_domains"],
                "counts": {
                    "use_cases": len(use_case_rows),
                    "customer_tagged": sum(
                        1 for uc in use_case_rows if uc.mapping_status == "customer_tagged"
                    ),
                    "unmapped": unmapped,
                    "invalid": invalid,
                },
            }
            assessment.params = {
                **params,
                "thresholds": {**settings, "count_disabled_as_coverage": bool(disabled_policy)},
            }
            assessment.status = "completed"
            assessment.completed_at = datetime.now(timezone.utc)
            assessment.updated_at = datetime.now(timezone.utc)
            await db.commit()

            await log_action(
                db,
                org_id=org_id,
                user_id=assessment.created_by,
                action="mitre.assessment_completed",
                # closed audit_logs CHECK — see resource_type note in router.py
                resource_type="organization",
                resource_id=assessment_id,
            )
            await db.commit()
            await invalidate_cache(f"cache:*:{org_id}:*")
        except Exception as exc:  # noqa: BLE001 — any failure must land in status=failed
            logger.exception(f"MITRE assessment {assessment_id} failed: {exc}")
            try:
                await db.rollback()
                result = await db.execute(
                    select(MitreAssessment).where(
                        MitreAssessment.assessment_id == assessment_id
                    )
                )
                assessment = result.scalar_one_or_none()
                if assessment is not None:
                    assessment.status = "failed"
                    assessment.error_message = str(exc)[:2000]
                    assessment.updated_at = datetime.now(timezone.utc)
                    await db.commit()
            except Exception:  # noqa: BLE001
                logger.exception(
                    f"Could not mark MITRE assessment {assessment_id} as failed"
                )
