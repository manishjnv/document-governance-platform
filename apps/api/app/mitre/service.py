"""MITRE assessment pipeline driver + org tunables (Phase 1, tagged-only).

Pipeline stages at run time: applicability -> coverage -> persist. Tag
validation happens at CREATE time (router) so the parse preview can report
the tagged/untagged/invalid split; its assumption lines ride in
params["parse_assumptions"] and are merged into the final summary here.

AI tagging and narrative are Phase 2 — untagged rows stay 'unmapped' with an
assumption line.
"""

import asyncio
import json
import logging
from datetime import datetime, timezone
from uuid import UUID

from sqlalchemy import select, text

from app.compliance.audit import log_action
from app.core.cache import invalidate_cache
from app.db.session import AsyncSessionLocal
from app.mitre import agents, attack_data, ranking
from app.mitre.applicability import compute_applicability
from app.mitre.coverage import compute_coverage
from app.models.mitre_assessment import MitreAssessment
from app.models.mitre_file import MitreFile
from app.models.mitre_use_case import MitreUseCase

logger = logging.getLogger(__name__)

# Cap concurrent pipelines process-wide: each run makes long sequential LLM
# calls, and unbounded parallel runs could exhaust the shared DB pool / CPU
# (2026-08-01 adversarial review, blocking finding #1).
# ponytail: process-wide cap; per-org fairness only if multi-tenant load grows
_PIPELINE_CAP = 3
_PIPELINE_SEMAPHORE = asyncio.Semaphore(_PIPELINE_CAP)


class MitreAssessmentError(Exception):
    """Pipeline failure with a plain-English, user-facing message — lands in
    mitre_assessments.error_message via the pipeline's except path."""

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


def compare_assessments(current, baseline) -> dict:
    """Trend diff of two COMPLETED assessments (plan §8). Pure Python over
    the stored technique_results/summary — nothing recomputed.

    Direction: `current` is the run being viewed, `baseline` the older run
    compared against; positive deltas mean more coverage now. Techniques
    present in only one run (ATT&CK version drift) are skipped —
    `attack_version_mismatch` flags that case. A technique that entered/left
    the applicable set appears in na_changed (and also in newly_covered when
    it went straight to covered — both facts are true).
    """
    cur_by_id = {r["technique_id"]: r for r in current.technique_results or []}
    base_by_id = {r["technique_id"]: r for r in baseline.technique_results or []}

    newly_covered, regressed, na_changed = [], [], []
    for tid in sorted(cur_by_id.keys() & base_by_id.keys()):
        cur, base = cur_by_id[tid], base_by_id[tid]
        # .get() throughout: technique_results is unenforced JSONB — a row from
        # a future/older schema missing 'state' must degrade, not 500.
        cur_state, base_state = cur.get("state"), base.get("state")
        if cur_state == base_state:
            continue
        tech = attack_data.DEFAULT.get(tid)
        entry = {
            "technique_id": tid,
            "name": tech.get("name", tid) if tech else tid,
            "domain": cur.get("domain"),
            "from": base_state,
            "to": cur_state,
        }
        if cur_state == "covered":
            newly_covered.append(entry)
        elif base_state == "covered" and cur_state in ("partial", "not_covered"):
            regressed.append(entry)
        if (cur_state == "not_applicable") != (base_state == "not_applicable"):
            na_changed.append(entry)

    def _overall(a):
        return (a.summary or {}).get("overall", {})

    keys = ("strict_pct", "weighted_pct", "covered", "partial", "not_covered",
            "not_applicable", "applicable")
    overall_delta = {
        k: round((_overall(current).get(k) or 0) - (_overall(baseline).get(k) or 0), 1)
        for k in keys
    }

    def _tactics(a):
        return {
            (dk, t.get("id")): t
            for dk, d in ((a.summary or {}).get("domains") or {}).items()
            for t in d.get("tactics", [])
            if t.get("id")
        }

    cur_tactics, base_tactics = _tactics(current), _tactics(baseline)
    tactic_deltas = [
        {
            "domain": dk,
            "id": tid,
            "name": cur_tactics[(dk, tid)].get("name"),
            "current_strict_pct": cur_tactics[(dk, tid)].get("strict_pct"),
            "baseline_strict_pct": base_tactics[(dk, tid)].get("strict_pct"),
            "delta": round(
                (cur_tactics[(dk, tid)].get("strict_pct") or 0)
                - (base_tactics[(dk, tid)].get("strict_pct") or 0),
                1,
            ),
        }
        for (dk, tid) in sorted(cur_tactics.keys() & base_tactics.keys())
    ]

    def _meta(a):
        return {
            "assessment_id": str(a.assessment_id),
            "name": a.name,
            "completed_at": a.completed_at.isoformat() if a.completed_at else None,
            "attack_version": a.attack_version,
            "strict_pct": _overall(a).get("strict_pct"),
        }

    return {
        "current": _meta(current),
        "baseline": _meta(baseline),
        "attack_version_mismatch": current.attack_version != baseline.attack_version,
        "overall_delta": overall_delta,
        "tactic_deltas": tactic_deltas,
        "newly_covered": newly_covered,
        "regressed": regressed,
        "na_changed": na_changed,
    }


async def run_assessment_pipeline(assessment_id: UUID, org_id: UUID) -> None:
    """Fire-and-forget task body. Own AsyncSession; any failure lands the
    assessment in status=failed with error_message (lifecycle CHECKs).
    Concurrency-capped; queued runs simply wait their turn (the 30-min
    stale-run guard is generous enough to cover realistic queue waits)."""
    async with _PIPELINE_SEMAPHORE:
        await _run_pipeline_body(assessment_id, org_id)


async def _run_pipeline_body(assessment_id: UUID, org_id: UUID) -> None:
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
            params = dict(assessment.params or {})
            pipeline_assumptions = []
            models_used = {}
            # Release the pooled connection before any long LLM wait — a
            # transaction left open across sequential LLM batches holds a
            # pool slot for the whole run (expire_on_commit=False, so loaded
            # objects stay usable after commit).
            await db.commit()

            # Stage 0 — extraction: pdf/docx dumps arrive with parsed text
            # but no rows (plan §7 stage 1); AI-extract use cases now.
            if not use_case_rows and params.get("extraction_text"):
                extraction = await agents.extract_use_cases_from_text(
                    params["extraction_text"]
                )
                if not extraction["rows"]:
                    raise MitreAssessmentError(
                        "No detection rules could be extracted from the "
                        "uploaded document. Please retry, or upload the rules "
                        "in the XLSX template."
                    )
                file_result = await db.execute(
                    select(MitreFile).where(
                        (MitreFile.assessment_id == assessment_id)
                        & (MitreFile.kind == "use_cases")
                        & (MitreFile.deleted_at.is_(None))
                    )
                )
                uc_file = file_result.scalars().first()
                for row in extraction["rows"]:
                    db.add(
                        MitreUseCase(
                            assessment_id=assessment_id,
                            org_id=org_id,
                            file_id=uc_file.file_id if uc_file else None,
                            row_ref=row["row_ref"],
                            name=row["name"],
                            description=row["description"],
                            log_source=row["log_source"],
                            enabled=row["enabled"],
                            mappings=row["mappings"],
                            mapping_status=row["mapping_status"],
                        )
                    )
                if uc_file is not None:
                    uc_file.parse_status = "parsed"
                    uc_file.row_count = len(extraction["rows"])
                await db.commit()
                rows = await db.execute(
                    select(MitreUseCase).where(
                        (MitreUseCase.assessment_id == assessment_id)
                        & (MitreUseCase.deleted_at.is_(None))
                    )
                )
                use_case_rows = rows.scalars().all()
                await db.commit()  # release connection before the tagging LLM stage
                pipeline_assumptions.extend(extraction["assumptions"])
                if extraction["models_used"]:
                    models_used["extraction"] = extraction["models_used"]

            # Stage 2 — AI-tag rows the customer left untagged (or tagged
            # invalidly). Customer-tagged rows are NEVER re-tagged.
            to_tag = [
                uc
                for uc in use_case_rows
                if uc.mapping_status in ("unmapped", "invalid")
            ]
            if to_tag:
                tagging = await agents.tag_untagged_rows(
                    [
                        {
                            "row_ref": uc.row_ref,
                            "name": uc.name,
                            "description": uc.description or "",
                            "logic": "",
                        }
                        for uc in to_tag
                    ]
                )
                customer_tagged = sum(
                    1
                    for uc in use_case_rows
                    if uc.mapping_status == "customer_tagged"
                )
                if (
                    tagging["batches_failed"] == tagging["batches_total"]
                    and customer_tagged == 0
                ):
                    raise MitreAssessmentError(
                        "AI tagging is temporarily unavailable and none of the "
                        "uploaded rules carry MITRE technique tags — the "
                        "assessment would be empty. Please re-run in a few "
                        "minutes, or upload a dump with technique tags."
                    )
                now = datetime.now(timezone.utc)
                for uc in to_tag:
                    mapped = tagging["mappings_by_ref"].get(uc.row_ref)
                    if mapped:
                        uc.mappings = mapped
                        uc.mapping_status = "ai_tagged"
                        uc.updated_at = now
                await db.commit()
                pipeline_assumptions.extend(tagging["assumptions"])
                if tagging["models_used"]:
                    models_used["tagging"] = tagging["models_used"]

            use_cases = [
                {
                    "row_ref": uc.row_ref,
                    "name": uc.name,
                    "enabled": uc.enabled,
                    "mappings": uc.mappings or [],
                }
                for uc in use_case_rows
            ]

            environment = params.get("environment") or {
                "platforms": [],
                "has_ics_assets": False,
                "has_managed_mobile": False,
                "inventory_provided": False,
                "exclusions": params.get("intake", {}).get("exclusions", []),
            }

            settings = await get_mitre_settings(db, org_id)
            await db.commit()  # release connection before the narrative LLM stage
            intake = params.get("intake", {})
            disabled_policy = intake.get("count_disabled_as_coverage")
            if disabled_policy is None:
                disabled_policy = settings["count_disabled_as_coverage"]

            applicability = compute_applicability(environment)
            applicability["assumptions"] = (
                list(params.get("parse_assumptions", []))
                + pipeline_assumptions
                + applicability["assumptions"]
            )
            unmapped = sum(1 for uc in use_case_rows if uc.mapping_status == "unmapped")
            invalid = sum(1 for uc in use_case_rows if uc.mapping_status == "invalid")
            if unmapped or invalid:
                applicability["assumptions"].append(
                    f"{unmapped + invalid} rules remain unmapped to ATT&CK — "
                    "they do not count toward coverage"
                )
            if params.get("columns"):
                applicability["assumptions"].append(
                    "detected columns: "
                    + ", ".join(
                        f"{field}→col {idx + 1}"
                        for field, idx in sorted(params["columns"].items())
                    )
                )

            coverage = compute_coverage(
                use_cases,
                applicability,
                disabled_counts_as_coverage=bool(disabled_policy),
                covered_confidence=settings["confidence_covered"],
                partial_confidence=settings["confidence_partial_floor"],
                partial_weight=settings["partial_credit"],
            )

            # Stage 6 — deterministic gap ranking + roadmap bucketing.
            env_lists = params.get("environment_lists") or {}
            ranked = ranking.rank_gaps(
                coverage["techniques"],
                env_lists.get("log_sources") or [],
                env_lists.get("tooling") or [],
            )

            # Stage 7 — narrative over COMPUTED data only; degrades to
            # template text so the assessment still completes.
            computed = {
                "industry": intake.get("industry"),
                "region": intake.get("region"),
                "attack_version": coverage["attack_version"],
                "overall": coverage["overall"],
                "domains_brief": {
                    dom: {k: v for k, v in dd.items() if k != "tactics"}
                    for dom, dd in coverage["domains"].items()
                },
                "top_gaps": [
                    {
                        k: g[k]
                        for k in (
                            "technique_id", "name", "state", "tier",
                            "feasibility", "via", "hint",
                        )
                    }
                    for g in ranked["gaps"][:15]
                ],
                "roadmap_counts": {b: len(v) for b, v in ranked["roadmap"].items()},
                "not_applicable_count": coverage["overall"]["not_applicable"],
            }
            narrative_out = await agents.generate_narrative(computed)
            if narrative_out["model_used"]:
                models_used["narrative"] = [narrative_out["model_used"]]
            coverage["assumptions"].append(
                "narrative text was AI-generated — all numbers come from "
                "computed results"
                if narrative_out["generated_by"] == "ai"
                else "narrative used deterministic template text (AI narrative "
                "unavailable)"
            )

            assessment.technique_results = coverage["techniques"]
            assessment.summary = {
                "overall": coverage["overall"],
                "domains": coverage["domains"],
                "assumptions": coverage["assumptions"],
                "gaps": ranked["gaps"],
                "roadmap": ranked["roadmap"],
                "narrative": {
                    **narrative_out["narrative"],
                    "generated_by": narrative_out["generated_by"],
                    "model_used": narrative_out["model_used"],
                },
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
                    "ai_tagged": sum(
                        1 for uc in use_case_rows if uc.mapping_status == "ai_tagged"
                    ),
                    "unmapped": unmapped,
                    "invalid": invalid,
                },
            }
            assessment.params = {
                **params,
                "thresholds": {**settings, "count_disabled_as_coverage": bool(disabled_policy)},
                "models_used": models_used,
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
