"""LLM agents for the MITRE assessment module (plan §7 stages 3 + 7).

Both agents subclass ReviewAgent exactly like ConflictDetector — ONLY to
inherit the OpenRouter client, GLM-5.2 → DeepSeek → MiniMax → Qwen fallback
chain, unparseable-JSON-advances-chain behavior, asyncio.to_thread, and
_model_used stamping. They are registered NOWHERE in ReviewOrchestrator
(a 7th registered agent would corrupt every review's status math).

Prompt rationale + changelog: docs/planning/PROMPT_ENGINEERING_GUIDE.md
("2026-08-01 — MITRE module prompts"). These prompts are NOT mirrored to
prompts/ (its generator covers only the 6 review personas).

Failure discipline (plan §7): every LLM call runs under asyncio.wait_for
(60s, one retry at 120s); a failed tagging batch degrades those rows to
unmapped + an assumption line; a failed narrative degrades to
deterministic template text. Neither ever fails the assessment by itself.
"""

import asyncio
import json
import logging

from app.ai.agent import ReviewAgent, _CONFIDENCE_CALIBRATION

from .attack_data import DEFAULT
from .coverage import PARTIAL_CONFIDENCE
from .ingest import MAX_USE_CASE_ROWS

logger = logging.getLogger(__name__)

BATCH_SIZE = 25          # rules per tagging call (plan §7 stage 3)
EXCERPT_CAP = 500        # chars of description/logic sent per rule
CHUNK_CHARS = 9000       # extraction-mode text chunk size
# Extraction budgets (2026-08-01 adversarial review, blocking finding #3:
# a bloated pdf/docx must not drive unbounded LLM calls or row inserts).
# 40 chunks ≈ 360KB of text; the OCR path caps scanned PDFs at 30 pages.
MAX_EXTRACTION_CHUNKS = 40
TIMEOUTS = (60, 120)     # first try, one retry (house pattern)
CONFIDENCE_FLOOR = PARTIAL_CONFIDENCE  # < floor -> unmapped + assumption


class MitreTaggingAgent(ReviewAgent):
    """Maps detection rules to ATT&CK techniques. Two prompt modes selected
    via the review() document_type param: "tagging" (structured rows) and
    "extraction" (unstructured pdf/docx text chunks)."""

    def __init__(self):
        super().__init__("MitreTaggingAgent")

    def get_system_prompt(self, document_type: str = "tagging") -> str:
        if document_type == "extraction":
            return (
                """You are a senior SOC analyst extracting detection use cases from an unstructured document (a SIEM detection-rule inventory exported to PDF or DOCX). The user message contains one text chunk from that document.

Extract each individual detection rule / use case you can identify in the chunk:
- Only extract actual detection rules or use cases — never headings, narrative prose, tables of contents, or boilerplate. An empty list is a good, correct answer for a chunk with none.
- name: short, as written in the document where possible.
- description: 1-2 sentences taken from the document text.
- technique_ids: MITRE ATT&CK v19 technique IDs (format T1234 or T1234.001) when the document states them OR the rule's behavior clearly maps to one; [] when unclear. Never invent IDs.
"""
                + _CONFIDENCE_CALIBRATION
                + """
Provide your response as a JSON object with this structure:
{
    "use_cases": [
        {"name": "string", "description": "string", "technique_ids": ["T1234.001"], "confidence": 0.0-1.0}
    ],
    "overall_confidence": 0.0-1.0
}"""
            )
        return (
            """You are a senior SOC detection engineer mapping SIEM detection rules to MITRE ATT&CK v19 techniques. The user message contains a JSON array of detection rules: [{"row_ref", "name", "description", "logic"}].

For each rule, identify the technique(s) the rule ACTUALLY DETECTS:
- Map what the detection logic observes — not every technique the surrounding attack chain might involve.
- Prefer the most specific sub-technique (e.g. T1059.001) when the rule clearly targets it; use the parent (T1059) when the rule is broader.
- 0-3 techniques per rule. An empty technique_ids list is correct for rules that are not ATT&CK-mappable (health monitoring, compliance checks, pure correlation plumbing).
- Use only real ATT&CK v19 technique IDs in the format T1234 or T1234.001. Never invent IDs.
"""
            + _CONFIDENCE_CALIBRATION
            + """
Provide your response as a JSON object with this structure — every input row_ref appears exactly once:
{
    "mappings": [
        {"row_ref": "string (verbatim from input)", "technique_ids": ["T1059.001"], "confidence": 0.0-1.0, "rationale": "one short sentence"}
    ],
    "overall_confidence": 0.0-1.0
}"""
        )

    def get_output_schema(self) -> dict:
        return {"type": "object", "required": ["mappings", "overall_confidence"]}


class MitreNarrativeAgent(ReviewAgent):
    """Writes the report narrative from COMPUTED results. It may rephrase
    but never introduces numbers — templates print figures exclusively from
    the computed summary (plan §7 stage 7)."""

    def __init__(self):
        super().__init__("MitreNarrativeAgent")

    def get_system_prompt(self, document_type: str = "SOW") -> str:
        return """You write the narrative for a MITRE ATT&CK coverage assessment report read by security leadership. The user message contains the COMPUTED assessment results as JSON: coverage percentages, ranked gaps with feasibility hints, roadmap bucket counts, not-applicable counts, and the customer's industry/region.

Hard rules:
- Plain, simple English. Short sentences. No unexplained jargon — write "techniques we cannot detect yet because no log source covers them", never "telemetry-gap-induced detection debt".
- NEVER introduce, change, round, or recompute any number. You may repeat a number exactly as it appears in the input. All figures in the report are printed from the computed data — your text explains, it does not calculate.
- Do not invent facts, threat actors, tools, or log sources that are not in the input.
- Be direct about weaknesses. This is an internal working document, not marketing.

Provide your response as a JSON object with this structure:
{
    "executive_summary": "string (at most ~300 words)",
    "gap_recommendations": {"<technique_id>": "one or two sentences of exact, actionable recommendation", ...},
    "roadmap_prose": {"short": "string", "mid": "string", "long": "string"}
}
Write a gap_recommendations entry for EVERY technique in the input's top_gaps list, keyed by its technique_id."""

    def get_output_schema(self) -> dict:
        return {"type": "object", "required": ["executive_summary", "gap_recommendations", "roadmap_prose"]}


async def _call_with_retry(agent: ReviewAgent, payload: str, mode: str) -> dict:
    """agent.review under the house timeout discipline: 60s, one retry at 120s."""
    last_error = None
    for timeout in TIMEOUTS:
        try:
            return await asyncio.wait_for(agent.review(payload, mode), timeout=timeout)
        except Exception as exc:  # noqa: BLE001 — timeout or full-chain failure
            last_error = exc
            logger.warning(f"{agent.name} ({mode}): attempt failed ({exc})")
    raise last_error


def _validate_ai_ids(ids, confidence, rationale, index, stats) -> list:
    """Model-emitted technique IDs -> validated mapping dicts (source='ai').
    Models emit revoked/hallucinated IDs: remap revoked, drop
    invalid/deprecated, count both in stats."""
    mappings, seen = [], set()
    for raw in ids or []:
        canonical, status = index.resolve(str(raw).strip().upper())
        if status in ("malformed", "unknown", "deprecated"):
            stats["invalid_ids"] += 1
            continue
        if status == "remapped":
            stats["remapped_ids"] += 1
        if canonical not in seen:
            seen.add(canonical)
            mappings.append(
                {
                    "technique_id": canonical,
                    "source": "ai",
                    "confidence": round(float(confidence), 2),
                    "rationale": str(rationale or "")[:500],
                }
            )
    return mappings


async def tag_untagged_rows(rows, *, index=None, agent=None) -> dict:
    """AI-tag rows the customer left untagged (or tagged invalidly).

    rows: [{"row_ref", "name", "description", "logic"}] — customer-tagged
    rows must never be passed in (customer truth wins).
    Returns {"mappings_by_ref": {row_ref: [mapping...]}, "assumptions": [...],
    "models_used": [...], "batches_total": int, "batches_failed": int}.
    A failed batch degrades to unmapped; it never raises.
    """
    index = index if index is not None else DEFAULT
    agent = agent if agent is not None else MitreTaggingAgent()

    mappings_by_ref, assumptions, models_used = {}, [], set()
    stats = {"invalid_ids": 0, "remapped_ids": 0, "low_confidence": 0}
    batches = [rows[i : i + BATCH_SIZE] for i in range(0, len(rows), BATCH_SIZE)]
    batches_failed = 0

    for batch in batches:  # sequential — rate-limit courtesy (plan §7)
        payload = json.dumps(
            [
                {
                    "row_ref": r["row_ref"],
                    "name": str(r.get("name") or "")[:EXCERPT_CAP],
                    "description": str(r.get("description") or "")[:EXCERPT_CAP],
                    "logic": str(r.get("logic") or "")[:EXCERPT_CAP],
                }
                for r in batch
            ],
            ensure_ascii=False,
        )
        try:
            result = await _call_with_retry(agent, payload, "tagging")
        except Exception:  # noqa: BLE001
            result = None
        raw_mappings = (result or {}).get("mappings")
        if not isinstance(raw_mappings, list):
            # full-chain failure OR the degrade-to-raw-text dict — either way
            # this batch stays unmapped.
            batches_failed += 1
            assumptions.append(
                f"AI tagging unavailable for {len(batch)} rules "
                f"({batch[0]['row_ref']} … {batch[-1]['row_ref']}) — left unmapped"
            )
            continue
        if result.get("_model_used"):
            models_used.add(result["_model_used"])
        by_ref = {
            str(m.get("row_ref")): m for m in raw_mappings if isinstance(m, dict)
        }
        for row in batch:
            m = by_ref.get(row["row_ref"])
            if not m:
                continue
            try:
                confidence = float(m.get("confidence") or 0.0)
            except (TypeError, ValueError):
                confidence = 0.0
            validated = _validate_ai_ids(
                m.get("technique_ids"), confidence, m.get("rationale"), index, stats
            )
            if not validated:
                continue
            if confidence < CONFIDENCE_FLOOR:
                stats["low_confidence"] += 1
                continue
            mappings_by_ref[row["row_ref"]] = validated

    if mappings_by_ref:
        assumptions.append(
            f"{len(mappings_by_ref)} rules were AI-tagged (confidence ≥ "
            f"{CONFIDENCE_FLOOR}) — model-generated mappings, spot-check "
            "before operational use"
        )
    if stats["low_confidence"]:
        assumptions.append(
            f"{stats['low_confidence']} AI-suggested mappings fell below the "
            f"{CONFIDENCE_FLOOR} confidence floor — those rules stay unmapped"
        )
    if stats["invalid_ids"]:
        assumptions.append(
            f"{stats['invalid_ids']} invalid or deprecated technique IDs "
            "emitted by the AI were dropped"
        )
    if stats["remapped_ids"]:
        assumptions.append(
            f"{stats['remapped_ids']} revoked technique IDs from the AI were "
            "remapped to their ATT&CK successors"
        )
    return {
        "mappings_by_ref": mappings_by_ref,
        "assumptions": assumptions,
        "models_used": sorted(models_used),
        "batches_total": len(batches),
        "batches_failed": batches_failed,
    }


def _chunk_text(text: str, size: int = CHUNK_CHARS) -> list:
    """Split on the last newline before the size cap so rules aren't cut
    mid-line where avoidable."""
    chunks, remaining = [], text
    while remaining:
        if len(remaining) <= size:
            chunks.append(remaining)
            break
        cut = remaining.rfind("\n", size // 2, size)
        if cut < 0:
            cut = size
        chunks.append(remaining[:cut])
        remaining = remaining[cut:]
    return chunks


async def extract_use_cases_from_text(text: str, *, index=None, agent=None) -> dict:
    """Extraction mode for pdf/docx dumps (replaces Phase 1's 422).

    Returns {"rows": [use-case row dicts with validated 'mappings' +
    'mapping_status'], "assumptions": [...], "models_used": [...],
    "chunks_total": int, "chunks_failed": int}. Never raises; zero rows is
    the caller's signal to fail the assessment with a clear message.
    """
    index = index if index is not None else DEFAULT
    agent = agent if agent is not None else MitreTaggingAgent()

    rows, assumptions, models_used = [], [], set()
    stats = {"invalid_ids": 0, "remapped_ids": 0, "low_confidence": 0}
    chunks = _chunk_text(text)
    if len(chunks) > MAX_EXTRACTION_CHUNKS:
        assumptions.append(
            f"the document is very large — only its first "
            f"{MAX_EXTRACTION_CHUNKS} sections were scanned for rules"
        )
        chunks = chunks[:MAX_EXTRACTION_CHUNKS]
    chunks_failed = 0
    row_cap_hit = False

    for chunk_no, chunk in enumerate(chunks, start=1):
        if row_cap_hit:
            break
        try:
            result = await _call_with_retry(agent, chunk, "extraction")
        except Exception:  # noqa: BLE001
            result = None
        entries = (result or {}).get("use_cases")
        if not isinstance(entries, list):
            chunks_failed += 1
            continue
        if result.get("_model_used"):
            models_used.add(result["_model_used"])
        for i, entry in enumerate(entries, start=1):
            if len(rows) >= MAX_USE_CASE_ROWS:
                row_cap_hit = True
                assumptions.append(
                    f"rule extraction stopped at the {MAX_USE_CASE_ROWS:,}-row "
                    "limit — rules beyond it are not included"
                )
                break
            if not isinstance(entry, dict):
                continue
            name = str(entry.get("name") or "").strip()
            if not name:
                continue
            try:
                confidence = float(entry.get("confidence") or 0.0)
            except (TypeError, ValueError):
                confidence = 0.0
            mappings = _validate_ai_ids(
                entry.get("technique_ids"), confidence, entry.get("description"),
                index, stats,
            )
            if mappings and confidence < CONFIDENCE_FLOOR:
                stats["low_confidence"] += 1
                mappings = []
            rows.append(
                {
                    "row_ref": f"doc:{chunk_no}:{i}",
                    "name": name[:500],
                    "description": str(entry.get("description") or "")[:2000] or None,
                    "log_source": None,
                    "enabled": None,
                    "mappings": mappings,
                    "mapping_status": "ai_tagged" if mappings else "unmapped",
                }
            )

    if rows:
        assumptions.append(
            f"{len(rows)} rules were AI-extracted from an unstructured "
            "PDF/DOCX document — row-level completeness is not guaranteed; "
            "prefer the XLSX template for exact results"
        )
    if chunks_failed:
        assumptions.append(
            f"{chunks_failed} of {len(chunks)} document sections could not be "
            "processed by the AI — rules in those sections are missing"
        )
    return {
        "rows": rows,
        "assumptions": assumptions,
        "models_used": sorted(models_used),
        "chunks_total": len(chunks),
        "chunks_failed": chunks_failed,
    }


def build_template_narrative(computed: dict) -> dict:
    """Deterministic fallback narrative — uses only numbers already in the
    computed input, verbatim. Keeps the assessment completing when the LLM
    chain is down (ConflictDetector-style degrade)."""
    overall = computed.get("overall", {})
    top_gaps = computed.get("top_gaps", [])
    counts = computed.get("roadmap_counts", {})

    lines = [
        f"Coverage of the applicable MITRE ATT&CK techniques is "
        f"{overall.get('strict_pct')}% ({overall.get('covered')} of "
        f"{overall.get('applicable')} techniques covered; "
        f"{overall.get('partial')} partially covered).",
        f"{overall.get('not_covered')} applicable techniques have no "
        "detection today.",
    ]
    if top_gaps:
        names = ", ".join(
            f"{g['name']} ({g['technique_id']})" for g in top_gaps[:5]
        )
        lines.append(f"The highest-priority gaps are: {names}.")
    if counts:
        lines.append(
            f"The roadmap has {counts.get('short', 0)} short-term, "
            f"{counts.get('mid', 0)} mid-term and {counts.get('long', 0)} "
            "long-term items."
        )
    return {
        "executive_summary": " ".join(lines),
        "gap_recommendations": {
            g["technique_id"]: f"{g['name']}: {g['hint']}." for g in top_gaps
        },
        "roadmap_prose": {
            "short": "Quick wins: these detections use telemetry you already "
                     "collect — build them first.",
            "mid": "Next: onboard the named log sources from tooling you "
                   "already own, then build these detections.",
            "long": "Longer term: these need a new telemetry capability or "
                    "bespoke detection engineering.",
        },
    }


def _narrative_valid(candidate) -> bool:
    return (
        isinstance(candidate, dict)
        and isinstance(candidate.get("executive_summary"), str)
        and candidate["executive_summary"].strip() != ""
        and isinstance(candidate.get("gap_recommendations"), dict)
        and isinstance(candidate.get("roadmap_prose"), dict)
        and all(k in candidate["roadmap_prose"] for k in ("short", "mid", "long"))
    )


async def generate_narrative(computed: dict, *, agent=None) -> dict:
    """One LLM call over the computed JSON; degrades to template text.

    Returns {"narrative": {...}, "generated_by": "ai"|"template",
    "model_used": str|None}. Never raises.
    """
    agent = agent if agent is not None else MitreNarrativeAgent()
    try:
        result = await _call_with_retry(
            agent, json.dumps(computed, ensure_ascii=False), "narrative"
        )
    except Exception:  # noqa: BLE001
        result = None
    if result is not None and _narrative_valid(result):
        narrative = {
            "executive_summary": result["executive_summary"],
            "gap_recommendations": result["gap_recommendations"],
            "roadmap_prose": result["roadmap_prose"],
        }
        return {
            "narrative": narrative,
            "generated_by": "ai",
            "model_used": result.get("_model_used"),
        }
    logger.warning("MitreNarrativeAgent degraded to template narrative")
    return {
        "narrative": build_template_narrative(computed),
        "generated_by": "template",
        "model_used": None,
    }
