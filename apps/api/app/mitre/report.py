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


def build_xlsx_export(assessment, use_cases: list) -> bytes:
    """The detailed gap register as an 8-sheet workbook. Working document
    styling only: bold headers, frozen top row, sane widths."""
    from openpyxl import Workbook
    from openpyxl.styles import Font
    from openpyxl.utils import get_column_letter

    summary = assessment.summary or {}
    params = assessment.params or {}
    overall = summary.get("overall", {})
    narrative = summary.get("narrative", {})
    gap_recs = narrative.get("gap_recommendations", {})

    wb = Workbook()
    bold = Font(bold=True)

    def sheet(title, headers, rows, widths, first=False):
        ws = wb.active if first else wb.create_sheet()
        ws.title = title
        ws.append([_guard(h) for h in headers])
        for cell in ws[1]:
            cell.font = bold
        for row in rows:
            ws.append([_guard(v) for v in row])
        ws.freeze_panes = "A2"
        for i, width in enumerate(widths, start=1):
            ws.column_dimensions[get_column_letter(i)].width = width
        return ws

    thresholds = params.get("thresholds", {})
    sheet(
        "Summary",
        ["Metric", "Value"],
        [
            ["Assessment", assessment.name],
            ["ATT&CK version", assessment.attack_version],
            ["Completed", str(assessment.completed_at or "")],
            ["Strict coverage %", overall.get("strict_pct")],
            ["Weighted coverage %", overall.get("weighted_pct")],
            ["Covered", overall.get("covered")],
            ["Partial", overall.get("partial")],
            ["Not covered", overall.get("not_covered")],
            ["Not applicable", overall.get("not_applicable")],
            ["Applicable techniques", overall.get("applicable")],
            ["Narrative", narrative.get("generated_by", "")],
            ["Thresholds", str(thresholds)],
        ]
        + [
            [f"{DOMAIN_LABELS.get(k, k)} strict %", d.get("strict_pct")]
            for k, d in summary.get("domains", {}).items()
        ],
        [28, 60],
        first=True,
    )

    sheet(
        "Coverage by Tactic",
        ["Matrix", "Tactic", "Covered", "Partial", "Not covered", "N/A", "Applicable", "Strict %", "Weighted %"],
        [
            [DOMAIN_LABELS.get(dk, dk), t.get("name"), t.get("covered"), t.get("partial"),
             t.get("not_covered"), t.get("not_applicable"), t.get("applicable"),
             t.get("strict_pct"), t.get("weighted_pct")]
            for dk, d in summary.get("domains", {}).items()
            for t in d.get("tactics", [])
        ],
        [12, 26, 10, 10, 12, 8, 12, 10, 12],
    )

    rules_by_technique: dict = {}
    for uc in use_cases:
        for m in uc.get("mappings") or []:
            rules_by_technique.setdefault(m.get("technique_id"), []).append(uc.get("name", ""))
    sheet(
        "Technique Register",
        ["Technique", "Matrix", "Tactics", "State", "N/A reason", "Mapped rules", "Rule names"],
        [
            [r.get("technique_id"), DOMAIN_LABELS.get(r.get("domain"), r.get("domain")),
             ", ".join(r.get("tactics", [])), STATE_LABELS.get(r.get("state"), r.get("state")),
             r.get("na_reason") or "", len(r.get("use_case_refs", [])),
             "; ".join(rules_by_technique.get(r.get("technique_id"), []))]
            for r in (assessment.technique_results or [])
        ],
        [12, 10, 22, 12, 50, 12, 60],
    )

    sheet(
        "Use-Case Mappings",
        ["Row", "Rule name", "Enabled", "Mapping status", "Techniques", "Confidence", "Source", "Log source", "Description"],
        [
            [uc.get("row_ref"), uc.get("name"),
             {True: "yes", False: "no"}.get(uc.get("enabled"), "unknown"),
             uc.get("mapping_status"),
             ", ".join(m.get("technique_id", "") for m in (uc.get("mappings") or [])),
             ", ".join(str(m.get("confidence", "")) for m in (uc.get("mappings") or [])),
             ", ".join(m.get("source", "") for m in (uc.get("mappings") or [])),
             uc.get("log_source") or "", uc.get("description") or ""]
            for uc in use_cases
        ],
        [10, 42, 9, 16, 22, 12, 12, 16, 60],
    )

    sheet(
        "Gaps & Recommendations",
        ["Rank", "Technique", "Name", "Priority tier", "State", "Feasibility", "Via", "Recommendation"],
        [
            [g.get("rank"), g.get("technique_id"), g.get("name"),
             g.get("tier"), STATE_LABELS.get(g.get("state"), g.get("state")),
             FEASIBILITY_LABELS.get(g.get("feasibility"), g.get("feasibility")), g.get("via") or "",
             gap_recs.get(g.get("technique_id")) or g.get("hint")]
            for g in summary.get("gaps", [])
        ],
        [7, 12, 34, 12, 12, 18, 22, 70],
    )

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
