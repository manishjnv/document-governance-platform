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
