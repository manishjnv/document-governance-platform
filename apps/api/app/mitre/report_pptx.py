"""MITRE assessment PPTX briefing-deck builder (2026-08-14, from the VFQ
customer-deliverable review): a client-presentation deck in the same design
system as the XLSX export (deep purple / teal / magenta, card-with-accent-bar
layout, highlighted keywords).

Same invariants as every other report surface: numbers come ONLY from the
stored summary/technique_results JSONB — never recomputed here; the only LLM
text reused is the stored narrative's per-gap recommendations (rephrased
words, never numbers). Fully deterministic output for a given assessment.
"""

import io

from app.mitre.report_common import (
    DOMAIN_LABELS,
    compute_log_source_coverage,
    resolve_branding,
)

# palette — mirrors report_xlsx's BRAND/ACCENT plus the deck-only tones
_PURPLE = "341954"
_PURPLE2 = "46246B"
_LAVENDER = "7370A7"
_MAGENTA = "B71D6B"
_TEAL = "00A98B"
_GREEN = "007A5E"
_GREEN_D = "1E7B4D"
_AMBER = "C8801A"
_CARD = "F3F0F7"
_MINT = "E7F5F1"
_ROSEBG = "FCEEF3"
_GREY = "404040"
_MUTED = "BBBDC2"
_LILAC = "D8D2E4"
_FONT = "Tenorite"  # MS cloud font; PowerPoint substitutes silently if absent

_STATE_PLAIN = {"not_covered": "No rule detects this", "partial": "Half-covered"}


def build_pptx_export(assessment, use_cases: list, branding: dict | None = None) -> bytes:
    """The briefing deck as .pptx bytes. use_cases: the same dict rows the
    XLSX builder receives (log_source / last_triggered feed two slides)."""
    from pptx import Presentation
    from pptx.chart.data import CategoryChartData
    from pptx.dml.color import RGBColor
    from pptx.enum.chart import XL_CHART_TYPE, XL_LEGEND_POSITION
    from pptx.enum.shapes import MSO_SHAPE
    from pptx.enum.text import MSO_ANCHOR, PP_ALIGN
    from pptx.util import Inches, Pt

    branding = resolve_branding(branding)
    display_name = branding["report_display_name"]
    summary = assessment.summary or {}
    params = assessment.params or {}
    intake = params.get("intake") or {}
    overall = summary.get("overall", {})
    gaps = summary.get("gaps", [])
    roadmap = summary.get("roadmap", {})
    quality = summary.get("quality", {})
    counts = summary.get("counts", {})
    narrative = summary.get("narrative", {})
    gap_recs = narrative.get("gap_recommendations", {})
    completed = str(assessment.completed_at or "")[:10]
    total_rules = counts.get("use_cases", len(use_cases))
    never_count = sum(
        1 for uc in use_cases
        if str(uc.get("last_triggered") or "").strip().lower() == "never"
    )
    footer_text = (
        f"{intake.get('project_name') or assessment.name} · MITRE ATT&CK "
        f"v{assessment.attack_version} · {display_name} · {completed}"
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

    def text(s, x, y, w, h, paras, anchor=MSO_ANCHOR.TOP):
        """paras: [(runs, opts)] with runs [(txt, {bold,color,size})]."""
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
            for txt, ro in runs:
                r = p.add_run()
                r.text = str(txt)
                f = r.font
                f.name = _FONT
                f.size = Pt(ro.get("size", 9))
                f.bold = ro.get("bold", False)
                f.color.rgb = rgb(ro.get("color", "000000"))
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

    # ------------------------------------------------------------- 1 · cover
    s = slide()
    rect(s, 0, 0, 10.0, 5.625, _PURPLE)
    rect(s, -1.60, 1.40, 6.00, 6.00, _PURPLE2, MSO_SHAPE.OVAL)
    rect(s, 2.60, -2.60, 5.20, 5.20, _MAGENTA, MSO_SHAPE.OVAL)
    rect(s, 0.75, 3.15, 3.20, 0.03, _TEAL)
    text(s, 4.45, 1.05, 5.20, 1.90, [
        P([R("MITRE ATT&CK", bold=True, color="FFFFFF", size=36)]),
        P([R("Coverage Assessment", bold=True, color="FFFFFF", size=36)]),
        P([R("Detection coverage · Gaps · Roadmap", bold=True, color=_TEAL, size=17)]),
    ])
    meta = [P([R(intake.get("project_name") or assessment.name,
                 bold=True, color="FFFFFF", size=13.5)])]
    if intake.get("prepared_by"):
        meta.append(P([R(f"Prepared by {intake['prepared_by']}", color=_MUTED, size=11)]))
    meta.append(P([R(f"{total_rules} detection rules analyzed", color=_MUTED, size=11)]))
    meta.append(P([R(f"MITRE ATT&CK v{assessment.attack_version} · {completed}",
                     color=_MUTED, size=11)]))
    text(s, 4.45, 3.15, 5.20, 1.90, meta)
    text(s, 0.75, 2.55, 3.40, 0.50,
         [P([R(display_name, bold=True, color="FFFFFF", size=13.5)])])
    page_no += 1

    # -------------------------------------------------------- 2 · headline
    s = slide()
    chrome(s, f"Headline Result — {overall.get('strict_pct')}% of Applicable "
              "Techniques Covered",
           f"{overall.get('covered')} of {overall.get('applicable')} techniques "
           "your environment is exposed to have at least one enabled detection rule")
    gap_total = (overall.get("not_covered") or 0) + (overall.get("partial") or 0)
    tiles = [
        (f"{overall.get('strict_pct')}%",
         f"coverage ({overall.get('weighted_pct')}% weighted) — counted at "
         "sub-technique level", _PURPLE),
        (f"{overall.get('covered')} / {overall.get('applicable')}",
         "techniques covered by at least one enabled rule", _TEAL),
        (str(gap_total),
         f"gaps: {overall.get('not_covered')} with no rule + "
         f"{overall.get('partial')} partially covered", _MAGENTA),
        (str(overall.get("not_applicable")),
         "not applicable — excluded with stated reasons, not scored", _LAVENDER),
    ]
    for i, (big, label, color) in enumerate(tiles):
        stat_tile(s, 0.45 + i * 2.32, 1.25, 2.17, 1.20, big, label, color)
    info_card(s, 0.45, 2.70, 4.45, 1.10, _TEAL, _MINT, "Where you stand", _GREEN_D,
              [P([R("Early SIEM detection programs typically start ", size=9),
                  R("under 10%", bold=True, color=_GREEN, size=9),
                  R(" of ATT&CK — the roadmap matters more than the grade.", size=9)])])
    if never_count:
        info_card(s, 5.10, 2.70, 4.45, 1.10, _MAGENTA, _ROSEBG, "The trust lens", "B02830",
                  [P([R(f"{never_count} of {total_rules} rules found no events",
                        bold=True, color=_MAGENTA, size=9),
                      R(" when last validated. They count toward coverage — but their "
                        "quality scores are capped until they prove they fire.", size=9)])])
    else:
        info_card(s, 5.10, 2.70, 4.45, 1.10, _LAVENDER, _CARD, "Provenance", _PURPLE,
                  [P([R("Every number is computed from your own rule export and "
                        "asset inventory — drill into any technique in the "
                        "spreadsheet register.", size=9)])])
    domains_line = " · ".join(
        f"{DOMAIN_LABELS.get(d, d)} {v.get('strict_pct')}%"
        for d, v in (summary.get("domains") or {}).items() if v.get("applicable")
    ) or "no applicable domains"
    info_card(s, 0.45, 3.95, 9.10, 1.00, _LAVENDER, _CARD,
              "Why “applicable” matters", _PURPLE,
              [P([R("Techniques for platforms you don't run are excluded from the "
                    "denominator with the reason recorded — the score reflects your "
                    "real attack surface. ", size=9),
                  R("By matrix: ", bold=True, color=_PURPLE, size=9),
                  R(domains_line, bold=True, color=_GREEN, size=9)])])

    # -------------------------------------------- 3 · coverage by tactic
    domains = summary.get("domains") or {}
    primary = max(
        (d for d in domains if (domains[d] or {}).get("applicable")),
        key=lambda d: domains[d].get("applicable", 0), default=None,
    )
    if primary and domains[primary].get("tactics"):
        tactics = [t for t in domains[primary]["tactics"] if t.get("applicable")]
        s = slide()
        chrome(s, "Coverage by Attack Stage (Tactic)",
               f"Share of applicable techniques covered at each stage — "
               f"{DOMAIN_LABELS.get(primary, primary)} matrix")
        cd = CategoryChartData()
        cd.categories = [t.get("name") for t in tactics]
        cd.add_series("Coverage %", [t.get("strict_pct") or 0 for t in tactics])
        gf = s.shapes.add_chart(XL_CHART_TYPE.BAR_CLUSTERED, Inches(0.45),
                                Inches(1.25), Inches(5.85), Inches(3.85), cd)
        ch = gf.chart
        ch.has_title = False
        ch.has_legend = False
        ser = ch.series[0]
        ser.format.fill.solid()
        ser.format.fill.fore_color.rgb = rgb(_TEAL)
        plot = ch.plots[0]
        plot.gap_width = 60
        plot.has_data_labels = True
        plot.data_labels.font.size = Pt(8)
        plot.data_labels.font.name = _FONT
        plot.data_labels.font.color.rgb = rgb(_PURPLE)
        plot.data_labels.number_format = "0.0"
        plot.data_labels.number_format_is_linked = False
        ch.category_axis.tick_labels.font.size = Pt(8.5)
        ch.category_axis.tick_labels.font.name = _FONT
        ch.value_axis.visible = False
        ch.value_axis.has_major_gridlines = False
        ranked_tactics = sorted(tactics, key=lambda t: t.get("strict_pct") or 0)
        worst, best = ranked_tactics[:2], ranked_tactics[-2:][::-1]
        info_card(s, 6.50, 1.25, 3.05, 1.55, _TEAL, _MINT, "Strongest stages", _GREEN_D,
                  [P([R(f"{t.get('name')} {t.get('strict_pct')}%", bold=True,
                        color=_GREEN, size=8.5),
                      R(f" — {t.get('covered')} of {t.get('applicable')} techniques",
                        size=8.5)], space_after=3) for t in best])
        info_card(s, 6.50, 3.00, 3.05, 1.55, _MAGENTA, _ROSEBG, "Weakest stages", "B02830",
                  [P([R(f"{t.get('name')} {t.get('strict_pct')}%", bold=True,
                        color=_MAGENTA, size=8.5),
                      R(f" — {t.get('not_covered')} techniques open", size=8.5)],
                     space_after=3) for t in worst])

    # ---------------------------------------------- 4 · detection quality
    if quality.get("scored"):
        s = slide()
        chrome(s, "Detection Quality — Coverage Is Not the Same as Confidence",
               "Each covered technique scored 0–100 on rule provenance, status, "
               "logic and telemetry match")
        cd = CategoryChartData()
        cd.categories = ["Strong (75+)", "Moderate (45–74)", "Weak (<45)"]
        cd.add_series("Techniques", [quality.get("strong", 0),
                                     quality.get("moderate", 0),
                                     quality.get("weak", 0)])
        gf = s.shapes.add_chart(XL_CHART_TYPE.DOUGHNUT, Inches(0.45), Inches(1.30),
                                Inches(3.55), Inches(3.30), cd)
        ch = gf.chart
        ch.has_title = False
        ch.has_legend = True
        ch.legend.position = XL_LEGEND_POSITION.BOTTOM
        ch.legend.include_in_layout = False
        ch.legend.font.size = Pt(9)
        ch.legend.font.name = _FONT
        for pt, color in zip(ch.plots[0].series[0].points, (_TEAL, _AMBER, _MAGENTA)):
            pt.format.fill.solid()
            pt.format.fill.fore_color.rgb = rgb(color)
        plot = ch.plots[0]
        plot.has_data_labels = True
        plot.data_labels.show_value = True
        plot.data_labels.font.size = Pt(10)
        plot.data_labels.font.bold = True
        plot.data_labels.font.name = _FONT
        plot.data_labels.font.color.rgb = rgb("FFFFFF")
        info_card(s, 4.35, 1.30, 5.20, 1.16, _TEAL, _MINT,
                  f"{quality.get('strong', 0)} strong", _GREEN_D,
                  [P([R("Backed by enabled rules whose provenance, logic and "
                        "telemetry all line up — your most trustworthy detections.",
                        size=9)])])
        info_card(s, 4.35, 2.60, 5.20, 1.16, _AMBER, _CARD,
                  f"{quality.get('moderate', 0)} moderate", "8A5A10",
                  [P([R("Reasonable rules with an open question — unproven firing, "
                        "partial telemetry match, or AI-suggested mapping.", size=9)])])
        info_card(s, 4.35, 3.90, 5.20, 1.16, _MAGENTA, _ROSEBG,
                  "How to move the needle", "B02830",
                  [P([R("Validate the silent rules first", bold=True,
                        color=_MAGENTA, size=9),
                      R(" — zero new engineering; average strength today: ", size=9),
                      R(f"{quality.get('avg_strength')}", bold=True, size=9),
                      R("/100.", size=9)])])

    # ------------------------------------------- 5 · coverage by log source
    from app.mitre import attack_data
    groups = compute_log_source_coverage(
        use_cases, assessment.technique_results or [], attack_data.DEFAULT)
    if groups:
        s = slide()
        chrome(s, "What Each Log Source Buys You",
               "Detection rules and techniques covered per source — and the "
               "sources paying rent for nothing")
        top = groups[:8]
        rows = [("Log source", "Rules", "Techniques covered")]
        rows += [(g.get("log_source"), g.get("rule_count"),
                  g.get("techniques_covered")) for g in top]
        tbl = s.shapes.add_table(len(rows), 3, Inches(0.45), Inches(1.25),
                                 Inches(5.30), Inches(3.55)).table
        for ri, row in enumerate(rows):
            for ci, val in enumerate(row):
                tbl.cell(ri, ci).text = str(val)
        style_table(tbl, [3.30, 0.85, 1.15], header_size=9, body_size=8.5)
        zero = [g for g in groups if not g.get("techniques_covered")]
        best_g = top[0] if top else None
        if best_g:
            info_card(s, 6.00, 1.25, 3.55, 1.55, _TEAL, _MINT, "Your workhorse", _GREEN_D,
                      [P([R(str(best_g.get("log_source")), bold=True, color=_GREEN, size=8.5),
                          R(f" powers {best_g.get('rule_count')} rules covering "
                            f"{best_g.get('techniques_covered')} techniques — protect "
                            "this pipeline first.", size=8.5)])])
        info_card(s, 6.00, 3.00, 3.55, 1.55, _MAGENTA, _ROSEBG,
                  "Paying for silence", "B02830",
                  [P([R(f"{len(zero)} source group(s)", bold=True, color=_MAGENTA, size=8.5),
                      R(" have rules mapped to no covered technique — map them "
                        "properly or consciously accept (and document) the gap.",
                        size=8.5)])])

    # ----------------------------------------------------- 6 · top fixes
    if gaps:
        top5 = gaps[:5]
        s = slide()
        chrome(s, f"Top {len(top5)} Fixes — Start Here",
               "Highest-priority gaps first, ranked by real-world prevalence, "
               "your threat profile and build effort")
        rows = [("#", "Technique", "Recommendation", "Build effort")]
        for i, g in enumerate(top5, 1):
            tid = g.get("technique_id")
            rec = gap_recs.get(tid) or g.get("hint") or ""
            rows.append((str(i), f"{g.get('name')} ({tid})", str(rec)[:220],
                         {"short": "Short (0–3 mo)", "mid": "Mid (3–9 mo)",
                          "long": "Long (9–18 mo)"}.get(g.get("feasibility"), "")))
        tbl = s.shapes.add_table(len(rows), 4, Inches(0.45), Inches(1.30),
                                 Inches(9.10), Inches(3.30)).table
        for ri, row in enumerate(rows):
            for ci, val in enumerate(row):
                tbl.cell(ri, ci).text = str(val)
        style_table(tbl, [0.40, 2.70, 4.40, 1.60], header_size=9.5, body_size=8.5)
        text(s, 0.45, 4.80, 9.10, 0.40, [
            P([R("Detection sketches, required log fields and reference KQL for "
                 "every gap are in the ", size=9.5),
               R("Excel technique tracker", bold=True, color=_PURPLE, size=9.5),
               R(" delivered with this deck.", size=9.5)])])

    # ------------------------------------------------------- 7 · roadmap
    s = slide()
    chrome(s, "Improvement Roadmap",
           f"{len(roadmap.get('short', []))} of {gap_total} gaps are buildable "
           "on logs you already collect — sequencing is the whole game")
    buckets = [
        ("NOW · 0–3 months", _TEAL, _MINT, _GREEN_D, roadmap.get("short", []),
         "telemetry already onboarded — build the detection now"),
        ("NEXT · 3–9 months", _LAVENDER, _CARD, _PURPLE, roadmap.get("mid", []),
         "onboard telemetry from tooling you already own first"),
        ("LATER · 9–18 months", _MAGENTA, _ROSEBG, "B02830", roadmap.get("long", []),
         "needs a new telemetry capability — plan deliberately"),
    ]
    for i, (head, bar, fillc, hc, items, desc) in enumerate(buckets):
        x = 0.45 + i * 3.10
        card(s, x, 1.25, 2.95, 2.55, bar, fillc)
        text(s, x + 0.15, 1.33, 2.65, 0.26,
             [P([R(f"{head}  ·  {len(items)}", bold=True, color=hc, size=11)])])
        paras = [P([R(desc, color=_GREY, size=8.5)], space_after=5)]
        for g in items[:4]:
            paras.append(P([R(f"{g.get('technique_id')} ", bold=True,
                              color=_PURPLE, size=8.5),
                            R(str(g.get("name"))[:34], size=8.5)], space_after=2))
        if len(items) > 4:
            paras.append(P([R(f"+ {len(items) - 4} more in the tracker",
                              color=_GREY, size=8)]))
        text(s, x + 0.15, 1.66, 2.65, 2.05, paras)
    if never_count:
        info_card(s, 0.45, 4.00, 9.10, 1.00, _AMBER, _CARD,
                  "One caveat before committing build dates", "8A5A10",
                  [P([R("“Buildable now” means the log source is declared as "
                        "onboarded — ", size=9),
                      R(f"{never_count} of {total_rules} rules found no events "
                        "when last validated", bold=True, color=_AMBER, size=9),
                      R(", so verify source health first (parsing, normalization, "
                        "recent events), then commit dates.", size=9)])])

    # ---------------------------------------------------- 8 · next steps
    s = slide()
    chrome(s, "Recommended Next Steps",
           "Concrete, owned actions — each one moves the next re-run's number")
    steps = []
    if never_count:
        steps.append(("Validate the silent rules",
                      f"{never_count} rules found no events when last validated — "
                      "replay test data or trigger drills; proves coverage without "
                      "writing a single new rule.", _TEAL))
    if gaps:
        steps.append((f"Build the top {min(5, len(gaps))} detections",
                      "Highest-priority gaps, ranked for you — start with the "
                      "short-term bucket.", _TEAL))
    if counts.get("unmapped"):
        steps.append(("Map or retire the unmapped rules",
                      f"{counts['unmapped']} rules map to no ATT&CK technique and "
                      "count toward nothing — map them or document why not.",
                      _LAVENDER))
    if roadmap.get("long"):
        steps.append(("Plan new telemetry deliberately",
                      f"{len(roadmap['long'])} gaps need a capability you don't "
                      "collect today — bundle them into an onboarding plan.",
                      _LAVENDER))
    steps.append(("Re-run to trend",
                  f"Re-assess quarterly against this {overall.get('strict_pct')}% "
                  "baseline — same method, same math, comparable every time.",
                  _MAGENTA))
    for i, (head, sub, color) in enumerate(steps[:6]):
        x = 0.45 if i < 3 else 5.08
        y = 1.25 + (i % 3) * 1.32
        card(s, x, y, 4.50, 1.20, color)
        text(s, x + 0.15, y + 0.10, 0.55, 0.60,
             [P([R(str(i + 1), bold=True, color=color, size=24)])])
        text(s, x + 0.72, y + 0.10, 3.65, 0.30,
             [P([R(head, bold=True, color=_PURPLE, size=10.5)])])
        text(s, x + 0.72, y + 0.42, 3.65, 0.72, [P([R(sub, color=_GREY, size=8.5)])])

    # ------------------------------------------------------- 9 · closing
    s = slide()
    rect(s, 0, 0, 10.0, 5.625, _PURPLE)
    rect(s, -1.60, 1.40, 6.00, 6.00, _PURPLE2, MSO_SHAPE.OVAL)
    rect(s, 7.10, -1.20, 5.50, 5.50, _MAGENTA, MSO_SHAPE.OVAL)
    text(s, 0.90, 2.00, 8.20, 1.00,
         [P([R("Thank you · Q&A", bold=True, color="FFFFFF", size=34)])])
    text(s, 0.90, 3.10, 8.20, 1.10, [
        P([R(footer_text, bold=True, color=_TEAL, size=13)]),
        P([R("Full detail: the spreadsheet technique tracker, the PDF report "
             "and the ATT&CK Navigator layers.", color=_LILAC, size=11)]),
    ])

    cp = prs.core_properties
    cp.title = f"{assessment.name} — MITRE ATT&CK Coverage Assessment"
    cp.author = display_name
    cp.last_modified_by = display_name

    buf = io.BytesIO()
    prs.save(buf)
    return buf.getvalue()
