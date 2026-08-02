"""Deterministic per-technique detection-strength scoring (Phase 12). Pure.

Coverage (v1) scores detection PRESENCE: does an enabled rule map here?
This module adds an EFFICACY signal — 0-100 "detection strength" per
covered/partial technique — from signals already stored on the parsed
rules. It never touches coverage states or percentages; the two numbers
are deliberately separate (methodology footnote stays true).

Heuristic per mapped rule (coding-over-AI — no LLM in this module):
- provenance base: customer/manual 30, keyword 25, AI >= covered-conf 20,
  AI below it 10 (mirrors the tagging ladder's trust order)
- +10 the rule has detection logic to inspect at all
- +30 the rule's log_source/logic references a telemetry category the
  technique's ATT&CK data sources expect (ranking.py's category bridge —
  logic text usually names its source: index=, sourcetype=, vendor names)
- enabled bonus: +30 enabled, +15 status unknown, +0 disabled — so a
  disabled rule can never score "strong" (max 70 < STRONG)
Technique score = best rule + 5 per extra qualifying rule (max +10), cap
100. Buckets: strong >= 75, moderate >= 45, weak below.

The optional AI pass (service-gated, quality_ai_enabled OFF by default)
only re-rates "inconclusive" techniques — logic present but no telemetry
match to confirm or deny — and degrades to this heuristic on any failure.
"""

from .attack_data import DEFAULT
from .coverage import COVERED_CONFIDENCE, PARTIAL_CONFIDENCE
from .ranking import _LOG_SOURCE_RULES, _categories_provided, component_category

_FIELD_CAP = 2000  # same scan-cost discipline as keyword_tag (adversarial V2)

_PROVENANCE_BASE = {"customer": 30, "manual": 30, "keyword": 25}
_AI_HIGH_BASE, _AI_MID_BASE = 20, 10
_LOGIC_POINTS, _TELEMETRY_POINTS = 10, 30
_ENABLED_BONUS = {True: 30, None: 15, False: 0}
_REDUNDANCY_STEP, _REDUNDANCY_CAP = 5, 10

STRONG_FLOOR, MODERATE_FLOOR = 75, 45


def strength_bucket(score: int) -> str:
    if score >= STRONG_FLOOR:
        return "strong"
    if score >= MODERATE_FLOOR:
        return "moderate"
    return "weak"


def _technique_categories(tech: dict) -> list:
    categories = []
    for component in tech.get("data_sources") or []:
        category = component_category(component)
        if category and category not in categories:
            categories.append(category)
    return categories


def _rule_categories(uc: dict) -> set:
    """Telemetry categories a rule demonstrably touches: its log_source name
    and its logic text (which usually names the source) run through
    ranking.py's log-source keyword bridge."""
    return set(
        _categories_provided(
            [
                str(uc.get("log_source") or ""),
                str(uc.get("logic") or "")[:_FIELD_CAP],
            ],
            _LOG_SOURCE_RULES,
        )
    )


def _hit_score(uc: dict, mapping_confidence: float, source: str,
               tech_categories: list, covered_confidence: float):
    """(points, rationale fragments) for one rule mapped to the technique."""
    if source in _PROVENANCE_BASE:
        base = _PROVENANCE_BASE[source]
        frags = ["customer-tagged" if source == "customer"
                 else "reviewer-set" if source == "manual"
                 else "keyword-matched"]
    elif mapping_confidence >= covered_confidence:
        base, frags = _AI_HIGH_BASE, ["AI-mapped (high confidence)"]
    else:
        base, frags = _AI_MID_BASE, ["AI-mapped (low confidence)"]
    score = base

    enabled = uc.get("enabled")
    score += _ENABLED_BONUS[enabled if enabled in (True, False) else None]
    frags.append(
        "enabled" if enabled is True
        else "DISABLED" if enabled is False
        else "enabled/disabled status unknown"
    )

    has_logic = bool(str(uc.get("logic") or "").strip())
    telemetry_matched = False
    if has_logic:
        score += _LOGIC_POINTS
        frags.append("detection logic present")
    if not tech_categories:
        frags.append("technique lists no standard telemetry to verify against")
    elif _rule_categories(uc) & set(tech_categories):
        score += _TELEMETRY_POINTS
        telemetry_matched = True
        frags.append("log source/logic matches the telemetry this technique expects")
    else:
        frags.append("could not confirm the expected telemetry in the rule")
    return score, frags, has_logic, telemetry_matched


def compute_quality(results, use_cases, *,
                    covered_confidence: float = None,
                    partial_confidence: float = None,
                    index=None) -> list:
    """Annotate covered/partial entries in `results` (coverage output) with
    `strength` (0-100) + `strength_rationale`, in place. Returns the list of
    "inconclusive" items — {technique_id, row_ref, name, logic} — for the
    OPTIONAL AI pass (logic present, expected telemetry known, no match).

    Entries with no direct qualifying mapping (e.g. a parent partial only
    via a covered sub-technique) are left unannotated on purpose.
    """
    covered_confidence = (
        COVERED_CONFIDENCE if covered_confidence is None else covered_confidence
    )
    partial_confidence = (
        PARTIAL_CONFIDENCE if partial_confidence is None else partial_confidence
    )
    index = index if index is not None else DEFAULT

    # canonical technique id -> [(uc, confidence, source)]
    hits = {}
    for uc in use_cases or []:
        for mapping in uc.get("mappings") or []:
            canonical, status = index.resolve(
                str(mapping.get("technique_id", "")).strip().upper()
            )
            if status in ("malformed", "unknown", "deprecated"):
                continue
            confidence = mapping.get("confidence")
            if confidence is None:
                confidence = 1.0 if mapping.get("source") == "customer" else 0.0
            confidence = float(confidence)
            if confidence < partial_confidence:
                continue  # mirrors coverage: below the floor it never counted
            hits.setdefault(canonical, []).append(
                (uc, confidence, str(mapping.get("source") or "ai"))
            )

    inconclusive = []
    for entry in results or []:
        if entry.get("state") not in ("covered", "partial"):
            continue
        tech_hits = hits.get(entry["technique_id"])
        if not tech_hits:
            continue
        tech = index.get(entry["technique_id"]) or {}
        tech_categories = _technique_categories(tech)

        best_score, best_frags, best_uc = -1, [], None
        any_unmatched_logic = False
        for uc, confidence, source in tech_hits:
            score, frags, has_logic, matched = _hit_score(
                uc, confidence, source, tech_categories, covered_confidence
            )
            if has_logic and tech_categories and not matched:
                any_unmatched_logic = True
            if score > best_score:
                best_score, best_frags, best_uc = score, frags, uc
        extra = len(tech_hits) - 1
        if extra > 0:
            best_score += min(extra * _REDUNDANCY_STEP, _REDUNDANCY_CAP)
            best_frags.append(f"+{extra} more mapped rule{'s' if extra > 1 else ''}")

        entry["strength"] = min(best_score, 100)
        entry["strength_rationale"] = "; ".join(best_frags)
        if any_unmatched_logic and entry["strength"] < STRONG_FLOOR:
            inconclusive.append(
                {
                    "technique_id": entry["technique_id"],
                    "row_ref": best_uc.get("row_ref"),
                    "name": best_uc.get("name"),
                    "logic": str(best_uc.get("logic") or "")[:_FIELD_CAP],
                }
            )
    return inconclusive


def apply_ai_ratings(results, ratings: dict) -> int:
    """Merge validated AI strength ratings (technique_id -> {strength,
    rationale}) over the heuristic annotations. Returns how many were
    applied. Anything missing/invalid keeps the heuristic (degrade rule)."""
    applied = 0
    for entry in results or []:
        rating = ratings.get(entry.get("technique_id"))
        if not rating or entry.get("strength") is None:
            continue
        entry["strength"] = rating["strength"]
        entry["strength_rationale"] = "AI-assessed: " + rating["rationale"]
        applied += 1
    return applied


def quality_rollup(results) -> dict:
    """Summary rollup over annotated entries. Kept separate from coverage
    rollups — detection strength never feeds a coverage number."""
    scored = [r["strength"] for r in results or [] if r.get("strength") is not None]
    if not scored:
        return {"scored": 0, "avg_strength": None,
                "strong": 0, "moderate": 0, "weak": 0}
    buckets = {"strong": 0, "moderate": 0, "weak": 0}
    for score in scored:
        buckets[strength_bucket(score)] += 1
    return {
        "scored": len(scored),
        "avg_strength": round(sum(scored) / len(scored), 1),
        **buckets,
    }
