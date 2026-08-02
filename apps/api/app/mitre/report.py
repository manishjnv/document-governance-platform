"""MITRE assessment reports: exec+detailed HTML/PDF and the XLSX gap
register (plan §10).

Numbers come ONLY from the stored summary/technique_results JSONB — never
recomputed here, never parsed out of narrative text. Every customer/LLM
string goes through _esc (HTML) or _guard (XLSX formula injection): rule
names, descriptions, exclusion reasons, and narrative output are all
attacker-controlled.

PDF rendering reuses the house WeasyPrint approach (app/scoring/report.py):
lazily imported because its native libs (Pango/Cairo) only exist in the
prod image — local dev fails soft at call time, not import time.
"""

import io
import logging
import os
from datetime import datetime, timezone

from app.scoring.report import _esc  # house escaper, stored-XSS lesson baked in

logger = logging.getLogger(__name__)

STATE_LABELS = {
    "covered": "Covered",
    "partial": "Partial",
    "not_covered": "Not covered",
    "not_applicable": "N/A",
}
STATE_COLORS = {
    "covered": "#10b981",
    "partial": "#f59e0b",
    "not_covered": "#f43f5e",
    "not_applicable": "#9ca3af",
}
FEASIBILITY_LABELS = {"short": "Short term (0–3 mo)", "mid": "Mid term (3–9 mo)", "long": "Long term (9–18 mo)"}
DOMAIN_LABELS = {"enterprise": "Enterprise", "ics": "ICS / OT", "mobile": "Mobile"}

# PDF appendix cap — a 5,000-row use-case appendix belongs in the XLSX, not
# a PDF. The cap is stated in the report when it bites.
MAX_APPENDIX_ROWS = 500

_NA_GROUPS = [
    ("Whole matrix not applicable", lambda r: "matrix:" in r),
    ("Platform not in the environment", lambda r: r.startswith("targets ")),
    ("Deprecated by MITRE", lambda r: r.startswith("deprecated in ATT&CK")),
    ("Customer-declared exclusions", lambda r: True),
]


def _pct_bar(pct: float, color: str = "#0057B8") -> str:
    width = max(0.0, min(100.0, float(pct or 0)))
    return (
        '<div style="background:#e5e7eb;border-radius:4px;height:10px;width:100%;">'
        f'<div style="background:{color};border-radius:4px;height:10px;width:{width}%;"></div></div>'
    )


def _state_chip(state: str) -> str:
    return (
        f'<span style="color:{STATE_COLORS.get(state, "#333")};font-weight:600;">'
        f"{_esc(STATE_LABELS.get(state, state))}</span>"
    )


def build_html_report(assessment, use_cases: list) -> str:
    """Executive + detailed report as one self-contained HTML document.

    assessment: MitreAssessment ORM row (or anything with the same
    attributes). use_cases: list of dicts {row_ref, name, description,
    log_source, enabled, mappings, mapping_status}.
    """
    summary = assessment.summary or {}
    params = assessment.params or {}
    overall = summary.get("overall", {})
    domains = summary.get("domains", {})
    gaps = summary.get("gaps", [])
    roadmap = summary.get("roadmap", {})
    narrative = summary.get("narrative", {})
    assumptions = summary.get("assumptions", [])
    not_applicable = summary.get("not_applicable", [])

    completed = assessment.completed_at.strftime("%Y-%m-%d %H:%M UTC") if assessment.completed_at else "—"

    # --- executive block -------------------------------------------------
    domain_rows = "".join(
        f"<tr><td>{_esc(DOMAIN_LABELS.get(key, key))}</td>"
        f"<td class='num'>{_esc(d.get('strict_pct'))}%</td>"
        f"<td class='num'>{_esc(d.get('weighted_pct'))}%</td>"
        f"<td class='num'>{_esc(d.get('covered'))}/{_esc(d.get('applicable'))}</td>"
        f"<td style='width:35%'>{_pct_bar(d.get('strict_pct', 0))}</td></tr>"
        for key, d in domains.items()
        if d.get("applicable", 0) > 0
    )
    gated_notes = "".join(
        f"<p class='muted'>{_esc(DOMAIN_LABELS.get(key, key))}: not assessed — "
        f"{_esc(next((n['reason'] for n in not_applicable if n.get('domain') == key), ''))}</p>"
        for key, d in domains.items()
        if d.get("applicable", 0) == 0
    )
    top_gaps_html = "".join(
        f"<li><strong>{_esc(g.get('technique_id'))}</strong> {_esc(g.get('name'))} — "
        f"{_esc(narrative.get('gap_recommendations', {}).get(g.get('technique_id')) or g.get('hint'))}</li>"
        for g in gaps[:5]
    )
    roadmap_glance = " · ".join(
        f"{_esc(FEASIBILITY_LABELS[b])}: {len(roadmap.get(b, []))}" for b in ("short", "mid", "long")
    )

    # --- per-tactic tables ----------------------------------------------
    tactic_sections = ""
    for key, d in domains.items():
        if d.get("applicable", 0) == 0:
            continue
        rows = "".join(
            f"<tr><td>{_esc(t.get('name'))}</td>"
            f"<td class='num'>{_esc(t.get('covered'))}</td>"
            f"<td class='num'>{_esc(t.get('partial'))}</td>"
            f"<td class='num'>{_esc(t.get('not_covered'))}</td>"
            f"<td class='num'>{_esc(t.get('not_applicable'))}</td>"
            f"<td class='num'>{_esc(t.get('strict_pct'))}%</td>"
            f"<td style='width:25%'>{_pct_bar(t.get('strict_pct', 0))}</td></tr>"
            for t in d.get("tactics", [])
        )
        tactic_sections += (
            f"<h3>{_esc(DOMAIN_LABELS.get(key, key))} — coverage by tactic</h3>"
            "<table><thead><tr><th>Tactic</th><th>Covered</th><th>Partial</th>"
            "<th>Not covered</th><th>N/A</th><th>Strict %</th><th></th></tr></thead>"
            f"<tbody>{rows}</tbody></table>"
        )

    # --- gap register ----------------------------------------------------
    gap_rows = "".join(
        f"<tr><td class='num'>{_esc(g.get('rank'))}</td>"
        f"<td><strong>{_esc(g.get('technique_id'))}</strong><br><span class='muted'>{_esc(g.get('name'))}</span></td>"
        f"<td class='num'>{'P' + str(g['tier']) if g.get('tier', 4) < 4 else '—'}</td>"
        f"<td>{_esc(FEASIBILITY_LABELS.get(g.get('feasibility'), g.get('feasibility')))}</td>"
        f"<td>{_state_chip(g.get('state', ''))}</td>"
        f"<td>{_esc(narrative.get('gap_recommendations', {}).get(g.get('technique_id')) or g.get('hint'))}</td></tr>"
        for g in gaps
    )

    # --- roadmap detail --------------------------------------------------
    roadmap_sections = ""
    for bucket in ("short", "mid", "long"):
        items = roadmap.get(bucket, [])
        prose = narrative.get("roadmap_prose", {}).get(bucket, "")
        item_rows = "".join(
            f"<tr><td><strong>{_esc(g.get('technique_id'))}</strong> {_esc(g.get('name'))}</td>"
            f"<td>{_esc(g.get('hint'))}</td></tr>"
            for g in items
        )
        roadmap_sections += (
            f"<h3>{_esc(FEASIBILITY_LABELS[bucket])} — {len(items)} item(s)</h3>"
            f"<p class='muted'>{_esc(prose)}</p>"
            + (f"<table><tbody>{item_rows}</tbody></table>" if items else "")
        )

    # --- assumptions + N/A appendix -------------------------------------
    assumptions_html = "".join(f"<li>{_esc(a)}</li>" for a in assumptions)
    na_sections = ""
    remaining = list(not_applicable)
    for title, match in _NA_GROUPS:
        grouped = [n for n in remaining if match(n.get("reason") or "")]
        remaining = [n for n in remaining if n not in grouped]
        if not grouped:
            continue
        rows = "".join(
            f"<tr><td>{_esc(n.get('technique_id'))}</td>"
            f"<td>{_esc(DOMAIN_LABELS.get(n.get('domain'), n.get('domain')))}</td>"
            f"<td>{_esc(n.get('reason'))}</td></tr>"
            for n in grouped
        )
        na_sections += (
            f"<h3>{_esc(title)} ({len(grouped)})</h3>"
            "<table><thead><tr><th>Technique</th><th>Matrix</th><th>Reason</th></tr></thead>"
            f"<tbody>{rows}</tbody></table>"
        )

    # --- use-case appendix ----------------------------------------------
    appendix_note = ""
    shown_use_cases = use_cases
    if len(use_cases) > MAX_APPENDIX_ROWS:
        shown_use_cases = use_cases[:MAX_APPENDIX_ROWS]
        appendix_note = (
            f"<p class='muted'>Showing the first {MAX_APPENDIX_ROWS} of "
            f"{len(use_cases)} rules — the XLSX export contains all of them.</p>"
        )
    uc_rows = "".join(
        f"<tr><td>{_esc(uc.get('row_ref'))}</td><td>{_esc(uc.get('name'))}</td>"
        f"<td>{'Enabled' if uc.get('enabled') else ('Disabled' if uc.get('enabled') is False else 'Unknown')}</td>"
        f"<td>{_esc(', '.join(m.get('technique_id', '') for m in (uc.get('mappings') or [])) or '—')}</td>"
        f"<td>{_esc(uc.get('mapping_status'))}</td>"
        f"<td>{_esc(uc.get('log_source') or '')}</td></tr>"
        for uc in shown_use_cases
    )

    # --- audit footer ----------------------------------------------------
    thresholds = params.get("thresholds", {})
    models_used = params.get("models_used", {})
    footer_bits = [
        f"ATT&amp;CK v{_esc(assessment.attack_version)}",
        f"generated {_esc(datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC'))}",
        f"run completed {_esc(completed)}",
        f"narrative: {_esc(narrative.get('generated_by', 'n/a'))}"
        + (f" ({_esc(narrative.get('model_used'))})" if narrative.get("model_used") else ""),
    ]
    if os.getenv("GIT_SHA"):
        footer_bits.append(f"build {_esc(os.getenv('GIT_SHA'))}")
    if models_used:
        footer_bits.append(
            "models: " + _esc("; ".join(f"{k}: {', '.join(v)}" for k, v in models_used.items()))
        )
    siem = params.get("siem") or {}
    if siem:
        # Phase 13d provenance: which SIEM, manual vs scheduled, when.
        # Non-secret fields only (workspace_ref never holds credentials).
        source_bits = [
            "source: Microsoft Sentinel pull",
            _esc(siem.get("trigger") or "manual"),
        ]
        if (siem.get("workspace_ref") or {}).get("workspace"):
            source_bits.append(_esc(siem["workspace_ref"]["workspace"]))
        if siem.get("connection_name"):
            source_bits.append(_esc(siem["connection_name"]))
        if siem.get("pulled_at"):
            source_bits.append("pulled " + _esc(str(siem["pulled_at"])[:16]))
        footer_bits.append(" · ".join(source_bits))
    if thresholds:
        footer_bits.append(
            _esc(
                f"thresholds: covered≥{thresholds.get('confidence_covered')}, "
                f"partial≥{thresholds.get('confidence_partial_floor')}, "
                f"partial credit {thresholds.get('partial_credit')}, "
                f"disabled counts: {'yes' if thresholds.get('count_disabled_as_coverage') else 'no'}"
            )
        )

    counts = summary.get("counts", {})
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<title>MITRE ATT&amp;CK Coverage Assessment — {_esc(assessment.name)}</title>
<style>
@page {{ size: A4; margin: 1.5cm; }}
* {{ margin: 0; padding: 0; box-sizing: border-box; }}
body {{ font-family: Arial, 'Liberation Sans', Helvetica, sans-serif; color: #333; line-height: 1.5; font-size: 12px; }}
.container {{ max-width: 900px; margin: 0 auto; padding: 8px; }}
h1 {{ font-size: 20px; color: #0057B8; margin-bottom: 2px; }}
h2 {{ font-size: 15px; color: #003D82; margin: 18px 0 6px; border-bottom: 2px solid #0057B8; padding-bottom: 3px; }}
h3 {{ font-size: 13px; margin: 12px 0 4px; }}
p {{ margin: 4px 0; }}
.muted {{ color: #6b7280; font-size: 11px; }}
.headline {{ font-size: 34px; font-weight: bold; color: #0057B8; }}
.tiles {{ display: flex; gap: 8px; margin: 8px 0; }}
.tile {{ flex: 1; background: #f3f4f6; border-radius: 6px; padding: 8px; text-align: center; }}
.tile b {{ display: block; font-size: 18px; }}
table {{ width: 100%; border-collapse: collapse; margin: 6px 0 10px; font-size: 11px; }}
th {{ text-align: left; background: #f3f4f6; padding: 4px 6px; border-bottom: 1px solid #d1d5db; }}
td {{ padding: 4px 6px; border-bottom: 1px solid #e5e7eb; vertical-align: top; }}
td.num {{ text-align: right; white-space: nowrap; }}
ul {{ margin: 4px 0 4px 18px; }}
.footer {{ margin-top: 20px; padding-top: 8px; border-top: 1px solid #d1d5db; font-size: 10px; color: #6b7280; }}
</style>
</head>
<body><div class="container">
<h1>MITRE ATT&amp;CK Coverage Assessment</h1>
<p><strong>{_esc(assessment.name)}</strong></p>
<p class="muted">Methodology: coverage is computed deterministically against the pinned
MITRE ATT&amp;CK v{_esc(assessment.attack_version)} dataset; techniques impossible in this
environment (or excluded by the customer) leave the denominator as “not applicable”.
A technique counts as covered when at least one enabled rule maps to it with qualifying
confidence. This assessment scores detection <em>presence</em>, not rule efficacy.</p>

<h2>Executive summary</h2>
<div class="tiles">
  <div class="tile"><b class="headline">{_esc(overall.get('strict_pct'))}%</b>coverage of applicable techniques<br>
  <span class="muted">weighted (partial = half): {_esc(overall.get('weighted_pct'))}%</span></div>
  <div class="tile"><b style="color:#10b981">{_esc(overall.get('covered'))}</b>covered</div>
  <div class="tile"><b style="color:#f59e0b">{_esc(overall.get('partial'))}</b>partial</div>
  <div class="tile"><b style="color:#f43f5e">{_esc(overall.get('not_covered'))}</b>not covered</div>
  <div class="tile"><b>{_esc(overall.get('not_applicable'))}</b>not applicable</div>
</div>
<p>{_esc(narrative.get('executive_summary', ''))}</p>
<table><thead><tr><th>Matrix</th><th>Strict</th><th>Weighted</th><th>Covered</th><th></th></tr></thead>
<tbody>{domain_rows}</tbody></table>
{gated_notes}
<h3>Top 5 gaps</h3>
<ul>{top_gaps_html}</ul>
<p><strong>Roadmap at a glance:</strong> {roadmap_glance}</p>
<p class="muted">Rules analyzed: {_esc(counts.get('use_cases'))} ({_esc(counts.get('customer_tagged'))} customer-tagged,
{_esc(counts.get('ai_tagged'))} AI-tagged, {_esc(counts.get('unmapped'))} unmapped, {_esc(counts.get('invalid'))} invalid tags)</p>

<h2>Coverage by tactic</h2>
{tactic_sections}

<h2>Gap register ({len(gaps)})</h2>
<table><thead><tr><th>#</th><th>Technique</th><th>Priority</th><th>Feasibility</th><th>State</th><th>Recommendation</th></tr></thead>
<tbody>{gap_rows}</tbody></table>

<h2>Remediation roadmap</h2>
{roadmap_sections}

<h2>Assumptions</h2>
<ul>{assumptions_html or '<li>None.</li>'}</ul>

<h2>Not-applicable appendix ({len(not_applicable)})</h2>
<p class="muted">These techniques leave the coverage denominator — the headline percentage
makes no claim about them.</p>
{na_sections}

<h2>Use-case mapping appendix ({len(use_cases)})</h2>
{appendix_note}
<table><thead><tr><th>Row</th><th>Rule</th><th>Status</th><th>Techniques</th><th>Mapping</th><th>Log source</th></tr></thead>
<tbody>{uc_rows}</tbody></table>

<div class="footer">{' · '.join(footer_bits)}</div>
</div></body></html>"""


def generate_pdf(html_content: str) -> bytes:
    """HTML -> PDF. Lazy import: WeasyPrint's native libs exist only in the
    prod image (Dockerfile.prod) — see app/scoring/report.py precedent."""
    from weasyprint import HTML

    return HTML(string=html_content).write_pdf()


# ---------------------------------------------------------------------------
# XLSX export
# ---------------------------------------------------------------------------


def _guard(value):
    """Excel formula-injection guard (plan §10): a leading =, +, - or @ in an
    attacker-controlled string (rule names, descriptions, reasons) would
    execute as a formula when the register opens in Excel."""
    if isinstance(value, str) and value[:1] in ("=", "+", "-", "@"):
        return "'" + value
    return value


# Phase 14c: fill colors (ARGB-less hex; light fills, dark text stays legible)
_XLSX_STATE_FILLS = {
    "covered": "C6EFCE",
    "partial": "FFE699",
    "not_covered": "FFC7CE",
    "not_applicable": "D9D9D9",
}
_XLSX_TIER_FILLS = {1: "F8CBAD", 2: "FFE699", 3: "FFF2CC"}
_XLSX_FEAS_FILLS = {"short": "C6EFCE", "mid": "FFE699", "long": "D9D9D9"}
_STATE_PLAIN_XLSX = {
    "covered": "A rule detects this",
    "partial": "Half-covered",
    "not_covered": "No rule detects this",
    "not_applicable": "Doesn't apply to this environment",
}
_MAPPING_STATUS_PLAIN_XLSX = {
    "customer_tagged": "You tagged this",
    "keyword_tagged": "Matched by tool/technique keyword (no AI)",
    "ai_tagged": "AI-suggested — verify",
    "manual": "Edited by a reviewer",
    "unmapped": "Could not be mapped",
    "invalid": "Tags were invalid — treated as untagged",
}


def _row_ref_sort_key(uc: dict):
    """Numeric-aware sort for row refs ('Rules:2' before 'Rules:10')."""
    import re as _re

    ref = str(uc.get("row_ref") or "")
    return (
        _re.sub(r"\d+", "#", ref),
        [int(n) for n in _re.findall(r"\d+", ref)],
    )


def build_xlsx_export(assessment, use_cases: list) -> bytes:
    """The detailed gap register as a 9-sheet workbook (Phase 14c polish):
    'Read Me' guide sheet first, colored state/priority/feasibility cells,
    frozen headers + auto-filter + wrapped text everywhere, technique names
    + plain-words 'Why' column, numerically sorted rule rows. Computed
    numbers are untouched — styling and wording only."""
    from openpyxl import Workbook
    from openpyxl.styles import Alignment, Font, PatternFill
    from openpyxl.utils import get_column_letter

    from app.mitre import attack_data, plain_language

    summary = assessment.summary or {}
    params = assessment.params or {}
    overall = summary.get("overall", {})
    narrative = summary.get("narrative", {})
    gap_recs = narrative.get("gap_recommendations", {})
    index = attack_data.DEFAULT

    wb = Workbook()
    bold = Font(bold=True)
    wrap = Alignment(wrap_text=True, vertical="top")

    def fill(color):
        return PatternFill(start_color=color, end_color=color, fill_type="solid")

    def sheet(title, headers, rows, widths, first=False, filters=True):
        ws = wb.active if first else wb.create_sheet()
        ws.title = title
        ws.append([_guard(h) for h in headers])
        for cell in ws[1]:
            cell.font = bold
        for row in rows:
            ws.append([_guard(v) for v in row])
        for row in ws.iter_rows(min_row=2):
            for cell in row:
                cell.alignment = wrap
        ws.freeze_panes = "A2"
        if filters and rows:
            ws.auto_filter.ref = ws.dimensions
        for i, width in enumerate(widths, start=1):
            ws.column_dimensions[get_column_letter(i)].width = width
        return ws

    # ---------------------------------------------------------------- Read Me
    strict_pct = overall.get("strict_pct")
    readme_rows = [
        ["This workbook is the full detail behind your MITRE ATT&CK coverage assessment."],
        [],
        ["The three key numbers"],
        [f"Coverage: {strict_pct}%",
         f"{overall.get('covered')} of {overall.get('applicable')} techniques that "
         "apply to your environment have at least one detection rule."],
        [f"Gaps to work on: {len(summary.get('gaps', []))}",
         "Ranked by priority in the 'Gaps & Recommendations' sheet — start at the top."],
        [f"Rules analyzed: {(summary.get('counts') or {}).get('use_cases', len(use_cases))}",
         "Your uploaded detection rules — see 'Use-Case Mappings' for what each one maps to."],
        [f"Is {strict_pct}% bad? Probably not: early SIEM detection programs typically "
         "start under 10%, because ATT&CK counts every known attacker technique. "
         "The roadmap matters more than the grade."],
        [],
        ["What each sheet contains"],
        ["Summary", "The headline numbers with a plain-words explanation of each."],
        ["Coverage by Tactic", "Coverage per attack stage (tactic), per matrix."],
        ["Technique Register", "Every technique: its state, why, and the rules mapped to it."],
        ["Use-Case Mappings", "Your rules, one per row, with how each was mapped."],
        ["Gaps & Recommendations", "What's missing, grouped by how soon you could fix it."],
        ["Roadmap", "The same gaps as a short/mid/long-term work plan."],
        ["Not Applicable", "Techniques that don't count toward your score, with reasons."],
        ["Assumptions", "What we had to assume — read before trusting the numbers."],
        [],
        ["Color legend"],
        ["Covered", "A rule detects this technique."],
        ["Partial", "Only a disabled rule, a low-confidence mapping, or a sub-technique reaches it."],
        ["Not covered", "No rule detects it — this is a gap."],
        ["N/A", "Doesn't apply to your environment; excluded from the score."],
    ]
    ws_readme = sheet("Read Me", ["How to read this workbook", ""],
                      readme_rows, [46, 100], first=True, filters=False)
    for label, color in (("Covered", "covered"), ("Partial", "partial"),
                         ("Not covered", "not_covered"), ("N/A", "not_applicable")):
        for row in ws_readme.iter_rows(min_row=2, max_col=1):
            if row[0].value == label:
                row[0].fill = fill(_XLSX_STATE_FILLS[color])
    for row in ws_readme.iter_rows(min_row=2, max_col=1):
        if row[0].value in ("The three key numbers", "What each sheet contains", "Color legend"):
            row[0].font = bold

    # ---------------------------------------------------------------- Summary
    domain_rows = [
        [f"{DOMAIN_LABELS.get(k, k)} coverage %", d.get("strict_pct"),
         f"Coverage within the {DOMAIN_LABELS.get(k, k)} matrix only."]
        for k, d in summary.get("domains", {}).items()
    ]
    # Phase 14d: optional project metadata rows (only when provided).
    intake = params.get("intake") or {}
    metadata_rows = [
        [label, intake[key], meaning]
        for key, label, meaning in (
            ("project_name", "Organization / project", "Who this assessment is for."),
            ("scope_label", "Scope", "The department or scope this run covers."),
            ("prepared_by", "Prepared by", "Who prepared this assessment."),
            ("purpose_note", "Purpose", "Why this assessment was run."),
        )
        if intake.get(key)
    ]
    sheet(
        "Summary",
        ["Metric", "Value", "What it means"],
        [
            ["Assessment", assessment.name, "The name this run was saved under."],
        ]
        + metadata_rows
        + [
            ["ATT&CK version", assessment.attack_version,
             "The MITRE ATT&CK release the assessment is pinned to."],
            ["Completed", str(assessment.completed_at or ""), ""],
            ["Coverage %", overall.get("strict_pct"),
             "Of the techniques that apply to your environment, the share with at "
             "least one qualifying detection rule."],
            ["Weighted coverage %", overall.get("weighted_pct"),
             "Same, but half-covered techniques count as 0.5 instead of 0."],
            ["Covered", overall.get("covered"), "Techniques at least one enabled rule detects."],
            ["Partial", overall.get("partial"),
             "Techniques reached only by a disabled rule, a low-confidence mapping, "
             "or a covered sub-technique."],
            ["Not covered", overall.get("not_covered"), "Techniques no rule detects — the gaps."],
            ["Not applicable", overall.get("not_applicable"),
             "Techniques excluded from the score (wrong platform, excluded by you, or deprecated)."],
            ["Applicable techniques", overall.get("applicable"),
             "The denominator: techniques that apply to your environment."],
            ["Narrative", narrative.get("generated_by", ""),
             "Whether recommendation wording was AI-written or standard template text "
             "(numbers are computed either way)."],
            ["Thresholds", str(params.get("thresholds", {})),
             "The confidence cut-offs used to count a mapping as coverage."],
        ]
        + domain_rows,
        [26, 44, 78],
    )

    # ------------------------------------------------------ Coverage by Tactic
    sheet(
        "Coverage by Tactic",
        ["Matrix", "Tactic", "Covered", "Partial", "Not covered", "N/A", "Applicable", "Coverage %", "Weighted %"],
        [
            [DOMAIN_LABELS.get(dk, dk), t.get("name"), t.get("covered"), t.get("partial"),
             t.get("not_covered"), t.get("not_applicable"), t.get("applicable"),
             t.get("strict_pct"), t.get("weighted_pct")]
            for dk, d in summary.get("domains", {}).items()
            for t in d.get("tactics", [])
        ],
        [12, 26, 10, 10, 12, 8, 12, 12, 12],
    )

    # ------------------------------------------------------- Technique Register
    rules_by_technique: dict = {}
    mapped_by_technique: dict = {}
    for uc in use_cases:
        for m in uc.get("mappings") or []:
            tid = m.get("technique_id")
            rules_by_technique.setdefault(tid, []).append(uc.get("name", ""))
            mapped_by_technique.setdefault(tid, []).append(
                {"name": uc.get("name"), "enabled": uc.get("enabled"),
                 "source": m.get("source"), "confidence": m.get("confidence")}
            )
    results = assessment.technique_results or []
    state_by_id = {r.get("technique_id"): r.get("state") for r in results}
    total_rules = (summary.get("counts") or {}).get("use_cases", len(use_cases))
    tactic_names = {
        (domain, t["id"]): t["name"]
        for domain in index.domains
        for t in index.tactics(domain)
    }
    confidence_covered = (params.get("thresholds") or {}).get("confidence_covered", 0.7)

    def register_row(r):
        tid = r.get("technique_id")
        mapped = mapped_by_technique.get(tid, [])
        why = plain_language.derive_why(
            r, mapped,
            total_rules=total_rules,
            sub_states=plain_language.sub_states_for(r, mapped, state_by_id, index),
            confidence_covered=confidence_covered,
        )
        return [
            tid,
            (index.get(tid) or {}).get("name", ""),
            DOMAIN_LABELS.get(r.get("domain"), r.get("domain")),
            ", ".join(tactic_names.get((r.get("domain"), t), t) for t in r.get("tactics", [])),
            STATE_LABELS.get(r.get("state"), r.get("state")),
            _STATE_PLAIN_XLSX.get(r.get("state"), ""),
            why,
            len(r.get("use_case_refs", [])),
            "; ".join(rules_by_technique.get(tid, [])),
        ]

    ws_reg = sheet(
        "Technique Register",
        ["Technique", "Name", "Matrix", "Tactics", "State", "In plain words", "Why", "Mapped rules", "Rule names"],
        [register_row(r) for r in results],
        [12, 30, 10, 26, 12, 26, 70, 12, 50],
    )
    for i, r in enumerate(results, start=2):
        color = _XLSX_STATE_FILLS.get(r.get("state"))
        if color:
            ws_reg.cell(row=i, column=5).fill = fill(color)

    # -------------------------------------------------------- Use-Case Mappings
    sorted_ucs = sorted(use_cases, key=_row_ref_sort_key)
    sheet(
        "Use-Case Mappings",
        ["Row", "Rule name", "Enabled", "How it was mapped", "Techniques", "Confidence", "Source", "Log source", "Description", "Logic"],
        [
            [uc.get("row_ref"), uc.get("name"),
             {True: "yes", False: "no"}.get(uc.get("enabled"), "unknown"),
             _MAPPING_STATUS_PLAIN_XLSX.get(uc.get("mapping_status"), uc.get("mapping_status")),
             ", ".join(m.get("technique_id", "") for m in (uc.get("mappings") or [])),
             ", ".join(str(m.get("confidence", "")) for m in (uc.get("mappings") or [])),
             ", ".join(m.get("source", "") for m in (uc.get("mappings") or [])),
             uc.get("log_source") or "", uc.get("description") or "",
             uc.get("logic") or ""]  # Phase 7; query text is attacker-controlled — _guard applies
            for uc in sorted_ucs
        ],
        [10, 42, 9, 30, 22, 12, 12, 16, 60, 60],
    )

    # --------------------------------------------- Gaps grouped by feasibility
    ws_gaps = wb.create_sheet()
    ws_gaps.title = "Gaps & Recommendations"
    gap_headers = ["Rank", "Technique", "Name", "Priority", "State", "Log source to use", "Recommendation"]
    ws_gaps.append(gap_headers)
    for cell in ws_gaps[1]:
        cell.font = bold
    gaps = summary.get("gaps", [])
    row_idx = 1
    for bucket in ("short", "mid", "long"):
        bucket_gaps = [g for g in gaps if g.get("feasibility") == bucket]
        if not bucket_gaps:
            continue
        ws_gaps.append([f"{FEASIBILITY_LABELS[bucket]} — {len(bucket_gaps)} item"
                        f"{'' if len(bucket_gaps) == 1 else 's'}"])
        row_idx += 1
        header_cell = ws_gaps.cell(row=row_idx, column=1)
        header_cell.font = bold
        for col in range(1, len(gap_headers) + 1):
            ws_gaps.cell(row=row_idx, column=col).fill = fill(_XLSX_FEAS_FILLS[bucket])
        for g in bucket_gaps:
            tier = g.get("tier")
            ws_gaps.append([_guard(v) for v in [
                g.get("rank"), g.get("technique_id"), g.get("name"),
                f"P{tier}" if isinstance(tier, int) and tier <= 3 else "Unranked",
                STATE_LABELS.get(g.get("state"), g.get("state")),
                (f"Uses logs you already collect: {g.get('via')}" if bucket == "short"
                 else f"Onboard from tooling you own: {g.get('via')}" if bucket == "mid" and g.get("via")
                 else g.get("via") or "Needs a new log source"),
                gap_recs.get(g.get("technique_id")) or g.get("hint"),
            ]])
            row_idx += 1
            if isinstance(tier, int) and tier in _XLSX_TIER_FILLS:
                ws_gaps.cell(row=row_idx, column=4).fill = fill(_XLSX_TIER_FILLS[tier])
            state_color = _XLSX_STATE_FILLS.get(g.get("state"))
            if state_color:
                ws_gaps.cell(row=row_idx, column=5).fill = fill(state_color)
    for row in ws_gaps.iter_rows(min_row=2):
        for cell in row:
            cell.alignment = wrap
    ws_gaps.freeze_panes = "A2"
    for i, width in enumerate([7, 12, 34, 12, 12, 34, 70], start=1):
        ws_gaps.column_dimensions[get_column_letter(i)].width = width

    # ------------------------------------------------------------------ Roadmap
    sheet(
        "Roadmap",
        ["Bucket", "Technique", "Name", "Action"],
        [
            [FEASIBILITY_LABELS[b], g.get("technique_id"), g.get("name"), g.get("hint")]
            for b in ("short", "mid", "long")
            for g in summary.get("roadmap", {}).get(b, [])
        ],
        [18, 12, 34, 70],
    )

    sheet(
        "Not Applicable",
        ["Technique", "Matrix", "Reason"],
        [
            [n.get("technique_id"), DOMAIN_LABELS.get(n.get("domain"), n.get("domain")), n.get("reason")]
            for n in summary.get("not_applicable", [])
        ],
        [12, 10, 80],
    )

    sheet(
        "Assumptions",
        ["Assumption"],
        [[a] for a in summary.get("assumptions", [])],
        [110],
    )

    buf = io.BytesIO()
    wb.save(buf)
    return buf.getvalue()
