"""Constants/helpers shared between report.py (HTML/PDF) and report_xlsx.py
(XLSX) — split out in Phase 14h so neither builder has to import the other
(report.py re-exports these names so existing imports/tests are unaffected).
"""

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
