"""Plain-language technique content + deterministic why-phrases (Phase 14a).

Three curated, hand-written data files (never runtime-LLM):
- data/technique_plain_language.json — definition / attacker_use /
  detection_hint per curated technique (the technique_priorities.json ∪
  threat_profiles.json union — the IDs that realistically surface as top
  gaps). Long tail falls back to the first sentence of the ATT&CK
  description already in attack.json.
- data/tactic_lines.json — one story line per tactic shortname, all domains.
- data/telemetry_fields.json — Phase 14h "what logs do I need?": per
  ATT&CK data-source component, the plain-English query fields, the usual
  event source, and the single most common reason an already-onboarded
  source still can't support the detection. Long tail falls back to the
  bare component name.

``derive_why`` turns one technique's stored result + its mapped rules into
the one-sentence "why is it a gap / why does it count" — pure, reused by the
drawer explain endpoint now and the Phase 14c XLSX "Why" column later.
"""

import json

from .attack_data import DATA_DIR, DEFAULT


def load_plain_language() -> dict:
    return json.loads(
        (DATA_DIR / "technique_plain_language.json").read_text(encoding="utf-8")
    )


def load_tactic_lines() -> dict:
    return json.loads((DATA_DIR / "tactic_lines.json").read_text(encoding="utf-8"))


def load_telemetry_fields() -> dict:
    return json.loads(
        (DATA_DIR / "telemetry_fields.json").read_text(encoding="utf-8")
    )


PLAIN = load_plain_language()["techniques"]
TACTIC_LINES = load_tactic_lines()["tactics"]
TELEMETRY_FIELDS = load_telemetry_fields()["components"]


def describe_technique(technique_id: str, index=None) -> dict:
    """Curated plain-language entry, or the ATT&CK first-sentence fallback.

    Returns {"definition", "attacker_use", "detection_hint", "curated"} —
    the last three are None for uncurated techniques.
    """
    entry = PLAIN.get(technique_id)
    if entry:
        return {
            "definition": entry.get("definition"),
            "attacker_use": entry.get("attacker_use"),
            "detection_hint": entry.get("detection_hint"),
            "curated": True,
        }
    index = index if index is not None else DEFAULT
    summary = ((index.get(technique_id) or {}).get("summary") or "").strip()
    first = summary.split(". ")[0].strip()
    if first and not first.endswith("."):
        first += "."
    return {
        "definition": first or None,
        "attacker_use": None,
        "detection_hint": None,
        "curated": False,
    }


def detection_sketch(technique_id: str, via) -> str:
    """Deterministic 'what would good look like' template (coding-over-AI).

    Only curated techniques have a hint; returns None for the long tail —
    callers fall back to the gap hint / AI recommendation they already show.
    """
    hint = describe_technique(technique_id)["detection_hint"]
    if not hint:
        return None
    if via:
        return f"Using {via}, alert on: {hint}."
    return f"Alert on: {hint}."


def telemetry_requirements(technique_id: str, index=None) -> list:
    """Phase 14h 'what logs do I need?': per ATT&CK data-source component
    this technique lists, the curated {component, fields, where, gotcha}
    entry, or {"component": name, "fields": [], "where": None, "gotcha":
    None} for the long tail (no invented guidance). Techniques with no
    data_sources at all return []. Deterministic, no LLM, no network."""
    index = index if index is not None else DEFAULT
    tech = index.get(technique_id) or {}
    results = []
    for component in tech.get("data_sources") or []:
        entry = TELEMETRY_FIELDS.get(component)
        results.append({
            "component": component,
            "fields": (entry or {}).get("fields") or [],
            "where": (entry or {}).get("where"),
            "gotcha": (entry or {}).get("gotcha"),
        })
    return results


def telemetry_lines(technique_id: str, index=None) -> list:
    """One display line per curated telemetry component: 'Component — your
    query needs: <fields>. <where> <gotcha>'. Uncurated components (empty
    fields) are skipped — no invented guidance. Shared by the XLSX and PDF
    report builders so the wording stays identical across surfaces."""
    lines = []
    for entry in telemetry_requirements(technique_id, index):
        if not entry["fields"]:
            continue
        lines.append(
            f"{entry['component']} — your query needs: "
            f"{', '.join(entry['fields'])}. {entry['where']} {entry['gotcha']}"
        )
    return lines


def sub_states_for(result: dict, mapped_rules: list, state_by_id: dict, index=None):
    """For a partial parent with no direct rules: the live sub-technique
    states that explain the rollup (None otherwise). Shared by the drawer
    explain endpoint and the XLSX 'Why' column."""
    if result.get("state") != "partial" or mapped_rules:
        return None
    index = index if index is not None else DEFAULT
    children = index.children.get(result.get("technique_id")) or []
    if not children:
        return None
    return [
        {
            "technique_id": c["id"],
            "name": c.get("name"),
            "state": state_by_id.get(c["id"], "not_covered"),
        }
        for c in children
        if not c.get("revoked") and not c.get("deprecated")
    ]


def _source_phrase(rule: dict) -> str:
    source = rule.get("source")
    if source == "customer":
        return "tagged by you"
    if source == "keyword":
        return "matched by rule keyword"
    if source == "manual":
        return "set by your reviewer"
    pct = round((rule.get("confidence") or 0) * 100)
    return f"AI-mapped at {pct}% confidence"


def _quote_names(rules: list) -> str:
    return " and ".join(f"'{r.get('name')}'" for r in rules)


def derive_why(
    result: dict,
    mapped_rules: list,
    *,
    total_rules=None,
    sub_states=None,
    confidence_covered: float = 0.7,
) -> str:
    """One plain-English sentence explaining a technique's state.

    result: one stored technique_results entry (state, na_reason, strength).
    mapped_rules: [{"name", "enabled", "source", "confidence"}] — the rules
    with a mapping to this technique. sub_states: for parent techniques,
    [{"technique_id", "name", "state"}] per live sub-technique (rollup case).
    Pure and deterministic — golden-tested.
    """
    state = result.get("state")
    if state == "not_applicable":
        return result.get("na_reason") or "Not applicable to your environment."

    if state == "covered":
        qualifying = [
            r for r in mapped_rules
            if r.get("enabled") is not False
            and (r.get("confidence") or 0) >= confidence_covered
        ] or mapped_rules
        if not qualifying:
            return "Covered by a mapped detection rule."
        shown = qualifying[:3]
        parts = ", ".join(f"'{r.get('name')}' ({_source_phrase(r)})" for r in shown)
        more = f" and {len(qualifying) - 3} more" if len(qualifying) > 3 else ""
        noun = "rules" if len(qualifying) > 1 else "rule"
        sentence = f"Covered by your {noun} {parts}{more}."
        if isinstance(result.get("strength"), (int, float)):
            sentence += f" Detection strength {round(result['strength'])}/100."
        return sentence

    if state == "partial":
        disabled = [r for r in mapped_rules if r.get("enabled") is False]
        if disabled:
            names = _quote_names(disabled[:2])
            verb = "covers this but is" if len(disabled) == 1 else "cover this but are"
            noun = "rule" if len(disabled) == 1 else "rules"
            return (
                f"Your {noun} {names} {verb} disabled in your SIEM — "
                "enable it to close this gap."
            )
        low_confidence = [
            r for r in mapped_rules
            if 0 < (r.get("confidence") or 0) < confidence_covered
        ]
        if low_confidence:
            best = max(low_confidence, key=lambda r: r.get("confidence") or 0)
            pct = round((best.get("confidence") or 0) * 100)
            return (
                f"Rule '{best.get('name')}' probably covers this "
                f"(AI-tagged at {pct}% confidence) — confirm the mapping to "
                "count it as covered."
            )
        if sub_states:
            covered = [s for s in sub_states if s.get("state") == "covered"]
            listed = ", ".join(
                f"{s['technique_id']} {s.get('name') or ''}".strip()
                for s in covered[:4]
            )
            verb = "is" if len(covered) == 1 else "are"
            return (
                "No rule maps to this technique directly — only "
                f"{len(covered)} of its {len(sub_states)} sub-techniques "
                f"{verb} covered ({listed})."
            )
        return (
            "A related mapping gives this technique partial credit — "
            "review its mapped rules to confirm."
        )

    if total_rules:
        noun = "rule" if total_rules == 1 else "rules"
        return f"None of your {total_rules} {noun} maps to this technique."
    return "None of your uploaded rules maps to this technique."
