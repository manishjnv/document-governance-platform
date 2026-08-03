"""Constants/helpers shared between report.py (HTML/PDF) and report_xlsx.py
(XLSX) — split out in Phase 14h so neither builder has to import the other
(report.py re-exports these names so existing imports/tests are unaffected).
"""

import re

STATE_LABELS = {
    "covered": "Covered",
    "partial": "Partial",
    "not_covered": "Not covered",
    "not_applicable": "N/A",
}
FEASIBILITY_LABELS = {"short": "Short term (0–3 mo)", "mid": "Mid term (3–9 mo)", "long": "Long term (9–18 mo)"}
DOMAIN_LABELS = {"enterprise": "Enterprise", "ics": "ICS / OT", "mobile": "Mobile"}
# Shared between the HTML appendix's "Status" column and the XLSX
# Use-Case Mappings sheet — despite the name, not XLSX-only.
_MAPPING_STATUS_PLAIN_XLSX = {
    "customer_tagged": "You tagged this",
    "keyword_tagged": "Matched by tool/technique keyword (no AI)",
    "ai_tagged": "AI-suggested — verify",
    "manual": "Edited by a reviewer",
    "unmapped": "Could not be mapped",
    "invalid": "Tags were invalid — treated as untagged",
}
# Canonical display order: the stored summary follows the ATT&CK dataset's
# dict order (ICS, Mobile, Enterprise), which buries Enterprise last.
_DOMAIN_ORDER = ("enterprise", "ics", "mobile")


def _ordered_domains(domains: dict):
    return sorted(
        (domains or {}).items(),
        key=lambda kv: _DOMAIN_ORDER.index(kv[0]) if kv[0] in _DOMAIN_ORDER else 99,
    )


def _row_ref_sort_key(uc: dict):
    """Numeric-aware sort for row refs ('Rules:2' before 'Rules:10')."""
    import re as _re

    ref = str(uc.get("row_ref") or "")
    return (
        _re.sub(r"\d+", "#", ref),
        [int(n) for n in _re.findall(r"\d+", ref)],
    )


# --- Phase 14h: report branding -------------------------------------------
# Keys mirror app.mitre.service.SETTING_DEFAULTS's report_* tunables, kept
# as literal defaults here (not imported from service.py) so this leaf
# module doesn't pull in the settings/pipeline import graph.
DEFAULT_BRANDING = {
    "report_display_name": "ScopeWise",
    "report_accent_color": "#0057B8",
    "report_watermark_text": "",
}

_HEX_COLOR_RE = re.compile(r"^#[0-9A-Fa-f]{6}$")


def resolve_branding(branding: dict | None) -> dict:
    """Merge caller-supplied branding overrides over the platform defaults.

    The accent color is re-validated here (not just at settings-write time
    in service.validate_setting) because report.py interpolates it directly
    into a <style> block as a CSS color token — HTML-escaping (_esc) is the
    wrong defense for a CSS context, so a strict hex-color allowlist regex
    is used instead, falling back to the platform default on any mismatch.
    """
    merged = {**DEFAULT_BRANDING, **(branding or {})}
    color = merged.get("report_accent_color")
    if not isinstance(color, str) or not _HEX_COLOR_RE.match(color):
        merged["report_accent_color"] = DEFAULT_BRANDING["report_accent_color"]
    return merged


# --- Phase A10 piece 3: coverage by log source ----------------------------

OTHER_LOG_SOURCE = "Other / unrecognized"


def compute_log_source_coverage(use_cases, technique_results, index) -> list:
    """Deterministic read-time grouping (plan phase A10 piece 3): detection
    rules grouped by their log_source, normalized through ranking.py's own
    text normalizer (``ranking._norm`` — reused, never a second one) so
    case/punctuation variants of the same source collapse into one group;
    the group's display name is the first raw log_source text seen. Rules
    with no log_source (or nothing recognizable) land in
    ``OTHER_LOG_SOURCE`` — never dropped. No pipeline change: use_cases and
    technique_results are the exact same stored data every other read-time
    view (drill-downs, explain endpoint) already consumes.

    Returns [{"log_source", "rule_count", "techniques_covered", "tactics",
    "techniques": [{"technique_id", "name", "state"}], "row_refs": [...]}],
    sorted by rule count (desc) then log source name, with
    ``OTHER_LOG_SOURCE`` always last regardless of count. Pure; no AI.
    """
    from .ranking import _norm as _log_source_norm

    results_by_id = {r.get("technique_id"): r for r in technique_results or []}
    groups: dict = {}
    for uc in use_cases or []:
        raw = str(uc.get("log_source") or "").strip()
        key = _log_source_norm(raw) if raw else ""
        display = raw or OTHER_LOG_SOURCE
        bucket = groups.setdefault(
            key, {"display": display, "rule_count": 0, "technique_ids": set(), "row_refs": []}
        )
        bucket["rule_count"] += 1
        if uc.get("row_ref"):
            bucket["row_refs"].append(uc["row_ref"])
        for mapping in uc.get("mappings") or []:
            canonical, _status = index.resolve(
                str(mapping.get("technique_id", "")).strip().upper()
            )
            if canonical:
                bucket["technique_ids"].add(canonical)

    rows = []
    for bucket in groups.values():
        techniques = []
        tactics = set()
        for tid in sorted(bucket["technique_ids"]):
            result = results_by_id.get(tid)
            tech = index.get(tid) or {}
            techniques.append({
                "technique_id": tid,
                "name": tech.get("name", tid),
                "state": result.get("state") if result else None,
            })
            if result:
                tactic_names = {t["id"]: t["name"] for t in index.tactics(result.get("domain"))}
                tactics.update(
                    tactic_names[t] for t in (result.get("tactics") or []) if t in tactic_names
                )
        rows.append({
            "log_source": bucket["display"],
            "rule_count": bucket["rule_count"],
            "techniques_covered": len(techniques),
            "tactics": sorted(tactics),
            "techniques": techniques,
            "row_refs": bucket["row_refs"],
        })

    rows.sort(key=lambda r: (r["log_source"] == OTHER_LOG_SOURCE, -r["rule_count"], r["log_source"]))
    return rows
