"""Plain-language technique content + deterministic why-phrases (Phase 14a).

Two curated, hand-written data files (never runtime-LLM):
- data/technique_plain_language.json — definition / attacker_use /
  detection_hint per curated technique (the technique_priorities.json ∪
  threat_profiles.json union — the IDs that realistically surface as top
  gaps). Long tail falls back to the first sentence of the ATT&CK
  description already in attack.json.
- data/tactic_lines.json — one story line per tactic shortname, all domains.

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


PLAIN = load_plain_language()["techniques"]
TACTIC_LINES = load_tactic_lines()["tactics"]


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
