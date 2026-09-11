"""Code Security Review XLSX tracker builder (module reference §5).

Numbers/strings come ONLY from `review.report` (the ingest-normalized
JSONB, module reference §3) — never recomputed, never network/LLM. Every
attacker-controlled string (it originated in the scanned repo, passed
through an LLM) goes through `_guard` before it reaches a cell.
"""

import io

from app.mitre.report_common import resolve_branding

BRAND = "341954"
ACCENT = "00A98B"
ZEBRA = "F3F0F7"
_SEVERITY_FILLS = {
    "critical": ("B02830", "FFFFFF"),
    "high": ("C73E65", "FFFFFF"),
    "medium": ("C8801A", "000000"),
    "low": ("00A98B", "000000"),
    "info": ("BBBDC2", "000000"),
}


def _guard(value):
    """Excel formula-injection guard: a leading =, +, - or @ in an
    attacker-controlled string would execute as a formula when the
    register opens in Excel."""
    if isinstance(value, str) and value[:1] in ("=", "+", "-", "@"):
        return "'" + value
    return value


def build_xlsx_export(review) -> bytes:
    branding = resolve_branding(None)
    from openpyxl import Workbook
    from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
    from openpyxl.utils import get_column_letter

    report = review.report or {}
    counts = report.get("counts") or {}
    findings = report.get("findings") or []
    chains = report.get("chains") or []
    metrics = report.get("metrics") or {}
    manifest = report.get("manifest") or {}

    wb = Workbook()
    bold = Font(bold=True)
    wrap = Alignment(wrap_text=True, vertical="top")
    thin = Side(style="thin", color="B9AECB")
    cell_border = Border(left=thin, right=thin, top=thin, bottom=thin)
    white_bold = Font(bold=True, color="FFFFFF")

    def fill(color):
        return PatternFill(start_color=color, end_color=color, fill_type="solid")

    def sheet(title, headers, rows, widths, first=False, filters=True, borders=True):
        ws = wb.active if first else wb.create_sheet()
        ws.title = title
        ws.append([_guard(h) for h in headers])
        for cell in ws[1]:
            cell.font = white_bold
            cell.fill = fill(BRAND)
            if borders:
                cell.border = cell_border
        for row in rows:
            ws.append([_guard(v) for v in row])
        for row in ws.iter_rows(min_row=2):
            for cell in row:
                cell.alignment = wrap
                if borders:
                    cell.border = cell_border
                if cell.row % 2 == 0:
                    cell.fill = fill(ZEBRA)
        ws.freeze_panes = "A2"
        if filters and rows:
            ws.auto_filter.ref = ws.dimensions
        for i, width in enumerate(widths, start=1):
            ws.column_dimensions[get_column_letter(i)].width = width
        return ws

    # ------------------------------------------------------------- Read Me
    readme_rows = [
        ["This workbook is a code security review findings tracker."],
        [],
        ["What this is",
         "Output of Visa's open-source Vulnerability Agentic Harness "
         "(VVAH, Apache-2.0), imported and formatted by ScopeWise."],
        ["Findings are candidates, not confirmed bugs",
         "Every row is an AI-generated triage candidate. A human must "
         "confirm each finding before acting on it."],
        ["Severity / CVSS / Confidence",
         "Severity is the tool's triage rating (critical/high/medium/low/"
         "info). CVSS score/vector/rating follow the standard scale when "
         "the scanner computed one. Confidence (0-1) and Votes reflect "
         "the harness's internal verification pass."],
        ["Verdict",
         "TRUE_POSITIVE / FALSE_POSITIVE when the harness's verifier "
         "ran; blank when it did not. Still confirm either way."],
        ["Tracker columns",
         "Owner, Status, Target date and Notes are blank — fill them in "
         "as you work the findings; nothing here is pre-populated."],
        [f"Attribution",
         "Findings produced by Visa Vulnerability Agentic Harness "
         "(Apache-2.0). ScopeWise consumes its output only; no VVAH "
         "code is vendored."],
    ]
    sheet("Read Me", ["How to read this workbook", ""], readme_rows,
          [32, 90], first=True, filters=False, borders=False)

    # -------------------------------------------------------------- Summary
    by_sev = counts.get("by_severity") or {}
    by_class = counts.get("by_vuln_class") or {}
    sum_rows = [["Counts by severity", ""]]
    for sev in ("critical", "high", "medium", "low", "info"):
        sum_rows.append([sev.title(), by_sev.get(sev, 0)])
    sum_rows.append([])
    sum_rows.append(["Counts by vulnerability class", ""])
    for label, n in sorted(by_class.items(), key=lambda kv: -kv[1]):
        sum_rows.append([label, n])
    sum_rows.append([])
    sum_rows.append(["Total findings", counts.get("total", len(findings))])
    if report.get("dropped_count"):
        sum_rows.append(["Dropped (over cap)", report.get("dropped_count")])
    if metrics:
        sum_rows.append([])
        sum_rows.append(["Metrics", ""])
        for label, key in (
            ("Scan duration (sec)", "duration_sec"),
            ("Files in scope", "total_files_in_scope"),
            ("Files analyzed", "analyzed_files_unique"),
            ("True positives (verifier)", "true_positive_count"),
            ("False positives (verifier)", "false_positive_count"),
            ("Total tokens", "total_tokens"),
        ):
            if metrics.get(key) is not None:
                sum_rows.append([label, metrics[key]])
    if manifest:
        sum_rows.append([])
        sum_rows.append(["Run manifest", ""])
        if manifest.get("target_git_sha"):
            sum_rows.append(["Git SHA", manifest["target_git_sha"]])
        if manifest.get("duration_sec") is not None:
            sum_rows.append(["Duration (sec)", manifest["duration_sec"]])
        for role, model in (manifest.get("models") or {}).items():
            sum_rows.append([f"Model — {role}", model.get("id")])
        if manifest.get("total_cost_usd") is not None:
            sum_rows.append(["Total cost (USD)", manifest["total_cost_usd"]])
        if manifest.get("total_tokens") is not None:
            sum_rows.append(["Total tokens", manifest["total_tokens"]])
    ws_sum = sheet("Summary", ["Metric", "Value"], sum_rows, [34, 20],
                   filters=False)
    for row in ws_sum.iter_rows(min_row=2, max_col=1):
        if row[0].value in ("Counts by severity", "Counts by vulnerability class",
                             "Metrics", "Run manifest"):
            row[0].font = bold

    # -------------------------------------------------------- Findings Register
    reg_headers = [
        "#", "Severity", "Title", "Class", "CWE", "CVSS", "Rating",
        "Confidence", "Votes", "Verdict", "File", "Lines", "Description",
        "Impact", "Exploit scenario", "Preconditions", "Recommendation",
        "Code snippet", "Source→Sink", "Also at",
        "Owner", "Status", "Target date", "Notes",
    ]
    reg_rows = []
    for f in findings:
        dupes = "; ".join(
            f"{d.get('file')}:{d.get('line_start')}" for d in (f.get("duplicates") or [])
        )
        source_sink = " -> ".join(x for x in (f.get("source_ref"), f.get("sink_ref")) if x)
        lines = f"{f.get('line_start')}-{f.get('line_end')}"
        reg_rows.append([
            f.get("idx"), (f.get("severity") or "").title(), f.get("title"),
            f.get("vuln_class_label") or f.get("vuln_class"), f.get("cwe"),
            f.get("cvss_score"), f.get("cvss_rating"), f.get("confidence"),
            f.get("votes"), f.get("verdict"), f.get("file"), lines,
            f.get("description"), f.get("impact"), f.get("exploit_scenario"),
            "; ".join(f.get("preconditions") or []), f.get("recommendation"),
            f.get("code_snippet"), source_sink, dupes,
            "", "", "", "",
        ])
    ws_reg = sheet("Findings Register", reg_headers, reg_rows, [
        5, 10, 30, 18, 10, 8, 10, 10, 7, 14, 26, 10, 40, 30, 30, 26, 30,
        30, 20, 20, 14, 12, 12, 24,
    ])
    for row in ws_reg.iter_rows(min_row=2):
        sev = str(row[1].value or "").lower()
        colors = _SEVERITY_FILLS.get(sev)
        if colors:
            bg, fg = colors
            row[1].fill = fill(bg)
            row[1].font = Font(bold=True, color=fg)

    # -------------------------------------------------------- Exploit Chains
    chain_rows = []
    for c in chains:
        chain_rows.append([
            c.get("title"), (c.get("severity") or "").title(),
            ", ".join(str(s) for s in (c.get("steps") or [])),
            c.get("narrative"),
        ])
    if not chain_rows:
        chain_rows = [["No exploit chains reported", "", "", ""]]
    sheet("Exploit Chains", ["Title", "Severity", "Steps", "Narrative"],
          chain_rows, [30, 12, 20, 60])

    wb.properties.title = f"{review.name} — Code Security Review"
    wb.properties.creator = branding.get("report_display_name") or "ScopeWise"

    buf = io.BytesIO()
    wb.save(buf)
    return buf.getvalue()
