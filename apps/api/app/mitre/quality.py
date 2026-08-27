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
from .ranking import _LOG_SOURCE_RULES, _categories_provided, _norm, component_category

import datetime as _dt

_FIELD_CAP = 2000  # same scan-cost discipline as keyword_tag (adversarial V2)

_PROVENANCE_BASE = {"customer": 30, "manual": 30, "keyword": 25}
_AI_HIGH_BASE, _AI_MID_BASE = 20, 10
_LOGIC_POINTS, _TELEMETRY_POINTS = 10, 30
_ENABLED_BONUS = {True: 30, None: 15, False: 0}
_REDUNDANCY_STEP, _REDUNDANCY_CAP = 5, 10

# Phase A6: optional customer-provided health columns feed small,
# deterministic adjustments. Absent (None) values are a no-op — these only
# ever apply when the customer's dump actually populated the column.
_SEVERITY_DELTAS = {
    "critical": 10, "high": 5, "medium": 0, "low": -5,
    "informational": -10, "info": -10,
}
# A rule that has literally never fired can't be trusted as "strong"
# evidence of detection, however else it scores — same discipline as the
# disabled-rule cap below.
_NEVER_TRIGGERED_CAP = 70
_STALE_TRIGGER_DAYS = 180
_STALE_TRIGGER_PENALTY = -10
_DATE_FORMATS = ("%Y-%m-%d", "%m/%d/%Y", "%d/%m/%Y", "%Y/%m/%d")

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
        base, frags = _AI_HIGH_BASE, ["auto-mapped (high confidence)"]
    else:
        base, frags = _AI_MID_BASE, ["auto-mapped (low confidence)"]
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

    # Phase A6: optional severity/last-triggered health columns.
    severity = str(uc.get("severity") or "").strip().lower()
    if severity in _SEVERITY_DELTAS:
        delta = _SEVERITY_DELTAS[severity]
        score += delta
        if delta:
            frags.append(f"severity '{severity}'")

    never_triggered = False
    last_triggered = str(uc.get("last_triggered") or "").strip()
    if last_triggered.lower() == "never":
        never_triggered = True
        frags.append("has never triggered")
    elif last_triggered:
        parsed_date = None
        for fmt in _DATE_FORMATS:
            try:
                parsed_date = _dt.datetime.strptime(last_triggered, fmt).date()
                break
            except ValueError:
                continue
        if parsed_date and (_dt.date.today() - parsed_date).days > _STALE_TRIGGER_DAYS:
            score += _STALE_TRIGGER_PENALTY
            frags.append(f"last triggered over {_STALE_TRIGGER_DAYS} days ago")

    return score, frags, has_logic, telemetry_matched, never_triggered


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
        best_never_triggered = False
        any_unmatched_logic = False
        for uc, confidence, source in tech_hits:
            score, frags, has_logic, matched, never_triggered = _hit_score(
                uc, confidence, source, tech_categories, covered_confidence
            )
            if has_logic and tech_categories and not matched:
                any_unmatched_logic = True
            if score > best_score:
                best_score, best_frags, best_uc = score, frags, uc
                best_never_triggered = never_triggered
        extra = len(tech_hits) - 1
        if extra > 0:
            best_score += min(extra * _REDUNDANCY_STEP, _REDUNDANCY_CAP)
            best_frags.append(f"+{extra} more mapped rule{'s' if extra > 1 else ''}")
        if best_never_triggered:
            best_score = min(best_score, _NEVER_TRIGGERED_CAP)

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


def telemetry_shelfware_check(results, use_cases, log_sources, tooling, *,
                               covered_confidence: float = None,
                               partial_confidence: float = None,
                               index=None) -> list:
    """Plan phase A3 — deterministic shelfware detector.

    For every covered/partial technique whose qualifying rules ALL declare
    a log source that maps (via ranking.py's category bridge, reused here
    with no duplication) to a telemetry category absent from the
    customer's OWN Log Sources/Tooling sheets, return one flagged entry.
    A rule with no category-recognizable log_source/logic says nothing
    either way and is ignored; a technique is only flagged when every one
    of its qualifying rules' categories miss the customer's declared
    inventory (one matching rule is enough to clear it).

    Caller decides whether to surface this at all (an environment workbook
    with a Log Sources sheet must have been provided — this function is
    workbook-shape-agnostic; empty log_sources/tooling just means nothing
    is "provided" for the purposes of the cross-check, never an error).

    Returns [{"technique_id", "rules": [{"name", "log_source"}],
    "missing_categories": [str]}], one entry per affected technique.
    Never mutates `results` or changes state/coverage/ranking.
    """
    covered_confidence = (
        COVERED_CONFIDENCE if covered_confidence is None else covered_confidence
    )
    partial_confidence = (
        PARTIAL_CONFIDENCE if partial_confidence is None else partial_confidence
    )
    index = index if index is not None else DEFAULT

    provided = set(
        _categories_provided(list(log_sources or []) + list(tooling or []), _LOG_SOURCE_RULES)
    )

    # canonical technique id -> [use_case, ...] with a qualifying mapping
    # (same floor compute_quality uses: >= partial_confidence).
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
            if float(confidence) < partial_confidence:
                continue
            hits.setdefault(canonical, []).append(uc)

    flagged = []
    for entry in results or []:
        if entry.get("state") not in ("covered", "partial"):
            continue
        tech_hits = hits.get(entry["technique_id"])
        if not tech_hits:
            continue
        rule_info = []
        for uc in tech_hits:
            categories = _rule_categories(uc)
            if not categories:
                continue  # nothing category-recognizable -- not this rule's call
            rule_info.append((uc.get("name") or uc.get("row_ref") or "rule",
                               uc.get("log_source"), categories))
        if not rule_info:
            continue
        if all(not (cats & provided) for _, _, cats in rule_info):
            missing = sorted({c for _, _, cats in rule_info for c in cats})
            flagged.append({
                "technique_id": entry["technique_id"],
                "rules": [{"name": name, "log_source": src} for name, src, _ in rule_info],
                "missing_categories": missing,
            })
    return flagged


def unmonitored_capability_check(assets, tooling, log_sources, gaps, *,
                                  classes=None) -> list:
    """Plan phase A10 piece 4 -- the "Infoblox problem": a device whose
    main security value depends on one telemetry category can sit in the
    customer's own Assets/Security Tooling sheets while that category is
    never declared in Log Sources, silently useless for detection.

    For each curated class in data/device_classes.json matched (by
    keyword substring, same discipline as ranking.py's _categories_provided)
    against an Assets or Security Tooling entry: if NONE of the customer's
    declared Log Sources map (via ranking.py's category bridge, reused --
    no second normalizer) to that class's expected_category, emit ONE
    aggregated finding for the class (never per-gap). N is the count of
    ranked gaps whose category equals the missing telemetry category
    (those gaps are already mid/long feasibility precisely because the
    category was never onboarded); a class with zero such gaps is skipped
    -- nothing actionable to say, so stay silent rather than print "0
    gaps". Caller gates on a Log Sources sheet actually having been
    uploaded (no sheet -> no claim, never called at all in that case).

    Returns [{"class_id", "label", "matched_entry", "telemetry_label",
    "capability", "gap_count", "technique_ids", "message"}], one per
    flagged class. Never mutates assets/tooling/log_sources/gaps.
    """
    if classes is None:
        from .attack_data import load_device_classes
        classes = load_device_classes()

    provided = set(_categories_provided(list(log_sources or []), _LOG_SOURCE_RULES))
    entries = list(assets or []) + list(tooling or [])
    entries_norm = [(entry, _norm(entry)) for entry in entries]

    findings = []
    for cls in classes.get("classes", []):
        matched_entry = None
        for entry, entry_norm in entries_norm:
            if any(kw in entry_norm for kw in cls["keywords"]):
                matched_entry = entry
                break
        if matched_entry is None:
            continue  # class not present in this environment -- nothing to say
        if cls["expected_category"] in provided:
            continue  # customer already declares that telemetry -- silent
        category_gaps = [g for g in gaps or [] if g.get("category") == cls["expected_category"]]
        if not category_gaps:
            continue  # nothing actionable to lift -- stay silent, don't print "0 gaps"
        top_ids = [g["technique_id"] for g in category_gaps[:5]]
        gap_count = len(category_gaps)
        findings.append({
            "class_id": cls["id"],
            "label": cls["label"],
            "matched_entry": str(matched_entry),
            "telemetry_label": cls["telemetry_label"],
            "capability": cls["capability"],
            "gap_count": gap_count,
            "technique_ids": top_ids,
            "message": (
                f"Your inventory lists a {cls['label']} ({matched_entry}), but no "
                f"{cls['telemetry_label']} is declared. Its main security value — "
                f"{cls['capability']} — appears unmonitored. Declaring/enabling "
                f"{cls['telemetry_label']} would move {gap_count} gap"
                f"{'s' if gap_count != 1 else ''} closer to buildable "
                f"(e.g. {', '.join(top_ids)})."
            ),
        })
    return findings


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
