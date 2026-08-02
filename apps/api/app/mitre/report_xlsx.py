"""MITRE assessment XLSX gap-register builder (split out of report.py in
Phase 14h so the PDF/HTML builder and the spreadsheet builder are
independently editable; router.py still calls it via
``app.mitre.report.build_xlsx_export`` — report.py re-exports this module's
public names unchanged).

Computed numbers come ONLY from the stored summary/technique_results JSONB —
never recomputed here. Every customer/LLM string goes through `_guard` (Excel
formula-injection guard): rule names, descriptions, exclusion reasons, and
narrative output are all attacker-controlled.
"""

import io

from app.mitre.report_common import (
    DOMAIN_LABELS,
    FEASIBILITY_LABELS,
    STATE_LABELS,
    _MAPPING_STATUS_PLAIN_XLSX,
    _ordered_domains,
    _row_ref_sort_key,
    resolve_branding,
)


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


def build_xlsx_export(assessment, use_cases: list, scope: str = "full",
                       branding: dict | None = None) -> bytes:
    """The detailed gap register as a 9-sheet workbook (Phase 14c polish):
    'Read Me' guide sheet first, colored state/priority/feasibility cells,
    frozen headers + auto-filter + wrapped text everywhere, technique names
    + plain-words 'Why' column, numerically sorted rule rows. Computed
    numbers are untouched — styling and wording only.

    branding: optional org overrides (display name/accent/watermark — plan
    §14h). Resolved here for a consistent shape across callers; workbook
    core properties (title/author/company) start consuming it in the
    XLSX-polish follow-up.
    """
    branding = resolve_branding(branding)
    from openpyxl import Workbook
    from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
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
    italic = Font(italic=True)
    wrap = Alignment(wrap_text=True, vertical="top")
    wrap_center = Alignment(wrap_text=True, vertical="top", horizontal="center")
    # Clearly visible grid (the earlier pale blue read as "no border" in Excel)
    thin = Side(style="thin", color="8496AD")
    cell_border = Border(left=thin, right=thin, top=thin, bottom=thin)

    def fill(color):
        return PatternFill(start_color=color, end_color=color, fill_type="solid")

    def sheet(title, headers, rows, widths, first=False, filters=True,
              borders=True, center_cols=()):
        ws = wb.active if first else wb.create_sheet()
        ws.title = title
        ws.append([_guard(h) for h in headers])
        for cell in ws[1]:
            cell.font = bold
            if borders:
                cell.border = cell_border
            if cell.column in center_cols:
                cell.alignment = wrap_center
        for row in rows:
            ws.append([_guard(v) for v in row])
        for row in ws.iter_rows(min_row=2):
            for cell in row:
                cell.alignment = wrap_center if cell.column in center_cols else wrap
                if borders:
                    cell.border = cell_border
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
                      readme_rows, [46, 100], first=True, filters=False,
                      borders=False)  # prose sheet — a full grid would be noise
    for label, color in (("Covered", "covered"), ("Partial", "partial"),
                         ("Not covered", "not_covered"), ("N/A", "not_applicable")):
        for row in ws_readme.iter_rows(min_row=2, max_col=1):
            if row[0].value == label:
                row[0].fill = fill(_XLSX_STATE_FILLS[color])
    for row in ws_readme.iter_rows(min_row=2, max_col=1):
        if row[0].value in ("The three key numbers", "What each sheet contains", "Color legend"):
            row[0].font = bold

    # ------------------------- Summary (redesigned post-14: sectioned, ----
    # ------------------------- colored, with an executive summary) --------
    from openpyxl.styles import Font as _Font

    BRAND = "0057B8"
    white_bold = _Font(bold=True, color="FFFFFF")
    title_font = _Font(bold=True, size=14, color="FFFFFF")

    def _pct_fill_color(pct):
        value = float(pct or 0)
        if value >= 50:
            return _XLSX_STATE_FILLS["covered"]
        if value >= 15:
            return _XLSX_STATE_FILLS["partial"]
        return _XLSX_STATE_FILLS["not_covered"]

    ws_sum = wb.create_sheet()
    ws_sum.title = "Summary"
    for i, w in enumerate((28, 46, 78), start=1):
        ws_sum.column_dimensions[get_column_letter(i)].width = w

    def sum_row(values, *, fills=None, fonts=None, merge=False, height=None,
                center=()):
        ws_sum.append([_guard(v) for v in values])
        r = ws_sum.max_row
        if merge:
            ws_sum.merge_cells(start_row=r, start_column=1, end_row=r, end_column=3)
        for c in range(1, 4):
            cell = ws_sum.cell(row=r, column=c)
            cell.alignment = wrap_center if c in center else wrap
            cell.border = cell_border  # all-borders, merged content included
            if fills and fills.get(c):
                cell.fill = fill(fills[c])
            if fonts and fonts.get(c):
                cell.font = fonts[c]
        if height:
            ws_sum.row_dimensions[r].height = height
        return r

    def section(title):
        sum_row([""])
        sum_row([title, "", ""], merge=True,
                fills={1: BRAND, 2: BRAND, 3: BRAND}, fonts={1: white_bold})

    intake = params.get("intake") or {}
    sum_row(["MITRE ATT&CK Coverage Assessment", "", ""], merge=True,
            fills={1: BRAND, 2: BRAND, 3: BRAND}, fonts={1: title_font}, height=26)
    subtitle = assessment.name
    if intake.get("project_name"):
        subtitle = f"{intake['project_name']} — {assessment.name}"
    sum_row([subtitle, "", ""], merge=True, fonts={1: bold})
    sum_row([f"ATT&CK v{assessment.attack_version} · run completed "
             f"{str(assessment.completed_at or '')[:16]}", "", ""], merge=True)

    # Simple compact pointers instead of a paragraph — deterministic, built
    # from the computed numbers (the fuller narrative stays in the PDF).
    section("EXECUTIVE SUMMARY")
    top_gap_names = ", ".join(
        f"{g.get('technique_id')} {g.get('name')}" for g in summary.get("gaps", [])[:3]
    )
    roadmap_counts = {b: len(summary.get("roadmap", {}).get(b, [])) for b in ("short", "mid", "long")}
    pointers = [
        (f"• Your rules detect {overall.get('covered')} of "
         f"{overall.get('applicable')} applicable attacker techniques — "
         f"{overall.get('strict_pct')}% coverage ({overall.get('weighted_pct')}% weighted).",
         bold),
        (f"• {overall.get('not_covered')} techniques have no detection today; "
         f"{overall.get('partial')} are only partially covered.", None),
    ]
    if top_gap_names:
        pointers.append((f"• Start here: {top_gap_names}.", bold))
    pointers.append(
        (f"• Roadmap: {roadmap_counts['short']} gaps buildable now with logs you "
         f"already collect · {roadmap_counts['mid']} need log onboarding first · "
         f"{roadmap_counts['long']} need a new capability.", None))
    pointers.append(
        (f"• Is {overall.get('strict_pct')}% bad? Probably not: early SIEM "
         "programs typically start under 10% — the roadmap matters more than "
         "the grade.", italic))
    for text, font in pointers:
        sum_row([text, "", ""], merge=True, height=26,
                fonts={1: font} if font else None)

    section("KEY NUMBERS")
    sum_row(["Metric", "Value", "What it means"],
            fonts={1: bold, 2: bold, 3: bold}, center=(2,))
    r = sum_row(["Coverage %", overall.get("strict_pct"),
                 "Of the techniques that apply to your environment, the share "
                 "with at least one qualifying detection rule."], center=(2,))
    ws_sum.cell(row=r, column=2).fill = fill(_pct_fill_color(overall.get("strict_pct")))
    ws_sum.cell(row=r, column=1).font = bold
    ws_sum.cell(row=r, column=2).font = bold
    r = sum_row(["Weighted coverage %", overall.get("weighted_pct"),
                 "Same, but half-covered techniques count as 0.5 instead of 0."],
                center=(2,))
    ws_sum.cell(row=r, column=2).font = bold
    for label, key, meaning in (
        ("Covered", "covered", "Techniques at least one enabled rule detects."),
        ("Partial", "partial", "Techniques reached only by a disabled rule, a "
         "low-confidence mapping, or a covered sub-technique."),
        ("Not covered", "not_covered", "Techniques no rule detects — the gaps."),
        ("Not applicable", "not_applicable", "Techniques excluded from the score "
         "(wrong platform, excluded by you, or deprecated)."),
    ):
        r = sum_row([label, overall.get(key), meaning], center=(2,))
        ws_sum.cell(row=r, column=2).fill = fill(_XLSX_STATE_FILLS[key])
        ws_sum.cell(row=r, column=2).font = bold
    sum_row(["Applicable techniques", overall.get("applicable"),
             "The denominator: techniques that apply to your environment."],
            center=(2,))
    for k, d in _ordered_domains(summary.get("domains")):
        r = sum_row([f"{DOMAIN_LABELS.get(k, k)} coverage %", d.get("strict_pct"),
                     f"Coverage within the {DOMAIN_LABELS.get(k, k)} matrix only."],
                    center=(2,))
        if d.get("applicable"):
            ws_sum.cell(row=r, column=2).fill = fill(_pct_fill_color(d.get("strict_pct")))

    top_gaps = summary.get("gaps", [])[:5]
    if top_gaps:
        section("TOP 5 THINGS TO FIX FIRST")
        sum_row(["Gap", "Effort", "Recommendation"],
                fonts={1: bold, 2: bold, 3: bold}, center=(2,))
        for g in top_gaps:
            r = sum_row([
                f"#{g.get('rank')} {g.get('technique_id')} {g.get('name')}",
                FEASIBILITY_LABELS.get(g.get("feasibility"), ""),
                gap_recs.get(g.get("technique_id")) or g.get("hint") or "",
            ], fonts={1: bold}, center=(2,))
            bucket_color = _XLSX_FEAS_FILLS.get(g.get("feasibility"))
            if bucket_color:
                ws_sum.cell(row=r, column=2).fill = fill(bucket_color)

    section("ABOUT THIS ASSESSMENT")
    sum_row(["Assessment", assessment.name, "The name this run was saved under."])
    for key, label, meaning in (
        ("project_name", "Organization / project", "Who this assessment is for."),
        ("scope_label", "Scope", "The department or scope this run covers."),
        ("prepared_by", "Prepared by", "Who prepared this assessment."),
        ("purpose_note", "Purpose", "Why this assessment was run."),
    ):
        if intake.get(key):
            sum_row([label, intake[key], meaning])
    sum_row(["ATT&CK version", assessment.attack_version,
             "The MITRE ATT&CK release the assessment is pinned to."])
    sum_row(["Narrative", narrative.get("generated_by", ""),
             "Whether recommendation wording was AI-written or standard template "
             "text (numbers are computed either way)."])
    sum_row(["Thresholds", str(params.get("thresholds", {})),
             "The confidence cut-offs used to count a mapping as coverage."])
    ws_sum.freeze_panes = "A2"

    # ------------------------------------------------------ Coverage by Tactic
    sheet(
        "Coverage by Tactic",
        ["Matrix", "Tactic", "Covered", "Partial", "Not covered", "N/A", "Applicable", "Coverage %", "Weighted %"],
        [
            [DOMAIN_LABELS.get(dk, dk), t.get("name"), t.get("covered"), t.get("partial"),
             t.get("not_covered"), t.get("not_applicable"), t.get("applicable"),
             t.get("strict_pct"), t.get("weighted_pct")]
            for dk, d in _ordered_domains(summary.get("domains"))
            for t in d.get("tactics", [])
        ],
        [12, 26, 10, 10, 12, 8, 12, 12, 12],
        center_cols=(3, 4, 5, 6, 7, 8, 9),
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
        center_cols=(3, 5, 8),
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
        center_cols=(3, 6),
    )

    # --------------------------------------------- Gaps grouped by feasibility
    ws_gaps = wb.create_sheet()
    ws_gaps.title = "Gaps & Recommendations"
    gap_headers = ["Rank", "Technique", "Name", "Priority", "State", "Log source to use", "Recommendation"]
    ws_gaps.append(gap_headers)
    for cell in ws_gaps[1]:
        cell.font = bold
        cell.border = cell_border
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
            cell.alignment = wrap_center if cell.column in (1, 4, 5) else wrap
            cell.border = cell_border
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
        center_cols=(2,),
    )

    sheet(
        "Assumptions",
        ["Assumption"],
        [[a] for a in summary.get("assumptions", [])],
        [110],
    )

    # Phase 14g: per-entry environment evidence trail (present for
    # assessments created after the parser gained interpretations).
    interpretations = (params.get("environment_lists") or {}).get("interpretations") or []
    if interpretations:
        sheet(
            "How We Read Your Files",
            ["Your entry", "Sheet", "How it was read"],
            [
                [i.get("entry"), i.get("sheet"), i.get("interpretation")]
                for i in interpretations
            ],
            [40, 18, 80],
        )

    # Per-tab download: keep only that tab's sheets (built once, then pruned
    # — cheapest way to guarantee identical content and styling).
    _SCOPE_SHEETS = {
        "coverage": {"Coverage by Tactic", "Technique Register"},
        "gaps": {"Gaps & Recommendations", "Roadmap"},
        "assumptions": {"Not Applicable", "Assumptions", "How We Read Your Files"},
    }
    if scope in _SCOPE_SHEETS:
        for name in list(wb.sheetnames):
            if name not in _SCOPE_SHEETS[scope]:
                del wb[name]

    buf = io.BytesIO()
    wb.save(buf)
    return buf.getvalue()
