"""Code Security Review PPTX briefing-deck builder (module reference §5).

Design system shared with the MITRE deck (app/mitre/report_pptx.py): deep
purple / teal / magenta, card-with-accent-bar layout, Tenorite font, native
charts with per-point colours, keyword runs. 2026-09-12 rebuild (user
feedback: "professional, in a flow, compact, larger font, effective use of
space, data rich"): every slide carries numbers from the report, prose is
split into short bullets with code / attack / fix terms highlighted, and the
deck derives a remediation order (fewest fixes that break every exploit
chain) deterministically.

Numbers come ONLY from `review.report`; the only LLM text reused is the
scanner's own finding prose, trimmed to fit. No LLM call here.
"""

import io
import re

from app.codereview.report_xlsx import (
    FIX_STATUS_LABELS, FIX_TESTS_LABELS, _CODE_RE, _FIX_RE, _RISK_RE, _sentences,
)
from app.mitre.report_common import resolve_branding

_PURPLE = "341954"
_PURPLE2 = "46246B"
_PURPLE_NUM = "4A2A73"
_LAVENDER = "7370A7"
_MAGENTA = "B71D6B"
_ROSE = "C73E65"
_TEAL = "00A98B"
_GREEN_D = "1E7B4D"
_RED_D = "B02830"
_AMBER = "C8801A"
_BLUE = "1D4ED8"
_CARD = "F3F0F7"
_MINT = "E7F5F1"
_ROSEBG = "FCEEF3"
_AMBERBG = "FEF3C7"
_GREY = "404040"
_MUTED = "BBBDC2"
_LILAC = "D8D2E4"
_FONT = "Tenorite"

_SEV = {  # (solid, tint bg, tint text)
    "critical": ("B02830", "FFE4E6", "9F1239"),
    "high": ("C73E65", "FFEDD5", "9A3412"),
    "medium": ("C8801A", "FEF3C7", "92400E"),
    "low": ("00A98B", "D1FAE5", "065F46"),
    "info": ("7370A7", "E0F2FE", "075985"),
}
_SEV_ORDER = ["critical", "high", "medium", "low", "info"]
_NUM_RE = re.compile(r"(?<![A-Za-z0-9])\d[\d,\.]*\s?%|(?<![A-Za-z0-9.#])\d[\d,]*")
_ABBREV = re.compile(r"^(e\.g|i\.e|etc|vs|cf)$", re.I)


def _trim(value, length=300):
    value = "" if value is None else str(value)
    if len(value) <= length:
        return value
    cut = value[: length - 1]
    if " " in cut[length // 2:]:
        cut = cut[: cut.rfind(" ")]
    return cut.rstrip(",;:") + "…"


def _first_sentences(text, n=2, cap=260):
    return _trim(" ".join(_sentences(text or "")[:n]), cap)


def _fix_first_set(chains, findings):
    """Greedy set cover: the fewest findings whose fixes break every chain.
    Deterministic (ties → lowest idx). Returns [(idx, chains_broken)]."""
    remaining = [set(c.get("steps") or []) for c in chains if c.get("steps")]
    valid = {f.get("idx") for f in findings}
    chosen = []
    while remaining:
        best, best_hits = None, 0
        for idx in sorted(valid):
            hits = sum(1 for s in remaining if idx in s)
            if hits > best_hits:
                best, best_hits = idx, hits
        if best is None:
            break
        chosen.append((best, best_hits))
        remaining = [s for s in remaining if best not in s]
    return chosen


def build_pptx_export(review) -> bytes:
    from pptx import Presentation
    from pptx.chart.data import CategoryChartData
    from pptx.dml.color import RGBColor
    from pptx.enum.chart import XL_CHART_TYPE, XL_LABEL_POSITION
    from pptx.enum.shapes import MSO_SHAPE
    from pptx.enum.text import MSO_ANCHOR, PP_ALIGN
    from pptx.util import Inches, Pt

    branding = resolve_branding(None)
    display_name = branding["report_display_name"]
    report = review.report or {}
    counts = report.get("counts") or {}
    findings = report.get("findings") or []
    chains = report.get("chains") or []
    metrics = report.get("metrics") or {}
    manifest = report.get("manifest") or {}
    by_sev = counts.get("by_severity") or {}
    by_class = counts.get("by_vuln_class") or {}
    by_file = counts.get("by_file") or {}
    total = counts.get("total", len(findings))
    n_crit = by_sev.get("critical", 0)
    n_high = by_sev.get("high", 0)
    confirmed = sum(1 for f in findings if f.get("verdict") == "TRUE_POSITIVE")
    fp_count = sum(1 for f in findings if f.get("verdict") == "FALSE_POSITIVE")
    files_hit = len({f.get("file") for f in findings if f.get("file")})
    title_by_idx = {f.get("idx"): f for f in findings}
    run_extras = report.get("run_extras") or None
    git_sha_short = (review.git_sha or "")[:8]
    created = str(review.created_at or "")[:10]
    tool_version = (manifest.get("tool_version") or report.get("tool_version") or "")
    fix_first = _fix_first_set(chains, findings)
    chain_members = {}
    for c in chains:
        for s_ in c.get("steps") or []:
            chain_members[s_] = chain_members.get(s_, 0) + 1

    footer_text = " · ".join(
        bit for bit in (review.name, review.repo_label, git_sha_short, display_name, created) if bit
    )

    def rgb(hexc):
        return RGBColor.from_string(hexc)

    prs = Presentation()
    prs.slide_width = Inches(10.0)
    prs.slide_height = Inches(5.625)
    blank = prs.slide_layouts[6]
    page_no = 0

    # ------------------------------------------------------------ primitives
    def slide():
        return prs.slides.add_slide(blank)

    def rect(s, x, y, w, h, color, shape=MSO_SHAPE.RECTANGLE, line=None):
        sh = s.shapes.add_shape(shape, Inches(x), Inches(y), Inches(w), Inches(h))
        sh.fill.solid()
        sh.fill.fore_color.rgb = rgb(color)
        if line:
            sh.line.color.rgb = rgb(line)
            sh.line.width = Pt(0.75)
        else:
            sh.line.fill.background()
        sh.shadow.inherit = False
        return sh

    def _add_run(p, txt, size, bold, color, mono=False):
        r = p.add_run()
        r.text = txt
        f = r.font
        f.name = "Consolas" if mono else _FONT
        f.size = Pt(size)
        f.bold = bold
        f.color.rgb = rgb(color)

    def text(s, x, y, w, h, paras, anchor=MSO_ANCHOR.TOP, autofit=False):
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
            if opts.get("line_spacing"):
                p.line_spacing = opts["line_spacing"]
            for txt, ro in runs:
                txt = str(txt)
                size, bold, color = ro.get("size", 10), ro.get("bold", False), ro.get("color", _GREY)
                if ro.get("mono"):
                    _add_run(p, txt, size, bold, color, mono=True)
                    continue
                if bold or color not in (_GREY, "000000") or not ro.get("autonum", True):
                    _add_run(p, txt, size, bold, color)
                    continue
                cursor = 0  # auto-highlight numbers in plain runs (MITRE deck convention)
                for m in _NUM_RE.finditer(txt):
                    if m.start() > cursor:
                        _add_run(p, txt[cursor:m.start()], size, False, color)
                    _add_run(p, m.group(0), size, True, _PURPLE)
                    cursor = m.end()
                if cursor < len(txt) or not txt:
                    _add_run(p, txt[cursor:], size, False, color)
        return tb

    def P(runs, **opts):
        return (runs, opts)

    def R(txt, bold=False, color=_GREY, size=10, **kw):
        d = {"bold": bold, "color": color, "size": size}
        d.update(kw)
        return (txt, d)

    def K(txt, size=10, color=_GREEN_D):
        return R(txt, bold=True, color=color, size=size)

    def rich_runs(sentence, size=10, fix=False, color=_GREY):
        """Runs for one sentence: code tokens mono-blue, attack words rose
        bold (or fix words green bold when `fix`)."""
        word_re = _FIX_RE if fix else _RISK_RE
        hot = _GREEN_D if fix else _RED_D
        runs = []

        def words(chunk):
            pos = 0
            for m in word_re.finditer(chunk):
                if m.start() > pos:
                    runs.append(R(chunk[pos:m.start()], color=color, size=size, autonum=False))
                runs.append(R(m.group(0), bold=True, color=hot, size=size))
                pos = m.end()
            if pos < len(chunk):
                runs.append(R(chunk[pos:], color=color, size=size, autonum=False))

        pos = 0
        for m in _CODE_RE.finditer(sentence):
            if m.start() > pos:
                words(sentence[pos:m.start()])
            tok = m.group(0)
            if _ABBREV.match(tok):
                words(tok)
            else:
                runs.append(R(tok.strip("`"), color=_BLUE, size=size - 0.5, mono=True))
            pos = m.end()
        if pos < len(sentence):
            words(sentence[pos:])
        return runs

    def bullets(textv, size=10, fix=False, n=3, cap=170, gap=3):
        paras = []
        for sent in _sentences(textv or "")[:n]:
            runs = [R("•  ", bold=True, color=_TEAL, size=size)] + rich_runs(_trim(sent, cap), size, fix)
            paras.append(P(runs, space_after=gap))
        return paras or [P([R("—", color=_MUTED, size=size)])]

    def chrome(s, title, subtitle):
        nonlocal page_no
        page_no += 1
        text(s, 0.45, 0.16, 9.10, 0.55, [P([R(title, bold=True, color=_PURPLE, size=24)])])
        rect(s, 0.47, 0.74, 9.06, 0.03, _TEAL)
        text(s, 0.45, 0.80, 9.10, 0.30, [P([R(subtitle, color=_GREY, size=11.5)])])
        text(s, 0.45, 5.32, 7.50, 0.22, [P([R(footer_text, color=_MUTED, size=7.5)])])
        text(s, 9.25, 5.32, 0.40, 0.22, [P([R(str(page_no), color=_MUTED, size=8)], align=PP_ALIGN.RIGHT)])

    def card(s, x, y, w, h, bar=_TEAL, fillc=_CARD):
        rect(s, x, y, w, h, fillc)
        rect(s, x, y, 0.06, h, bar)

    def stat_tile(s, x, y, w, h, big, label, color=_PURPLE, sub=None):
        card(s, x, y, w, h, color)
        text(s, x + 0.16, y + 0.06, w - 0.28, 0.60, [P([R(big, bold=True, color=color, size=30)])])
        text(s, x + 0.16, y + 0.66, w - 0.28, h - 0.70,
             [P([R(label, bold=True, color=_GREY, size=10)])] +
             ([P([R(sub, color=_GREY, size=8.5)])] if sub else []))

    def chip(s, x, y, w, h, label, sev, size=9):
        solid, bg, fg = _SEV.get(sev, _SEV["info"])
        sh = rect(s, x, y, w, h, bg, MSO_SHAPE.ROUNDED_RECTANGLE)
        sh.adjustments[0] = 0.5
        tf = sh.text_frame
        tf.margin_left = tf.margin_right = Inches(0.04)
        tf.margin_top = tf.margin_bottom = 0
        tf.vertical_anchor = MSO_ANCHOR.MIDDLE
        p = tf.paragraphs[0]
        p.alignment = PP_ALIGN.CENTER
        _add_run(p, label, size, True, fg)
        return sh

    def style_table(tbl, widths, header_size=10, body_size=9.5, row_h=0.30):
        for i, w in enumerate(widths):
            tbl.columns[i].width = Inches(w)
        for ri, row in enumerate(tbl.rows):
            row.height = Inches(row_h)
            for cell in row.cells:
                cell.margin_left = cell.margin_right = Inches(0.06)
                cell.margin_top = cell.margin_bottom = Inches(0.02)
                cell.vertical_anchor = MSO_ANCHOR.MIDDLE
                cell.fill.solid()
                cell.fill.fore_color.rgb = rgb(_PURPLE if ri == 0 else (_CARD if ri % 2 else "FFFFFF"))
                for p in cell.text_frame.paragraphs:
                    for r in p.runs:
                        r.font.name = _FONT
                        r.font.size = Pt(header_size if ri == 0 else body_size)
                        if ri == 0:
                            r.font.bold = True
                            r.font.color.rgb = rgb("FFFFFF")
                        elif r.font.color.type is None:
                            r.font.color.rgb = rgb(_GREY)

    def set_cell(cell, txt, color=None, bold=False, mono=False, align=None, fill_=None):
        cell.text = ""
        p = cell.text_frame.paragraphs[0]
        if align:
            p.alignment = align
        _add_run(p, str(txt), 9.5, bold, color or _GREY, mono)
        if fill_:
            cell.fill.solid()
            cell.fill.fore_color.rgb = rgb(fill_)

    def style_chart(gf, colors=None, number_format="0", label_size=10, gap=60):
        ch = gf.chart
        ch.has_legend = False
        ch.has_title = False
        ch.font.name = _FONT
        ch.font.size = Pt(9.5)
        plot = ch.plots[0]
        plot.gap_width = gap
        plot.has_data_labels = True
        plot.data_labels.font.size = Pt(label_size)
        plot.data_labels.font.bold = True
        plot.data_labels.font.name = _FONT
        plot.data_labels.font.color.rgb = rgb(_PURPLE)
        plot.data_labels.number_format = number_format
        plot.data_labels.number_format_is_linked = False
        plot.data_labels.position = XL_LABEL_POSITION.OUTSIDE_END
        va = ch.value_axis
        va.has_major_gridlines = True
        va.major_gridlines.format.line.color.rgb = rgb("E3DEEB")
        va.tick_labels.font.size = Pt(8.5)
        va.tick_labels.font.color.rgb = rgb(_MUTED)
        va.format.line.fill.background()
        ca = ch.category_axis
        ca.tick_labels.font.size = Pt(9.5)
        ca.tick_labels.font.color.rgb = rgb(_GREY)
        ca.format.line.color.rgb = rgb("E3DEEB")
        if colors:
            for pt, color in zip(plot.series[0].points, colors):
                pt.format.fill.solid()
                pt.format.fill.fore_color.rgb = rgb(color)
        else:
            plot.series[0].format.fill.solid()
            plot.series[0].format.fill.fore_color.rgb = rgb(_LAVENDER)
        return ch

    def divider(num, title, desc, bullets_):
        nonlocal page_no
        page_no += 1
        s = slide()
        rect(s, 0, 0, 10.0, 5.625, _PURPLE)
        rect(s, 7.10, -1.20, 5.50, 5.50, _PURPLE2, MSO_SHAPE.OVAL)
        rect(s, 8.30, 3.60, 3.40, 3.40, _MAGENTA, MSO_SHAPE.OVAL)
        text(s, 0.90, 0.90, 4.60, 0.35, [P([R("Code Security Review", bold=True, color=_TEAL, size=12.5)])])
        text(s, 0.90, 1.80, 5.80, 1.00, [P([R(title, bold=True, color="FFFFFF", size=30)])])
        text(s, 0.90, 2.80, 5.80, 0.90, [P([R(desc, color=_LILAC, size=12.5, autonum=False)])])
        paras = [P([R("In this section", bold=True, color=_TEAL, size=10.5)], space_after=4)]
        paras += [P([R("·  ", bold=True, color=_TEAL, size=10.5), R(b, color="FFFFFF", size=10.5, autonum=False)],
                    space_after=3) for b in bullets_[:4]]
        text(s, 0.90, 3.75, 5.80, 1.60, paras)
        text(s, 6.30, 0.70, 3.20, 2.40, [P([R(num, bold=True, color=_PURPLE_NUM, size=120)])])
        return s

    # ------------------------------------------------------------ 1 · cover
    s = slide()
    rect(s, 0, 0, 10.0, 5.625, _PURPLE)
    rect(s, -1.60, 1.40, 6.00, 6.00, _PURPLE2, MSO_SHAPE.OVAL)
    rect(s, 2.60, -2.60, 5.20, 5.20, _MAGENTA, MSO_SHAPE.OVAL)
    rect(s, 0.75, 3.15, 3.20, 0.03, _TEAL)
    text(s, 4.45, 0.95, 5.20, 1.90, [
        P([R("Code Security", bold=True, color="FFFFFF", size=36)]),
        P([R("Review", bold=True, color="FFFFFF", size=36)]),
        P([R("Findings · Exploit chains · Remediation plan", bold=True, color=_TEAL, size=15)]),
    ])
    meta = [P([R(_trim(review.name, 60), bold=True, color="FFFFFF", size=14)])]
    if review.repo_label:
        meta.append(P([R(_trim(review.repo_label, 60), color=_LILAC, size=11.5, autonum=False)]))
    scope_bits = []
    if metrics.get("total_files_in_scope"):
        scope_bits.append(f"{metrics['total_files_in_scope']} files scanned")
    if git_sha_short:
        scope_bits.append(f"commit {git_sha_short}")
    if created:
        scope_bits.append(created)
    if scope_bits:
        meta.append(P([R(" · ".join(scope_bits), color=_LILAC, size=11, autonum=False)]))
    meta.append(P([R(f"Visa Vulnerability Agentic Harness {tool_version}".strip() + " · detection only",
                     color=_MUTED, size=10, autonum=False)]))
    text(s, 4.45, 3.05, 5.20, 2.00, meta)
    if display_name:
        text(s, 0.75, 2.55, 3.40, 0.50, [P([R(display_name, bold=True, color="FFFFFF", size=13.5)])])
    text(s, 0.75, 3.35, 3.40, 1.60, [
        P([R("CONFIDENTIAL", bold=True, color=_TEAL, size=13)], space_after=5),
        P([R("AI-generated triage candidates. Every finding needs human confirmation "
             "before action.", color=_LILAC, size=9.5, autonum=False)]),
    ])
    page_no += 1

    # --------------------------------------------------- 2 · executive verdict
    s = slide()
    chrome(s, f"Executive Summary — {total} findings, {n_crit} critical",
           f"{n_crit + n_high} findings need attention now · {len(chains)} exploit chains · "
           f"{files_hit} files affected · {confirmed} of {total} confirmed by the scanner's verifier")
    tiles = [
        (str(total), "findings", _PURPLE, f"{files_hit} files affected"),
        (str(n_crit), "critical", _RED_D, "fix immediately"),
        (str(n_high), "high", _ROSE, "fix this sprint"),
        (str(len(chains)), "exploit chains", _MAGENTA,
         f"{len(fix_first)} fix(es) break all" if fix_first else "none reported"),
        (f"{round(100 * confirmed / total) if total else 0}%", "verifier-confirmed", _TEAL,
         f"{fp_count} rejected as false positive"),
    ]
    for i, (big, label, color, sub) in enumerate(tiles):
        stat_tile(s, 0.45 + i * 1.86, 1.22, 1.74, 1.22, big, label, color, sub)
    top3 = findings[:3]
    text(s, 0.45, 2.62, 9.10, 0.30, [P([R("Start here — the three most severe findings", bold=True, color=_PURPLE, size=12.5)])])
    for i, f in enumerate(top3):
        y = 2.98 + i * 0.74
        sev = f.get("severity") or "info"
        card(s, 0.45, y, 9.10, 0.66, _SEV[sev][0], "FFFFFF")
        chip(s, 0.62, y + 0.19, 0.90, 0.28, sev.title(), sev)
        text(s, 1.62, y + 0.06, 5.60, 0.30,
             [P([R(f"#{f.get('idx')}  ", bold=True, color=_MUTED, size=11),
                 R(_trim(f.get("title"), 70), bold=True, color=_PURPLE, size=11.5)])])
        text(s, 1.62, y + 0.36, 5.60, 0.28,
             [P(rich_runs(_first_sentences(f.get("impact") or f.get("description"), 1, 110), 9))])
        cv = f.get("cvss_score")
        text(s, 7.35, y + 0.08, 2.10, 0.52, [
            P([R(f"{f.get('file')}:{f.get('line_start')}", color=_BLUE, size=8.5, mono=True)]),
            P([R("CVSS " + (f"{cv:.1f}" if cv is not None else "—"), bold=True, color=_SEV[sev][0], size=9.5),
               R(f"   {f.get('cwe') or ''}", color=_MUTED, size=8.5, autonum=False)]),
        ])

    # ------------------------------------------------------- 3 · risk profile
    s = slide()
    chrome(s, "Risk Profile — Where the Exposure Sits",
           f"Severity mix, vulnerability types and the files that concentrate the risk")
    sev_data = CategoryChartData()
    sev_data.categories = [x.title() for x in _SEV_ORDER]
    sev_data.add_series("Findings", [by_sev.get(k, 0) for k in _SEV_ORDER])
    text(s, 0.45, 1.20, 4.40, 0.28, [P([R("By severity", bold=True, color=_PURPLE, size=12)])])
    gf = s.shapes.add_chart(XL_CHART_TYPE.COLUMN_CLUSTERED, Inches(0.40), Inches(1.45), Inches(4.50), Inches(2.45), sev_data)
    style_chart(gf, colors=[_SEV[k][0] for k in _SEV_ORDER], gap=45)
    class_items = sorted(by_class.items(), key=lambda kv: (-kv[1], kv[0]))[:6]
    text(s, 5.15, 1.20, 4.40, 0.28, [P([R("By vulnerability type", bold=True, color=_PURPLE, size=12)])])
    if class_items:
        class_data = CategoryChartData()
        class_data.categories = [_trim(k, 24) for k, _ in class_items][::-1]
        class_data.add_series("Findings", [v for _, v in class_items][::-1])
        gf = s.shapes.add_chart(XL_CHART_TYPE.BAR_CLUSTERED, Inches(5.05), Inches(1.45), Inches(4.50), Inches(2.45), class_data)
        style_chart(gf, gap=40)
    files_top = sorted(by_file.items(), key=lambda kv: (-kv[1], kv[0]))[:5]
    text(s, 0.45, 3.98, 9.10, 0.28,
         [P([R("Files with the most findings", bold=True, color=_PURPLE, size=12),
             R(f"   {files_hit} files carry findings; the top {len(files_top)} hold "
               f"{sum(v for _, v in files_top)} of {total}", color=_GREY, size=9.5)])])
    max_n = max([v for _, v in files_top] or [1])
    for i, (path, n) in enumerate(files_top):
        y = 4.30 + i * 0.20
        text(s, 0.45, y, 4.30, 0.20, [P([R(_trim(path, 58), color=_GREY, size=8.5, mono=True)])])
        rect(s, 4.85, y + 0.04, 3.9 * n / max_n, 0.12, _LAVENDER)
        text(s, 4.90 + 3.9 * n / max_n, y, 0.60, 0.20, [P([R(str(n), bold=True, color=_PURPLE, size=9)])])

    # ------------------------------------------------------- 4 · findings table
    s = slide()
    top = findings[:10]
    chrome(s, "Findings at a Glance",
           f"Top {len(top)} of {total}, sorted by severity then CVSS · full register with tracker columns in the XLSX")
    rows = 1 + max(len(top), 1)
    tbl = s.shapes.add_table(rows, 7, Inches(0.45), Inches(1.18), Inches(9.10), Inches(0.30 * rows)).table
    for ci, h in enumerate(("#", "Severity", "Finding", "Type", "File : line", "CVSS", "Verdict")):
        tbl.cell(0, ci).text = h
    if top:
        for ri, f in enumerate(top, start=1):
            sev = f.get("severity") or "info"
            solid, bg, fg = _SEV[sev]
            set_cell(tbl.cell(ri, 0), f.get("idx", ri), align=PP_ALIGN.CENTER)
            set_cell(tbl.cell(ri, 1), sev.title(), color=fg, bold=True, align=PP_ALIGN.CENTER, fill_=bg)
            set_cell(tbl.cell(ri, 2), _trim(f.get("title"), 62), color=_PURPLE, bold=True)
            set_cell(tbl.cell(ri, 3), _trim(f.get("vuln_class_label") or f.get("vuln_class"), 22))
            set_cell(tbl.cell(ri, 4), f"{_trim(f.get('file'), 34)}:{f.get('line_start')}", color=_BLUE, mono=True)
            cv = f.get("cvss_score")
            set_cell(tbl.cell(ri, 5), "—" if cv is None else f"{cv:.1f}", color=solid, bold=True, align=PP_ALIGN.CENTER)
            v = f.get("verdict")
            set_cell(tbl.cell(ri, 6), "Confirmed" if v == "TRUE_POSITIVE" else ("False positive" if v == "FALSE_POSITIVE" else "—"),
                     color=_GREEN_D if v == "TRUE_POSITIVE" else _MUTED, bold=v == "TRUE_POSITIVE", align=PP_ALIGN.CENTER)
    else:
        tbl.cell(1, 0).text = "No findings reported."
    style_table(tbl, [0.40, 0.95, 3.05, 1.30, 2.05, 0.55, 0.80], row_h=0.30)

    # --------------------------------------------- 5 · divider · critical findings
    spot = [f for f in findings if f.get("severity") == "critical"][:6] or findings[:2]
    if spot:
        divider("01", "Critical Findings", f"{len(spot)} finding(s) that need a fix before anything else — "
                "what is wrong, why it matters, how to fix it.",
                [f"#{f.get('idx')}  {_trim(f.get('title'), 48)}" for f in spot])

    # ------------------------------------------- 6+ · spotlights, two per slide
    for start in range(0, len(spot), 2):
        pair = spot[start:start + 2]
        s = slide()
        chrome(s, "Critical Findings — What, Why, Fix",
               f"Findings {start + 1}–{start + len(pair)} of {len(spot)} critical · plain-language summary, code in blue, "
               "attack terms in red, fixes in green")
        for j, f in enumerate(pair):
            x = 0.45 + j * 4.60
            w = 4.50
            sev = f.get("severity") or "info"
            card(s, x, 1.18, w, 4.02, _SEV[sev][0], "FFFFFF")
            rect(s, x, 1.18, w, 0.62, _SEV[sev][1])
            chip(s, x + 0.16, 1.28, 0.85, 0.26, sev.title(), sev, size=8.5)
            text(s, x + 1.10, 1.22, w - 1.25, 0.56,
                 [P([R(f"#{f.get('idx')}  ", bold=True, color=_MUTED, size=10),
                     R(_trim(f.get("title"), 70), bold=True, color=_PURPLE, size=11)])], anchor=MSO_ANCHOR.MIDDLE)
            cv = f.get("cvss_score")
            facts = [R(f"{f.get('file')}:{f.get('line_start')}-{f.get('line_end')}", color=_BLUE, size=8.5, mono=True),
                     R(f"   CVSS {cv:.1f}" if cv is not None else "", bold=True, color=_SEV[sev][0], size=9),
                     R(f"   {f.get('cwe') or ''}", color=_MUTED, size=8.5, autonum=False)]
            if f.get("verdict") == "TRUE_POSITIVE":
                facts.append(R("   ✓ verifier-confirmed", bold=True, color=_GREEN_D, size=8.5))
            text(s, x + 0.16, 1.86, w - 0.32, 0.24, [P(facts)])
            y = 2.14
            for head, key, fix, color in (("WHAT IS WRONG", "description", False, _RED_D),
                                           ("WHY IT MATTERS", "impact", False, _AMBER),
                                           ("HOW TO FIX", "recommendation", True, _GREEN_D)):
                rect(s, x + 0.16, y + 0.02, w - 0.32, 0.015, "E3DEEB")
                text(s, x + 0.16, y + 0.06, w - 0.32, 0.20, [P([R(head, bold=True, color=color, size=8.5)])])
                body = bullets(f.get(key), size=9, fix=fix, n=2, cap=125, gap=1)
                text(s, x + 0.16, y + 0.28, w - 0.32, 0.70, body)
                y += 1.02

    # ------------------------------------------------- divider · exploit chains
    if chains:
        divider("02", "Exploit Chains", f"{len(chains)} attack paths where findings combine — an attacker "
                "walks the steps in order; breaking any one step breaks the chain.",
                [_trim(c.get("title"), 52) for c in chains])
        for start in range(0, min(len(chains), 8), 4):
            group = chains[start:start + 4]
            s = slide()
            chrome(s, "Exploit Chains — Step by Step",
                   f"Chains {start + 1}–{start + len(group)} of {len(chains)} · step boxes are finding numbers from the register · "
                   "fix the highlighted first step to break the chain")
            for i, c in enumerate(group):
                y = 1.18 + i * 1.02
                sev = c.get("severity") or "info"
                card(s, 0.45, y, 9.10, 0.94, _SEV[sev][0], _CARD if i % 2 else "FFFFFF")
                chip(s, 0.60, y + 0.10, 0.80, 0.24, sev.title(), sev, size=8)
                text(s, 1.48, y + 0.06, 7.90, 0.30, [P([R(_trim(c.get("title"), 90), bold=True, color=_PURPLE, size=11)])])
                steps = list(c.get("steps") or [])[:6]
                sx = 0.60
                bw = min(1.75, (8.80 - 0.25 * max(len(steps) - 1, 0)) / max(len(steps), 1))
                for k, st in enumerate(steps):
                    ff = title_by_idx.get(st) or {}
                    fill_ = _SEV[sev][1] if k == 0 else "FFFFFF"
                    sh = rect(s, sx, y + 0.40, bw, 0.46, fill_, MSO_SHAPE.CHEVRON if k else MSO_SHAPE.PENTAGON, line=_LILAC)
                    sh.adjustments[0] = 0.18
                    tf = sh.text_frame
                    tf.margin_left = Inches(0.14 if k else 0.06)
                    tf.margin_right = Inches(0.10)
                    tf.margin_top = tf.margin_bottom = 0
                    tf.vertical_anchor = MSO_ANCHOR.MIDDLE
                    tf.word_wrap = True
                    p = tf.paragraphs[0]
                    _add_run(p, f"#{st} ", 8.5, True, _SEV[sev][2] if k == 0 else _PURPLE)
                    _add_run(p, _trim(ff.get("title") or "not in register", 34), 7.5, False, _GREY)
                    sx += bw + 0.06
                narrative = _first_sentences(c.get("narrative"), 1, 150)
                if narrative:
                    text(s, 1.48, y + 0.34, 7.95, 0.10, [P([])])  # spacer keeps title/steps rhythm
                text(s, 5.40, y + 0.06, 4.05, 0.30,
                     [P([R("Break it: ", bold=True, color=_GREEN_D, size=8.5),
                         R(f"fix #{steps[0]} first" if steps else "—", color=_GREY, size=8.5)], align=PP_ALIGN.RIGHT)])

    # ------------------------------------------------ divider · remediation
    divider("03", "Remediation Plan", "A deterministic order of work: criticals first, then the fixes that "
            "break the most chains, then highs grouped by file.",
            [f"{n_crit} critical, {n_high} high", f"{len(fix_first)} fixes break every chain" if fix_first else "no chains to break",
             "re-scan to confirm"])

    # ------------------------------------------------------ remediation plan
    s = slide()
    chrome(s, "Remediation Plan — Work in This Order",
           "Priority = severity, then how many exploit chains the fix breaks · owner and dates go in the XLSX tracker")
    plan = []
    seen = set()
    for idx, hits in fix_first:
        f = title_by_idx.get(idx)
        if f and idx not in seen:
            plan.append((f, hits))
            seen.add(idx)
    for f in findings:
        if f.get("idx") not in seen and f.get("severity") in ("critical", "high"):
            plan.append((f, chain_members.get(f.get("idx"), 0)))
            seen.add(f.get("idx"))
    plan.sort(key=lambda t: (_SEV_ORDER.index(t[0].get("severity") or "info"), -t[1], t[0].get("idx") or 0))
    plan = plan[:7]
    rows = 1 + max(len(plan), 1)
    tbl = s.shapes.add_table(rows, 5, Inches(0.45), Inches(1.18), Inches(6.30), Inches(0.30 * rows)).table
    for ci, h in enumerate(("#", "Severity", "Finding (file)", "Chains broken", "Fix in one line")):
        tbl.cell(0, ci).text = h
    for ri, (f, hits) in enumerate(plan, start=1):
        sev = f.get("severity") or "info"
        solid, bg, fg = _SEV[sev]
        set_cell(tbl.cell(ri, 0), ri, bold=True, color=_PURPLE, align=PP_ALIGN.CENTER)
        set_cell(tbl.cell(ri, 1), sev.title(), color=fg, bold=True, align=PP_ALIGN.CENTER, fill_=bg)
        c2 = tbl.cell(ri, 2)
        c2.text = ""
        p2 = c2.text_frame.paragraphs[0]
        _add_run(p2, f"#{f.get('idx')} {_trim(f.get('title'), 44)}", 9, True, _PURPLE)
        p3 = c2.text_frame.add_paragraph()
        _add_run(p3, _trim((f.get("file") or "").split("/")[-1], 30), 8, False, _BLUE, mono=True)
        set_cell(tbl.cell(ri, 3), hits or "—", color=_MAGENTA if hits else _MUTED, bold=bool(hits), align=PP_ALIGN.CENTER)
        # plain cell (no rich runs) — drop markdown backticks so code reads as prose
        set_cell(tbl.cell(ri, 4), _first_sentences(f.get("recommendation"), 1, 95).replace("`", ""))
    if not plan:
        tbl.cell(1, 0).text = "Nothing to remediate."
    style_table(tbl, [0.35, 0.80, 2.15, 0.70, 2.30], body_size=8.5, row_h=0.44)
    # right column: the derived story
    card(s, 6.95, 1.18, 2.60, 1.35, _MAGENTA, _ROSEBG)
    ff_lines = [P([R("Fewest fixes, biggest effect", bold=True, color=_RED_D, size=10.5)], space_after=3)]
    if fix_first:
        ff_lines.append(P([R(f"Fixing {len(fix_first)} finding(s) breaks all {len(chains)} chains: ", size=9),
                           R(", ".join(f"#{i}" for i, _ in fix_first), bold=True, color=_PURPLE, size=9)]))
    else:
        ff_lines.append(P([R("No exploit chains reported, so no cross-finding leverage — work by severity.", size=9, autonum=False)]))
    text(s, 7.11, 1.26, 2.36, 1.20, ff_lines)
    card(s, 6.95, 2.63, 2.60, 1.30, _AMBER, _AMBERBG)
    highs_by_file = {}
    for f in findings:
        if f.get("severity") == "high":
            highs_by_file.setdefault((f.get("file") or "").split("/")[-1], 0)
            highs_by_file[(f.get("file") or "").split("/")[-1]] += 1
    hb = sorted(highs_by_file.items(), key=lambda kv: (-kv[1], kv[0]))[:3]
    text(s, 7.11, 2.71, 2.36, 1.15,
         [P([R("Batch the highs by file", bold=True, color=_AMBER, size=10.5)], space_after=3)] +
         ([P([R(f"{n} in ", size=9), R(path, color=_BLUE, size=8.5, mono=True)], space_after=1) for path, n in hb]
          or [P([R("No high-severity findings.", size=9, autonum=False)])]))
    card(s, 6.95, 4.03, 2.60, 1.17, _TEAL, _MINT)
    text(s, 7.11, 4.11, 2.36, 1.05,
         [P([R("Then verify", bold=True, color=_GREEN_D, size=10.5)], space_after=3),
          P([R(f"Confirm or dismiss the {fp_count} verifier-rejected finding(s), re-run the scan, "
               "and compare counts.", size=9)])])

    # ------------------------------------------------------- fix status
    if run_extras and run_extras.get("mode") == "fix":
        s = slide()
        chrome(s, "Fix Status — What the Scanner Attempted",
               "Attempted fixes from the run folder, the scanner's own accept/reject policy, and whether tests broke")
        fix_counts = run_extras.get("fix_counts") or {}
        tile_order = ["fixed", "patch_rejected", "needs_review", "not_fixed", "not_attempted"]
        tile_colors = {"fixed": _TEAL, "patch_rejected": _AMBER, "needs_review": _ROSE,
                       "not_fixed": _RED_D, "not_attempted": _MUTED}
        tiles = [(status, n) for status in tile_order if (n := fix_counts.get(status))]
        tw = min(2.18, 9.10 / max(len(tiles), 1) - 0.10)
        for i, (status, n) in enumerate(tiles):
            stat_tile(s, 0.45 + i * (tw + 0.10), 1.18, tw, 1.10, str(n),
                      FIX_STATUS_LABELS.get(status, status), tile_colors.get(status, _PURPLE))
        attempted = [f for f in findings if (f.get("fix") or {}).get("status") in ("fixed", "patch_rejected")]
        attempted.sort(key=lambda f: (f["fix"].get("tests") != "broke_tests", f["fix"].get("status") != "fixed"))
        max_rows = 6  # what fits under the tiles, even with two-line titles; the Excel "Fixes" sheet has every row
        more = len(attempted) - max_rows
        attempted = attempted[:max_rows]
        heading = "Attempted fixes" + (f" (first {max_rows}; {more} more in the Excel 'Fixes' sheet)" if more > 0 else "")
        text(s, 0.45, 2.46, 9.10, 0.28, [P([R(heading, bold=True, color=_PURPLE, size=12)])])
        rows = 1 + max(len(attempted), 1)
        tbl = s.shapes.add_table(rows, 4, Inches(0.45), Inches(2.78), Inches(9.10), Inches(0.30 * rows)).table
        for ci, h in enumerate(("#", "Finding", "Fix status", "Tests after fix")):
            tbl.cell(0, ci).text = h
        if attempted:
            for ri, f in enumerate(attempted, start=1):
                fix = f.get("fix") or {}
                broke = fix.get("tests") == "broke_tests"
                set_cell(tbl.cell(ri, 0), f.get("idx", ri), align=PP_ALIGN.CENTER)
                set_cell(tbl.cell(ri, 1), _trim(f.get("title"), 60), color=_PURPLE, bold=True)
                set_cell(tbl.cell(ri, 2), FIX_STATUS_LABELS.get(fix.get("status"), fix.get("status") or "—"))
                tests_txt = FIX_TESTS_LABELS.get(fix.get("tests"), "—")
                if broke:
                    tests_txt = f"{tests_txt} — do not treat as fixed"
                tests_color = _RED_D if broke else (_GREEN_D if fix.get("tests") == "passed" else _MUTED)
                set_cell(tbl.cell(ri, 3), tests_txt, color=tests_color, bold=broke,
                         fill_=("FFE4E6" if broke else None))
        else:
            tbl.cell(1, 0).text = "No fixes were attempted."
        style_table(tbl, [0.40, 3.30, 2.60, 2.80], row_h=0.32)

    # ---------------------------------------------- coverage & confidence
    s = slide()
    chrome(s, "Scan Coverage & Confidence — How Much to Trust This",
           "What was analysed, how the scanner checked itself, and the limits of an automated review")
    run_cov = ((run_extras or {}).get("coverage") or {})
    in_scope = metrics.get("total_files_in_scope") or run_cov.get("files_in_scope")
    analysed = metrics.get("analyzed_files_unique") or run_cov.get("files_analyzed")
    cov_pct = f"{round(100 * analysed / in_scope)}%" if in_scope and analysed else "—"
    dur = metrics.get("duration_sec") or run_cov.get("duration_sec")
    ctiles = [
        (str(in_scope or "—"), "files in scope", _PURPLE, f"{analysed or '—'} analysed ({cov_pct})"),
        (f"{round(dur / 60)} min" if dur else "—", "scan duration", _LAVENDER,
         f"{metrics.get('total_tokens', 0):,} tokens" if metrics.get("total_tokens") else "detection only (S0–S9)"),
        (str(confirmed), "confirmed by verifier", _TEAL, f"{fp_count} rejected · {total - confirmed - fp_count} unverified"),
        (str(report.get("raw_findings_count") or total), "raw candidates", _MAGENTA,
         f"{report.get('dropped_count') or 0} dropped by triage → {total} kept"),
    ]
    ctile_h = 1.00 if run_extras else 1.22
    for i, (big, label, color, sub) in enumerate(ctiles):
        stat_tile(s, 0.45 + i * 2.32, 1.18, 2.18, ctile_h, big, label, color, sub)
    if run_extras:
        # ponytail: one compact strip (not a redesigned layout) — the slide has
        # no spare real estate, so the run note + build status + health bullets
        # are joined into a single trimmed line rather than stacked.
        cov = run_extras.get("coverage") or {}
        tests = run_extras.get("tests") or {}
        bits = [f"{run_extras.get('deep_verified', 0)} of {run_extras.get('total', total)} findings deep-verified"]
        if tests.get("build"):
            bits.append(f"test build: {tests['build']}")
        bits.extend((cov.get("health") or [])[:3])
        text(s, 0.45, 2.22, 9.10, 0.30,
             [P([R(_trim(" · ".join(bits), 190), color=_GREY, size=8.5, autonum=False)])])
    loc = metrics.get("loc_scanned_by_language") or {}
    loc_items = sorted(((k, v) for k, v in loc.items() if v), key=lambda kv: -kv[1])[:6]
    text(s, 0.45, 2.58, 4.40, 0.28, [P([R("Lines analysed by language", bold=True, color=_PURPLE, size=12)])])
    if loc_items:
        ld = CategoryChartData()
        ld.categories = [k for k, _ in loc_items][::-1]
        ld.add_series("LOC", [v for _, v in loc_items][::-1])
        gf = s.shapes.add_chart(XL_CHART_TYPE.BAR_CLUSTERED, Inches(0.40), Inches(2.84), Inches(4.50), Inches(2.35), ld)
        style_chart(gf, number_format="#,##0", label_size=9, gap=35)
    else:
        text(s, 0.45, 2.90, 4.40, 0.40, [P([R("No per-language metrics in this report.", color=_MUTED, size=10, autonum=False)])])
    models = manifest.get("models") or {}
    model_ids = sorted({(m or {}).get("id") for m in models.values() if (m or {}).get("id")})
    card(s, 5.15, 2.58, 4.40, 1.22, _LAVENDER, _CARD)
    text(s, 5.31, 2.66, 4.10, 1.10,
         [P([R("How the scanner checks itself", bold=True, color=_PURPLE, size=10.5)], space_after=3),
          P([R("•  ", bold=True, color=_TEAL, size=9), R("Every candidate is re-examined by a ", size=9),
             K("verifier pass", 9), R(" that votes it confirmed or false positive.", size=9, autonum=False)], space_after=2),
          P([R("•  ", bold=True, color=_TEAL, size=9), R("Models: ", size=9),
             R(", ".join(model_ids) if model_ids else "not recorded (upload the run manifest)", color=_BLUE, size=8.5, mono=True)])])
    card(s, 5.15, 3.90, 4.40, 1.29, _MAGENTA, _ROSEBG)
    text(s, 5.31, 3.98, 4.10, 1.17,
         [P([R("What it cannot tell you", bold=True, color=_RED_D, size=10.5)], space_after=3),
          P([R("•  ", bold=True, color=_TEAL, size=9), R("It reads code at rest — ", size=9, autonum=False),
             K("not a penetration test", 9, _MAGENTA), R("; reachability is reasoned, not exercised.", size=9, autonum=False)], space_after=2),
          P([R("•  ", bold=True, color=_TEAL, size=9), R("Non-deterministic: a re-run can differ. Treat counts as a ", size=9, autonum=False),
             K("triage queue", 9, _MAGENTA), R(", not a scorecard.", size=9, autonum=False)])])

    # ---------------------------------------------------------- next steps
    s = slide()
    chrome(s, "Recommended Next Steps", "Four moves, in order — each one measurable at the next scan")
    steps = [
        ("01", _RED_D, "Confirm and fix the criticals",
         f"{n_crit} critical finding(s): reproduce, patch, add a regression test. "
         + (f"Start with #{', #'.join(str(i) for i, _ in fix_first[:3])} — they break the chains." if fix_first else "")),
        ("02", _ROSE, "Clear the highs by file",
         f"{n_high} high finding(s) across {len(highs_by_file)} file(s); one owner per file, one PR per file."),
        ("03", _AMBER, "Triage the rest",
         f"{by_sev.get('medium', 0)} medium and {by_sev.get('low', 0) + by_sev.get('info', 0)} low/info: "
         "accept, defer or fix — record the decision in the XLSX Status column."),
        ("04", _TEAL, "Re-scan and compare",
         "Run the kit again on the fixed commit; the review should show fewer criticals and no surviving chains."),
    ]
    for i, (num, color, head, body) in enumerate(steps):
        x = 0.45 + (i % 2) * 4.60
        y = 1.22 + (i // 2) * 1.98
        card(s, x, y, 4.50, 1.84, color)
        text(s, x + 0.20, y + 0.14, 0.80, 0.70, [P([R(num, bold=True, color=color, size=28)])])
        text(s, x + 1.05, y + 0.16, 3.30, 0.36, [P([R(head, bold=True, color=_PURPLE, size=13)])])
        text(s, x + 1.05, y + 0.56, 3.30, 1.20, [P([R(body, color=_GREY, size=10)])])

    # ------------------------------------------------------------- closing
    s = slide()
    rect(s, 0, 0, 10.0, 5.625, _PURPLE)
    rect(s, 7.10, -1.20, 5.50, 5.50, _PURPLE2, MSO_SHAPE.OVAL)
    text(s, 0.90, 1.40, 8.20, 0.60,
         [P([R("Findings produced by Visa Vulnerability Agentic Harness (Apache-2.0).", bold=True, color="FFFFFF", size=16)])])
    text(s, 0.90, 2.20, 8.20, 1.60, [
        P([R("Findings are AI-generated triage candidates, not confirmed vulnerabilities; "
             "human review is required before action.", color=_LILAC, size=12, autonum=False)], space_after=8),
        P([R(f"{total} findings · {n_crit} critical · {n_high} high · {len(chains)} exploit chains · "
             f"{confirmed} verifier-confirmed", color=_TEAL, size=11)]),
    ])
    text(s, 0.90, 4.60, 8.20, 0.45, [P([R(footer_text, color=_MUTED, size=9)])])

    buf = io.BytesIO()
    prs.save(buf)
    return buf.getvalue()
