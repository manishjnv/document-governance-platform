"""One-slide management pitch: automated vs manual MITRE ATT&CK assessment.

Run: python scripts/build_mitre_value_slide.py [out.pptx]
Out: docs/planning/MITRE_AUTOMATION_VALUE_SLIDE.pptx

Manual effort is an ASSUMPTION (owner-approved 2026-09-21), not a measurement;
change the constants below and re-run. Product facts come from
docs/planning/MITRE_MODULE_REFERENCE.md. Palette copied from
apps/api/app/mitre/report_pptx.py (helpers there are nested closures).
"""

import re
import sys
from pathlib import Path

from pptx import Presentation
from pptx.dml.color import RGBColor
from pptx.enum.shapes import MSO_SHAPE
from pptx.enum.text import MSO_ANCHOR, PP_ALIGN
from pptx.util import Inches, Pt

# ---- baseline (edit these) -------------------------------------------------
USE_CASES = 300
MIN_PER_UC = 30      # manual: map + validate + log-source check, per use case
REPORT_HRS = 50      # manual: gap analysis, heatmap, tracker, deck
RATE = 50            # USD/hr blended
AUTO_HRS = 4         # automated: upload + review low-confidence tags (estimate)
RUNS_PER_YEAR = 10

MAP_HRS = USE_CASES * MIN_PER_UC // 60
MANUAL_HRS = MAP_HRS + REPORT_HRS
MANUAL_DAYS = MANUAL_HRS // 8
MANUAL_COST = MANUAL_HRS * RATE
AUTO_COST = AUTO_HRS * RATE
SAVED_HRS = MANUAL_HRS - AUTO_HRS
SAVED_COST = MANUAL_COST - AUTO_COST
SAVED_PCT = round(100 * SAVED_HRS / MANUAL_HRS)
YEAR_SAVED_HRS = SAVED_HRS * RUNS_PER_YEAR
YEAR_SAVED_COST = SAVED_COST * RUNS_PER_YEAR

PURPLE, PURPLE_NUM, LAVENDER = "341954", "4A2A73", "7370A7"
MAGENTA, TEAL, GREEN_D, RED_D = "B71D6B", "00A98B", "1E7B4D", "B02830"
CARD, MINT, ROSEBG, GREY, WHITE = "F3F0F7", "E7F5F1", "FCEEF3", "404040", "FFFFFF"
FONT = "Tenorite"

OUT = Path(sys.argv[1]) if len(sys.argv) > 1 else (
    Path(__file__).resolve().parents[1] / "docs/planning/MITRE_AUTOMATION_VALUE_SLIDE.pptx")


def rgb(h):
    return RGBColor.from_string(h)


def rect(s, x, y, w, h, fill, shape=MSO_SHAPE.RECTANGLE):
    r = s.shapes.add_shape(shape, Inches(x), Inches(y), Inches(w), Inches(h))
    r.fill.solid()
    r.fill.fore_color.rgb = rgb(fill)
    r.line.fill.background()
    r.shadow.inherit = False
    return r


def text(s, x, y, w, h, lines, size=10.5, color=GREY, bold=False, hi=MAGENTA,
         align=PP_ALIGN.LEFT, anchor=MSO_ANCHOR.TOP, gap=2):
    """lines: str or list of str; **x** marks a bold highlighted run."""
    tf = s.shapes.add_textbox(Inches(x), Inches(y), Inches(w), Inches(h)).text_frame
    tf.word_wrap = True
    tf.vertical_anchor = anchor
    tf.margin_left = tf.margin_right = Inches(0.06)
    tf.margin_top = tf.margin_bottom = Inches(0.03)
    for i, line in enumerate([lines] if isinstance(lines, str) else lines):
        p = tf.paragraphs[0] if i == 0 else tf.add_paragraph()
        p.alignment = align
        p.space_after = Pt(gap)
        for j, part in enumerate(re.split(r"\*\*(.+?)\*\*", line)):
            if not part:
                continue
            r = p.add_run()
            r.text = part
            r.font.name, r.font.size = FONT, Pt(size)
            r.font.bold = bold or j % 2 == 1
            r.font.color.rgb = rgb(hi if j % 2 == 1 else color)


def card(s, x, y, w, h, title, lines, accent=TEAL, fill=CARD, size=10.5):
    rect(s, x, y, w, h, fill)
    rect(s, x, y, 0.07, h, accent)
    text(s, x + 0.12, y + 0.05, w - 0.2, 0.3, title, 12, PURPLE, bold=True)
    text(s, x + 0.12, y + 0.37, w - 0.2, h - 0.4, lines, size)


def stat_tile(s, x, y, w, h, big, label, color):
    rect(s, x, y, w, h, CARD)
    rect(s, x, y, w, 0.06, color)
    text(s, x, y + 0.1, w, 0.55, big, 25, color, bold=True, align=PP_ALIGN.CENTER)
    text(s, x, y + 0.64, w, 0.35, label, 10, GREY, align=PP_ALIGN.CENTER)


def build():
    prs = Presentation()
    prs.slide_width, prs.slide_height = Inches(13.333), Inches(7.5)
    s = prs.slides.add_slide(prs.slide_layouts[6])

    # title bar
    rect(s, 0, 0, 13.333, 0.95, PURPLE)
    rect(s, 0, 0.95, 13.333, 0.05, TEAL)
    text(s, 0.35, 0.08, 12.6, 0.5,
         f"Automated MITRE ATT&CK Coverage Assessment: {USE_CASES} use cases in half a day, not {MANUAL_DAYS // 5} weeks",
         21, WHITE, bold=True)
    text(s, 0.35, 0.55, 12.6, 0.35,
         "ScopeSense MITRE module  |  rule list in, management deck out  |  same result every time, no ATT&CK expert needed",
         11.5, "D8D2E4")

    # three headline tiles, each one is worked out in the centre panel
    tiles = [
        (f"{MANUAL_HRS} hrs → {AUTO_HRS} hrs", "effort for one assessment", MAGENTA),
        (f"${MANUAL_COST:,} → ${AUTO_COST}", "cost for one assessment", GREEN_D),
        ("2-3 experts → 1 analyst", "people needed", PURPLE_NUM),
    ]
    tw = 4.12
    for i, (big, label, color) in enumerate(tiles):
        stat_tile(s, 0.35 + i * (tw + 0.135), 1.12, tw, 1.0, big, label, color)

    # left: problem (words, no statistics)
    card(s, 0.35, 2.25, 3.55, 3.2, "The problem today", [
        "• Every use case is mapped to MITRE ATT&CK **by hand** in a spreadsheet",
        "• Gap list, heatmap, tracker and deck are **rebuilt by hand** for every client",
        "• Needs **skilled L2/L3 engineers**, who are scarce and costly",
        "• Two analysts give **two different answers**",
        "• **Out of date** as soon as rules change, so it is rarely repeated",
    ], accent=MAGENTA, fill=ROSEBG, size=11)

    # centre: the sum, shown step by step
    cx, cw = 4.05, 5.75
    card(s, cx, 2.25, cw, 1.62, "Manual: how we get 200 hrs and $10,000", [
        f"• {USE_CASES} use cases × {MIN_PER_UC} min each = **{MAP_HRS} hrs** of mapping",
        f"• Gap list, heatmap, tracker and deck by hand = **{REPORT_HRS} hrs**",
        f"• Total = **{MANUAL_HRS} hrs** = {MANUAL_DAYS} working days (about {MANUAL_DAYS // 5} weeks)",
        f"• {MANUAL_HRS} hrs × ${RATE} per hour = **${MANUAL_COST:,}**",
    ], accent=MAGENTA, fill=ROSEBG, size=11)
    card(s, cx, 3.95, cw, 1.1, "Automated: how we get 4 hrs and $200", [
        "• Tool does mapping, scoring, gap list and deck in **minutes**",
        f"• 1 analyst uploads the list and checks the result = **{AUTO_HRS} hrs** (half a day)",
        f"• {AUTO_HRS} hrs × ${RATE} per hour = **${AUTO_COST}**",
    ], accent=TEAL, fill=MINT, size=11)
    rect(s, cx, 5.12, cw, 0.33, PURPLE)
    text(s, cx, 5.12, cw, 0.33,
         f"Saved each time:  {MANUAL_HRS} − {AUTO_HRS} = **{SAVED_HRS} hrs**   |   ${MANUAL_COST:,} − ${AUTO_COST} = **${SAVED_COST:,}**   |   **{SAVED_PCT}%** less",
         11, WHITE, hi="7FE3D0", align=PP_ALIGN.CENTER, anchor=MSO_ANCHOR.MIDDLE)

    # right: no skilled staff (words only)
    card(s, 9.95, 2.25, 3.03, 3.2, "Why no skilled staff is needed", [
        "• Upload the rule list as **Excel, CSV, PDF or Word**, or connect **Sentinel / Splunk**",
        "• Tool finds the right columns and **maps each use case** to ATT&CK itself",
        "• Scores are **calculated by fixed code, not guessed by AI**",
        "• Only **unsure mappings** are shown to the analyst to confirm",
        "• **Deck, Excel tracker and PDF** come out ready to share",
    ], accent=TEAL, fill=MINT, size=11)

    # how it works
    text(s, 0.35, 5.55, 3, 0.28, "How it works", 12, PURPLE, bold=True)
    steps = [("1  Upload / connect", "Rule list or SIEM"), ("2  Auto-map", "Use case to ATT&CK"),
             ("3  Score", "Coverage by tactic"), ("4  Gaps + roadmap", "What to fix first"),
             ("5  Deliverables", "Deck, Excel, PDF")]
    sw = 1.82
    for i, (head, sub) in enumerate(steps):
        x = 0.35 + i * (sw + 0.1)
        rect(s, x, 5.85, sw, 0.78, PURPLE if i % 2 == 0 else PURPLE_NUM)
        text(s, x, 5.9, sw, 0.3, head, 10.5, WHITE, bold=True, align=PP_ALIGN.CENTER)
        text(s, x, 6.22, sw, 0.35, sub, 9.5, "D8D2E4", align=PP_ALIGN.CENTER)

    # yearly view: plain multiplication
    rect(s, 9.95, 5.55, 3.03, 1.08, PURPLE)
    text(s, 10.02, 5.58, 2.9, 0.28, f"If we do {RUNS_PER_YEAR} assessments a year", 11.5, WHITE, bold=True)
    text(s, 10.02, 5.87, 2.9, 0.75, [
        f"• {RUNS_PER_YEAR} × ${SAVED_COST:,} = **${YEAR_SAVED_COST:,}** saved",
        f"• {RUNS_PER_YEAR} × {SAVED_HRS} hrs = **{YEAR_SAVED_HRS:,} hrs**, about 1 person's full year",
    ], 10, WHITE, hi="7FE3D0", gap=1)

    # proof + inputs
    rect(s, 0.35, 6.75, 12.63, 0.32, CARD)
    text(s, 0.4, 6.76, 12.5, 0.3,
         "Already proven: used on a real client assessment of **371 SIEM rules**. Coverage score, gap list, roadmap and deck all came from the tool.",
         10, GREY, anchor=MSO_ANCHOR.MIDDLE)
    text(s, 0.35, 7.1, 12.63, 0.3,
         f"Only 4 inputs drive every number: {MIN_PER_UC} min per use case, {REPORT_HRS} hrs of reporting, {AUTO_HRS} hrs of analyst review, ${RATE} per hour. "
         f"These are our estimates. Change them to your own figures and the savings recalculate.",
         9, "808080")

    s.notes_slide.notes_text_frame.text = (
        "WHERE EVERY NUMBER COMES FROM\n"
        f"- {USE_CASES} use cases: a typical SOC use-case library size.\n"
        f"- {MIN_PER_UC} min each: time for an engineer to read one rule, pick the ATT&CK technique and check the log source. Our estimate.\n"
        f"- {USE_CASES} x {MIN_PER_UC} min = {MAP_HRS} hrs.\n"
        f"- {REPORT_HRS} hrs: gap analysis, heatmap, tracker and slide deck built by hand (about 1 week). Our estimate.\n"
        f"- {MAP_HRS} + {REPORT_HRS} = {MANUAL_HRS} hrs = {MANUAL_DAYS} working days at 8 hrs a day.\n"
        f"- ${RATE} per hour: blended rate for a senior SOC / detection engineer. {MANUAL_HRS} x {RATE} = ${MANUAL_COST:,}.\n"
        f"- {AUTO_HRS} hrs: half a day for one analyst to upload the list and check the mappings the tool was unsure about. Our estimate. {AUTO_HRS} x {RATE} = ${AUTO_COST}.\n"
        f"- Saving: {MANUAL_HRS} - {AUTO_HRS} = {SAVED_HRS} hrs; ${MANUAL_COST:,} - ${AUTO_COST} = ${SAVED_COST:,}; {SAVED_HRS}/{MANUAL_HRS} = {SAVED_PCT}%.\n"
        f"- Yearly: {RUNS_PER_YEAR} assessments x the saving above. {YEAR_SAVED_HRS:,} hrs is roughly one person's working year.\n"
        "- 371 SIEM rules: size of the first real client assessment done with the tool.\n"
        "- AI running cost is a few cents per assessment, so it is left out of the sum.\n"
        "If challenged on 30 min or 50 hrs: ask the audience for their own figure; even at half the manual effort the saving is above 95%."
    )

    OUT.parent.mkdir(parents=True, exist_ok=True)
    prs.save(OUT)
    print(f"wrote {OUT}")


def build_xlsx():
    """Justification workbook: every number (live formulas) and every point on the slide."""
    from openpyxl import Workbook
    from openpyxl.styles import Alignment, Font, PatternFill
    from openpyxl.utils import get_column_letter

    wb = Workbook()
    ws = wb.active
    ws.title = "Numbers"
    # key, label, value-or-formula, how calculated, short reason, type
    rows = [
        ("uc", "Use cases assessed", USE_CASES, "Input",
         "Typical size of a SOC use-case library. Replace with the client's real count.", "Input"),
        ("min", "Minutes per use case (manual)", MIN_PER_UC, "Input",
         "Engineer reads the rule logic, searches 800+ ATT&CK techniques and sub-techniques, checks the log source, "
         "writes it in the sheet. About 30 min each on average.", "Estimate"),
        ("map", "Manual mapping hours", "={uc}*{min}/60", "Use cases x minutes / 60",
         "300 x 30 min = 9,000 min = 150 hrs.", "Calculated"),
        ("rep", "Manual reporting hours", REPORT_HRS, "Input",
         "Gap analysis ~2 days, heatmap ~1 day, tracker ~1 day, slide deck ~2 days = about 6 days = 50 hrs. "
         "All built by hand.", "Estimate"),
        ("man", "Total manual effort (hrs)", "={map}+{rep}", "Mapping + reporting", "150 + 50 = 200 hrs.", "Calculated"),
        ("days", "Manual effort (person-days)", "={man}/8", "Total hrs / 8 hrs per day",
         "200 / 8 = 25 person-days.", "Calculated"),
        ("weeks", "Manual elapsed time (weeks)", "={days}/5", "Person-days / 5 days per week",
         "25 days = 5 weeks of one person. With 2-3 people it still takes about 5 weeks because they do it "
         "alongside daily SOC work.", "Calculated"),
        ("rate", "Cost per hour (USD)", RATE, "Input",
         "Blended rate for a senior SOC / detection engineer. Replace with your own rate card.", "Estimate"),
        ("mcost", "Manual cost per assessment", "={man}*{rate}", "Total manual hrs x rate",
         "200 hrs x $50 = $10,000.", "Calculated"),
        ("auto", "Automated effort (analyst hrs)", AUTO_HRS, "Input",
         "Upload and set scope ~0.5 hr, confirm the mappings the tool was unsure about ~2.5 hrs, read through "
         "the deck ~1 hr = 4 hrs.", "Estimate"),
        ("acost", "Automated cost per assessment", "={auto}*{rate}", "Analyst hrs x rate",
         "4 hrs x $50 = $200. AI running cost is a few cents per run, so it is left out.", "Calculated"),
        ("shrs", "Hours saved per assessment", "={man}-{auto}", "Manual hrs - automated hrs",
         "200 - 4 = 196 hrs.", "Calculated"),
        ("scost", "Cost saved per assessment", "={mcost}-{acost}", "Manual cost - automated cost",
         "$10,000 - $200 = $9,800.", "Calculated"),
        ("pct", "Saving %", "={shrs}/{man}", "Hours saved / manual hrs",
         "196 / 200 = 98%. Same % for cost because both use the same rate.", "Calculated"),
        ("runs", "Assessments per year", RUNS_PER_YEAR, "Input",
         "Illustrative only, for example 10 clients once a year. Replace with your pipeline.", "Input"),
        ("ycost", "Cost saved per year", "={scost}*{runs}", "Saving per assessment x assessments",
         "10 x $9,800 = $98,000.", "Calculated"),
        ("yhrs", "Hours saved per year", "={shrs}*{runs}", "Hours saved x assessments",
         "10 x 196 = 1,960 hrs. One person works about 245 days x 8 hrs = 1,960 hrs a year, so this is about "
         "1 person's full year.", "Calculated"),
        (None, "People needed: 2-3 experts to 1 analyst", "2-3 to 1", "Not a formula",
         "Manual work is normally split: one maps, one reviews, one builds the report, all L2/L3. With the tool "
         "one analyst uploads and confirms; ATT&CK knowledge sits in the tool.", "Estimate"),
        (None, "Tool run time: 'minutes'", "minutes", "Not a formula",
         "The run is an automated background job. Not yet stopwatch-timed: time one real run before presenting "
         "and put the figure here.", "To be measured"),
        (None, "371 SIEM rules (proof line)", 371, "Fact",
         "Size of the first real client assessment done end to end with the tool. Client name withheld.", "Fact"),
    ]
    ws.append(["Justification of every number on the MITRE automation slide. "
               "Change the yellow cells; everything else recalculates."])
    ws.append(["#", "Number on the slide", "Value", "How it is calculated", "Short reason / justification", "Type"])
    first = 3
    ref = {k: f"C{first + i}" for i, (k, *_) in enumerate(rows) if k}
    for i, (k, label, val, how, why, typ) in enumerate(rows):
        is_formula = isinstance(val, str) and val.startswith("=")
        ws.append([i + 1, label, val.format(**ref) if is_formula else val, how, why, typ])
        c = ws.cell(row=first + i, column=3)
        if how == "Input":
            c.fill = PatternFill("solid", fgColor="FFF2CC")
        if k in ("rate", "mcost", "acost", "scost", "ycost"):
            c.number_format = '"$"#,##0'
        elif k == "pct":
            c.number_format = "0%"
        else:
            c.number_format = "#,##0"
        c.alignment = Alignment(horizontal="right")

    wp = wb.create_sheet("Points")
    wp.append(["Justification of every statement on the slide."])
    wp.append(["Section", "Point on the slide", "Short reason", "Where it comes from"])
    doc = "docs/planning/MITRE_MODULE_REFERENCE.md"
    for r in [
        ("Title", "300 use cases in half a day, not 5 weeks",
         "4 hrs of analyst time against 25 person-days of manual work.", "Numbers sheet, items 6, 7 and 10"),
        ("Title", "Same result every time",
         "Scores are calculated by code on a fixed ATT&CK version, so the same input gives the same output.", doc),
        ("Problem", "Mapped by hand in a spreadsheet",
         "This is how most SOC teams do ATT&CK mapping today: one row per use case, technique typed in by an engineer.",
         "Common practice; our own first engagement started this way"),
        ("Problem", "Gap list, heatmap, tracker and deck rebuilt by hand for every client",
         "Nothing is reusable between clients because each rule list is different.",
         "Our first client deck was hand-built before the tool could generate it"),
        ("Problem", "Needs skilled L2/L3 engineers",
         "Correct mapping needs someone who knows both the detection logic and the ATT&CK framework.", "Common practice"),
        ("Problem", "Two analysts give two different answers",
         "Mapping is a judgement call; there is no fixed rule, so results depend on who did it.", "Common practice"),
        ("Problem", "Out of date as soon as rules change",
         "A spreadsheet is a snapshot. Rules are added and tuned every month, and nobody redoes 200 hrs of work.",
         "Follows from the effort figure"),
        ("No skilled staff", "Upload Excel, CSV, PDF or Word, or connect Sentinel / Splunk",
         "All four file types and both connectors are built into the tool. Note: real client runs so far used file upload; "
         "the Splunk connector has not yet been run on a live client.", doc),
        ("No skilled staff", "Tool finds the right columns and maps each use case itself",
         "It recognises common column names on its own, maps by known technique names first and uses AI only for the rest.", doc),
        ("No skilled staff", "Scores calculated by fixed code, not guessed by AI",
         "Every percentage and count comes from code. AI only suggests a mapping and writes summary text; "
         "it never produces a number.", doc),
        ("No skilled staff", "Only unsure mappings shown to the analyst",
         "Each AI mapping carries a confidence score; low-confidence ones are left for a person to confirm. "
         "Tags the client already gave are never changed.", doc),
        ("No skilled staff", "Deck, Excel tracker and PDF come out ready",
         "The tool generates a slide deck, an Excel gap tracker and a PDF report from the same scored data.", doc),
        ("How it works", "1 Upload / connect",
         "Rule list file or SIEM connection is the only input. No raw logs or personal data are taken.", doc),
        ("How it works", "2 Auto-map", "Each use case is linked to ATT&CK techniques.", doc),
        ("How it works", "3 Score", "Coverage is worked out per tactic and per technique.", doc),
        ("How it works", "4 Gaps + roadmap",
         "Missing techniques are ranked and grouped into short, mid and long term fixes.", doc),
        ("How it works", "5 Deliverables", "Deck, Excel and PDF are downloaded from the same run.", doc),
        ("Yearly box", "If we do 10 assessments a year",
         "Simple multiplication of the per-assessment saving. 10 is an example, not a forecast.",
         "Numbers sheet, items 15 to 17"),
        ("Proof line", "Used on a real client assessment of 371 SIEM rules",
         "The tool has already produced a full client deliverable, so this is not a prototype.",
         "Internal engagement record; client name withheld"),
        ("Footer", "Only 4 inputs drive every number",
         "30 min, 50 hrs, 4 hrs and $50 are our estimates. Everything else is arithmetic on them.",
         "Numbers sheet, yellow cells"),
    ]:
        wp.append(list(r))

    for sh, widths in ((ws, (5, 40, 14, 32, 90, 16)), (wp, (18, 52, 90, 48))):
        for i, w in enumerate(widths, 1):
            sh.column_dimensions[get_column_letter(i)].width = w
        for row in sh.iter_rows(min_row=2):
            for c in row:
                c.alignment = Alignment(wrap_text=True, vertical="top", horizontal=c.alignment.horizontal)
        sh["A1"].font = Font(bold=True, size=12, color=PURPLE)
        for c in sh[2]:
            c.font = Font(bold=True, color=WHITE)
            c.fill = PatternFill("solid", fgColor=PURPLE)
        sh.freeze_panes = "A3"

    out = OUT.with_name("MITRE_AUTOMATION_VALUE_SLIDE_JUSTIFICATION.xlsx")
    wb.save(out)
    print(f"wrote {out}")


if __name__ == "__main__":
    # ponytail: self-check on the default baseline only
    if (USE_CASES, MIN_PER_UC, REPORT_HRS, RATE, AUTO_HRS, RUNS_PER_YEAR) == (300, 30, 50, 50, 4, 10):
        assert (MANUAL_HRS, MANUAL_DAYS, MANUAL_COST, SAVED_PCT, SAVED_COST) == (200, 25, 10000, 98, 9800)
        assert (YEAR_SAVED_HRS, YEAR_SAVED_COST) == (1960, 98000)
        assert round(100 * (100 - AUTO_HRS) / 100) > 95  # the "half the manual effort" line in the notes
    build_xlsx()
    build()
