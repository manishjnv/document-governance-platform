"""Code Security Review PPTX briefing-deck builder (module reference §5).

Same design system as the MITRE deck (app/mitre/report_pptx.py): deep
purple / teal / magenta, card-with-accent-bar, Tenorite font. Numbers come
ONLY from `review.report`; every string is length-trimmed before it lands
on a slide (no LLM call here — the harness's text already passed through
ingest's caps, this is just fit-for-a-slide trimming). Deterministic
output for a given review.
"""

import io

from app.mitre.report_common import resolve_branding

_PURPLE = "341954"
_MAGENTA = "B71D6B"
_TEAL = "00A98B"
_GREY = "404040"
_MUTED = "BBBDC2"
_CARD = "F3F0F7"
_RED_D = "B02830"
_ROSE = "C73E65"
_AMBER = "C8801A"
_FONT = "Tenorite"

_SEVERITY_COLOR = {
    "critical": "B02830", "high": "C73E65", "medium": "C8801A",
    "low": "00A98B", "info": "BBBDC2",
}


def _trim(value, length=300):
    value = "" if value is None else str(value)
    return value if len(value) <= length else value[: length - 1] + "…"


def build_pptx_export(review) -> bytes:
    from pptx import Presentation
    from pptx.chart.data import CategoryChartData
    from pptx.dml.color import RGBColor
    from pptx.enum.chart import XL_CHART_TYPE
    from pptx.enum.shapes import MSO_SHAPE
    from pptx.enum.text import MSO_ANCHOR, PP_ALIGN
    from pptx.util import Inches, Pt

    branding = resolve_branding(None)
    display_name = branding["report_display_name"]
    report = review.report or {}
    counts = report.get("counts") or {}
    findings = report.get("findings") or []
    chains = report.get("chains") or []
    by_sev = counts.get("by_severity") or {}
    by_class = counts.get("by_vuln_class") or {}
    total = counts.get("total", len(findings))
    fp_count = sum(1 for f in findings if f.get("verdict") == "FALSE_POSITIVE")
    files_with_findings = len({f.get("file") for f in findings if f.get("file")})
    git_sha_short = (review.git_sha or "")[:8]
    created = str(review.created_at or "")[:10]

    footer_text = " · ".join(
        bit for bit in (review.name, review.repo_label, git_sha_short,
                         display_name, created) if bit
    )

    def rgb(hexc):
        return RGBColor.from_string(hexc)

    prs = Presentation()
    prs.slide_width = Inches(10.0)
    prs.slide_height = Inches(5.625)
    blank = prs.slide_layouts[6]
    page_no = 0

    def slide():
        return prs.slides.add_slide(blank)

    def rect(s, x, y, w, h, color, shape=MSO_SHAPE.RECTANGLE):
        sh = s.shapes.add_shape(shape, Inches(x), Inches(y), Inches(w), Inches(h))
        sh.fill.solid()
        sh.fill.fore_color.rgb = rgb(color)
        sh.line.fill.background()
        sh.shadow.inherit = False
        return sh

    def _add_run(p, txt, size, bold, color):
        r = p.add_run()
        r.text = txt
        f = r.font
        f.name = _FONT
        f.size = Pt(size)
        f.bold = bold
        f.color.rgb = rgb(color)

    def text(s, x, y, w, h, paras, anchor=MSO_ANCHOR.TOP):
        tb = s.shapes.add_textbox(Inches(x), Inches(y), Inches(w), Inches(h))
        tf = tb.text_frame
        tf.word_wrap = True
        tf.vertical_anchor = anchor
        tf.margin_left = tf.margin_right = tf.margin_top = tf.margin_bottom = 0
        for i, (runs, opts) in enumerate(paras):
            p = tf.paragraphs[0] if i == 0 else tf.add_paragraph()
            p.alignment = opts.get("align", PP_ALIGN.LEFT)
            if opts.get("space_after") is not None:
                p.space_after = Pt(opts["space_after"])
            for txt_, ro in runs:
                _add_run(p, str(txt_), ro.get("size", 9), ro.get("bold", False),
                         ro.get("color", "000000"))
        return tb

    def P(runs, **opts):
        return (runs, opts)

    def R(txt, bold=False, color="000000", size=9):
        return (txt, {"bold": bold, "color": color, "size": size})

    def chrome(s, title, subtitle):
        nonlocal page_no
        page_no += 1
        text(s, 0.45, 0.18, 9.10, 0.55, [P([R(title, bold=True, color=_PURPLE, size=24)])])
        rect(s, 0.47, 0.78, 9.06, 0.03, _TEAL)
        text(s, 0.45, 0.86, 9.10, 0.30, [P([R(subtitle, color=_GREY, size=11.5)])])
        text(s, 0.45, 5.30, 7.50, 0.25, [P([R(footer_text, color=_MUTED, size=7.5)])])
        text(s, 9.25, 5.30, 0.40, 0.25,
             [P([R(str(page_no), color=_MUTED, size=8)], align=PP_ALIGN.RIGHT)])

    def card(s, x, y, w, h, bar=_TEAL, fillc=_CARD):
        rect(s, x, y, w, h, fillc)
        rect(s, x, y, 0.06, h, bar)

    def info_card(s, x, y, w, h, bar, fillc, head, head_color, body_paras):
        card(s, x, y, w, h, bar, fillc)
        text(s, x + 0.16, y + 0.07, w - 0.32, 0.26,
             [P([R(head, bold=True, color=head_color, size=10.5)])])
        text(s, x + 0.16, y + 0.34, w - 0.32, h - 0.42, body_paras)

    def stat_tile(s, x, y, w, h, big, label, color=_PURPLE):
        card(s, x, y, w, h, color)
        text(s, x + 0.16, y + 0.10, w - 0.28, 0.52,
             [P([R(big, bold=True, color=color, size=24)])])
        text(s, x + 0.16, y + 0.62, w - 0.28, h - 0.66,
             [P([R(label, color=_GREY, size=8.5)])])

    def style_table(tbl, widths, header_size=9.5, body_size=9):
        for i, w in enumerate(widths):
            tbl.columns[i].width = Inches(w)
        for ri, row in enumerate(tbl.rows):
            for cell in row.cells:
                cell.margin_left = Inches(0.06)
                cell.margin_right = Inches(0.06)
                cell.margin_top = cell.margin_bottom = Inches(0.02)
                cell.vertical_anchor = MSO_ANCHOR.MIDDLE
                cell.fill.solid()
                cell.fill.fore_color.rgb = rgb(
                    _PURPLE if ri == 0 else (_CARD if ri % 2 else "FFFFFF"))
                for p in cell.text_frame.paragraphs:
                    for r in p.runs:
                        r.font.name = _FONT
                        r.font.size = Pt(header_size if ri == 0 else body_size)
                        if ri == 0:
                            r.font.bold = True
                            r.font.color.rgb = rgb("FFFFFF")

    # ---------------------------------------------------------------- 1 · cover
    s = slide()
    rect(s, 0, 0, 10.0, 5.625, _PURPLE)
    rect(s, -1.60, 1.40, 6.00, 6.00, "46246B", MSO_SHAPE.OVAL)
    rect(s, 2.60, -2.60, 5.20, 5.20, _MAGENTA, MSO_SHAPE.OVAL)
    rect(s, 0.75, 3.15, 3.20, 0.03, _TEAL)
    text(s, 4.45, 1.05, 5.20, 1.90, [
        P([R("Code Security", bold=True, color="FFFFFF", size=36)]),
        P([R("Review", bold=True, color="FFFFFF", size=36)]),
        P([R("Findings triage · Exploit chains · Next steps", bold=True, color=_TEAL, size=15)]),
    ])
    meta = [P([R(_trim(review.name, 60), bold=True, color="FFFFFF", size=13.5)])]
    if review.repo_label:
        meta.append(P([R(_trim(review.repo_label, 60), color=_MUTED, size=11)]))
    if git_sha_short:
        meta.append(P([R(f"Commit {git_sha_short}", color=_MUTED, size=11)]))
    if created:
        meta.append(P([R(created, color=_MUTED, size=11)]))
    text(s, 4.45, 3.10, 5.20, 1.90, meta)
    text(s, 0.75, 3.35, 3.40, 1.40, [
        P([R("CONFIDENTIAL", bold=True, color=_TEAL, size=13)], space_after=5),
        P([R("AI-generated triage candidates. Human review required "
             "before action.", color="D8D2E4", size=9.5)]),
    ])

    # ----------------------------------------------------------- 2 · how to read
    s = slide()
    chrome(s, "How to Read This Deck",
           "What the numbers mean, what a finding is, and what to do next")
    info_card(s, 0.45, 1.25, 2.95, 3.55, _TEAL, _CARD,
              "What the numbers mean", _PURPLE,
              [P([R("Counts below are severity/class tallies straight from "
                    "the scan report — nothing is re-estimated.", size=9)])])
    info_card(s, 3.55, 1.25, 2.95, 3.55, _MAGENTA, "FCEEF3",
              "What a finding is", _RED_D,
              [P([R("One suspected vulnerability the harness's agents "
                    "found and, where possible, verified with a "
                    "confidence score and vote count.", size=9)])])
    info_card(s, 6.65, 1.25, 2.90, 3.55, _PURPLE, _CARD,
              "What to do next", _PURPLE,
              [P([R("Confirm each finding, fix criticals/highs first, "
                    "dismiss false positives explicitly, then re-scan.",
                    size=9)])])

    # -------------------------------------------------------- 3 · headline tiles
    s = slide()
    chrome(s, f"{total} Findings", "Headline counts for this review")
    tiles = [
        (str(total), "total findings", _PURPLE),
        (str(by_sev.get("critical", 0)), "critical", _RED_D),
        (str(by_sev.get("high", 0)), "high", _ROSE),
        (str(len(chains)), "exploit chains", _MAGENTA),
        (str(fp_count), "verified false positives", _TEAL),
        (str(files_with_findings), "files with findings", _AMBER),
    ]
    for i, (big, label, color) in enumerate(tiles):
        x = 0.45 + (i % 3) * 3.05
        y = 1.30 + (i // 3) * 1.55
        stat_tile(s, x, y, 2.85, 1.35, big, label, color)

    # ------------------------------------------------------ 4 · severity/class charts
    s = slide()
    chrome(s, "Findings by Severity and Class", "Counts from the scan report")
    sev_data = CategoryChartData()
    sev_order = ["critical", "high", "medium", "low", "info"]
    sev_data.categories = [x.title() for x in sev_order]
    sev_data.add_series("Findings", [by_sev.get(k, 0) for k in sev_order])
    s.shapes.add_chart(XL_CHART_TYPE.COLUMN_CLUSTERED, Inches(0.45), Inches(1.25),
                        Inches(4.45), Inches(3.60), sev_data)
    class_items = sorted(by_class.items(), key=lambda kv: -kv[1])[:8]
    if class_items:
        class_data = CategoryChartData()
        class_data.categories = [_trim(k, 22) for k, _ in class_items]
        class_data.add_series("Findings", [v for _, v in class_items])
        s.shapes.add_chart(XL_CHART_TYPE.BAR_CLUSTERED, Inches(5.10), Inches(1.25),
                            Inches(4.45), Inches(3.60), class_data)

    # --------------------------------------------------------- 5 · top findings
    s = slide()
    chrome(s, "Top Findings", "Up to 10, sorted by severity then CVSS")
    top = findings[:10]
    rows = 1 + max(len(top), 1)
    tbl_shape = s.shapes.add_table(rows, 5, Inches(0.45), Inches(1.25),
                                    Inches(9.10), Inches(3.70))
    tbl = tbl_shape.table
    for ci, h in enumerate(("#", "Severity", "Title", "File:Line", "CVSS")):
        tbl.cell(0, ci).text = h
    if top:
        for ri, f in enumerate(top, start=1):
            tbl.cell(ri, 0).text = str(f.get("idx", ri))
            tbl.cell(ri, 1).text = (f.get("severity") or "").title()
            tbl.cell(ri, 2).text = _trim(f.get("title"), 60)
            tbl.cell(ri, 3).text = f"{_trim(f.get('file'), 40)}:{f.get('line_start')}"
            tbl.cell(ri, 4).text = "" if f.get("cvss_score") is None else str(f.get("cvss_score"))
    else:
        tbl.cell(1, 0).text = "No findings reported."
    style_table(tbl, [0.5, 1.1, 3.6, 3.1, 0.8])

    # ------------------------------------------------------ 6 · exploit chains
    if chains:
        s = slide()
        chrome(s, "Exploit Chains", "Multi-finding attack paths reported by the harness")
        for i, c in enumerate(chains[:4]):
            y = 1.25 + i * 0.95
            card(s, 0.45, y, 9.10, 0.85, _MAGENTA)
            steps = ", ".join(str(x) for x in (c.get("steps") or []))
            text(s, 0.61, y + 0.08, 8.80, 0.28,
                 [P([R(_trim(c.get("title"), 70), bold=True, color=_PURPLE, size=11),
                     R(f"  ({(c.get('severity') or '').title()})", color=_GREY, size=9)])])
            text(s, 0.61, y + 0.38, 8.80, 0.42,
                 [P([R(f"Steps: {steps}  ", bold=True, color=_GREY, size=8.5),
                     R(_trim(c.get("narrative"), 140), color=_GREY, size=8.5)])])

    # ------------------------------------------------------- 7 · next steps
    s = slide()
    chrome(s, "Recommended Next Steps", "Deterministic priority order")
    criticals = [f for f in findings if f.get("severity") == "critical"]
    highs = [f for f in findings if f.get("severity") == "high"]
    by_file = {}
    for f in highs:
        by_file.setdefault(f.get("file") or "(unknown)", []).append(f)
    steps = []
    if criticals:
        nums = ", ".join(f"#{f.get('idx')}" for f in criticals)
        steps.append(f"Fix the {len(criticals)} critical finding(s) first: {nums}.")
    if by_file:
        parts = ", ".join(f"{path} ({len(fs)})" for path, fs in
                           sorted(by_file.items(), key=lambda kv: -len(kv[1])))
        steps.append(f"Then address {len(highs)} high-severity finding(s), grouped by "
                      f"file: {parts}.")
    if fp_count:
        steps.append(f"Confirm or dismiss the {fp_count} finding(s) the verifier "
                      "marked as false positive.")
    steps.append("Re-scan the repository after fixes to confirm the findings clear.")
    paras = [P([R(f"{i+1}.  ", bold=True, color=_TEAL, size=11),
                R(_trim(step, 220), color=_GREY, size=11)], space_after=10)
             for i, step in enumerate(steps)]
    text(s, 0.45, 1.35, 9.10, 3.60, paras)

    # ------------------------------------------------------------- 8 · closing
    s = slide()
    rect(s, 0, 0, 10.0, 5.625, _PURPLE)
    rect(s, 7.10, -1.20, 5.50, 5.50, "46246B", MSO_SHAPE.OVAL)
    text(s, 0.90, 1.60, 8.20, 0.60,
         [P([R("Findings produced by Visa Vulnerability Agentic Harness "
               "(Apache-2.0).", bold=True, color="FFFFFF", size=16)])])
    text(s, 0.90, 2.40, 8.20, 1.40, [
        P([R("Findings are AI-generated triage candidates, not confirmed "
             "vulnerabilities; human review is required before action.",
             color="D8D2E4", size=12)]),
    ])
    text(s, 0.90, 4.60, 8.20, 0.45,
         [P([R(footer_text, color=_MUTED, size=9)])])

    buf = io.BytesIO()
    prs.save(buf)
    return buf.getvalue()
