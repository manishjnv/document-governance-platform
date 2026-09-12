"""Tokens + components sheet: the design system on one artboard, with live primitives."""
from dc import T, screen, btn, chip, dot_chip, kpi, tabs, panel, sheet, dialog, dropzone, filerow, icon, TOKENS, esc, skel, alert

STEM = "Main"  # the entry artboard: the design system sheet
PAGE, TITLE, ORDER = "system", "Design system", 0


def _lum(hexv):
    r, g, b = [int(hexv[i:i + 2], 16) / 255 for i in (1, 3, 5)]
    f = lambda c: c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4
    return 0.2126 * f(r) + 0.7152 * f(g) + 0.0722 * f(b)


def ratio(a, b):
    la, lb = _lum(a), _lum(b)
    hi, lo = max(la, lb), min(la, lb)
    return (hi + 0.05) / (lo + 0.05)


def swatch(name, hexv, on="#FAF9F6", text=None):
    r = ratio(text or hexv, on)
    return ('<div class="card" style="padding:10px 12px;box-shadow:none"><div class="row" style="gap:10px"><span style="width:34px;height:34px;border-radius:8px;background:%s;border:1px solid var(--line);flex:none"></span>'
            '<div><div style="font-weight:600;font-size:13px">%s</div><div class="mono faint">%s · %.1f:1 on %s</div></div></div></div>') % (hexv, name, hexv, r, "paper" if on == "#FAF9F6" else "card")


SWATCHES = "".join([
    swatch("Ink (primary text)", TOKENS["ink"]), swatch("Ink 2 (secondary)", TOKENS["ink2"]), swatch("Ink 3 (labels)", TOKENS["ink3"]),
    swatch("Accent", TOKENS["accent"]), swatch("Critical", TOKENS["crit"], TOKENS["crit_soft"]), swatch("High", TOKENS["high"], TOKENS["high_soft"]),
    swatch("Medium", TOKENS["med"], TOKENS["med_soft"]), swatch("Low", TOKENS["low"], TOKENS["low_soft"]), swatch("Info", TOKENS["info"], TOKENS["info_soft"]),
    swatch("OK / covered", TOKENS["ok"], TOKENS["ok_soft"]), swatch("Violet (threat)", TOKENS["violet"], TOKENS["violet_soft"]),
])

TYPE = """
<div class="stack" style="gap:10px">
<div style="font-size:28px;font-weight:600;letter-spacing:-.02em">Page title 28 · IBM Plex Sans 600</div>
<div style="font-size:24px;font-weight:600">Screen heading 24</div>
<div style="font-size:18px;font-weight:600">Section heading 18</div>
<div style="font-size:16px">Lead 16 · the quick brown fox jumps over the lazy dog</div>
<div style="font-size:14px">Body 14 · every finding is pinned to the sentence it came from. Numbers use tabular figures: <span class="num">1,234 · 56.7% · 09:41</span></div>
<div style="font-size:13px" class="sub">Dense 13 · table cells and secondary copy in ink 2</div>
<div class="lbl">Label 11 uppercase in ink 3</div>
<div class="mono">Mono 12 · T1078.004 · app/routes/session.js:53-58 · c5cb68a</div>
</div>"""

BUTTONS = T("""
<div class="row wrap" style="gap:8px">[[a]][[b]][[c]][[d]][[e]][[f]]</div>
<div class="row wrap" style="gap:8px;margin-top:8px">[[g]][[h]][[i]][[j]]</div>""",
            a=btn("Primary", "primary"), b=btn("Outline"), c=btn("Ghost", "ghost"), d=btn("Destructive", "danger"), e=btn("Link", "link"), f=btn("Disabled", "primary", disabled=True),
            g=btn("Small", "primary", size="sm"), h=btn("With icon", "", "download"), i=btn("Large", "primary", size="lg"), j=btn("", "", "more", attrs='aria-label="Icon button"') .replace('class="btn "', 'class="btn icon"'))

CHIPS = T("""
<div class="row wrap" style="gap:6px">[[c1]][[c2]][[c3]][[c4]][[c5]][[c6]][[c7]][[c8]][[c9]][[c10]]</div>
<div class="row wrap" style="gap:14px;margin-top:10px">[[d1]][[d2]][[d3]][[d4]]</div>""",
            c1=chip("Critical", "crit"), c2=chip("High", "high"), c3=chip("Medium", "med"), c4=chip("Low", "low"), c5=chip("Info", "info"),
            c6=chip("Completed", "ok"), c7=chip("Running", "info"), c8=chip("Not run yet", "grey"), c9=chip("Demo", "info", tip="Shared sample — read-only for everyone"), c10=chip("PRO", "blue"),
            d1=dot_chip("P1 · Critical", "crit"), d2=dot_chip("Build now", "ok"), d3=dot_chip("Onboard logs first", "info"), d4=dot_chip("Healthy", "ok"))

INPUTS = T("""
<div class="grid g3" style="gap:10px">
 <div><label class="label">Text</label><input class="input" style="width:100%" placeholder="e.g. Q3 SOC coverage"></div>
 <div><label class="label">Select</label><select class="select" style="width:100%"><option>All statuses</option><option>Completed</option></select></div>
 <div><label class="label">Search</label><div class="search">[[s]]<input class="input" placeholder="Search all documents..."></div></div>
 <div><label class="label">Number</label><input class="input" type="number" value="5" min="0" max="1000" style="width:100px"></div>
 <div><label class="label">Checkbox</label><label class="row" style="gap:8px;font-size:13px"><input type="checkbox" checked> Count disabled rules as coverage</label></div>
 <div><label class="label">Textarea</label><textarea class="input" rows="2" style="width:100%" placeholder="e.g. Annual detection-coverage review"></textarea></div>
</div>""", s=icon("search", 15))

DROP = T("""<div class="grid g2" style="gap:10px"><div>[[dz]]<sc-if value="{{drop.demo.has}}" hint-placeholder-val="{{false}}"><div style="margin-top:8px">[[fr]]</div></sc-if></div>
<div class="stack"><div class="lbl">Alert patterns</div>[[a1]][[a2]][[a3]][[a4]]<p class="err-line" role="alert">Could not rename the review</p></div></div>""",
          dz=dropzone("demo", "Drag &amp; drop or click to select", "xlsx, xls, csv, pdf or docx · up to 50MB", "Detection rules export: choose a file or drag it here"),
          fr=filerow("demo", "drop.demo.removeAria"),
          a1=alert("err", "Failed to load assessments"), a2=alert("warn", "<b>Scan degraded.</b> Model provider rate-limited during stage s7; findings after that stage may be missing.", "dismissWarn"),
          a3=alert("ok", "Document uploaded successfully: SOC_SOW_Testing.docx"), a4=alert("blue", "<b>sample_rfp_v2.docx</b> looks like it could be a new version of <b>sample_rfp.docx</b> (v1) -- link as v2? <span style='color:var(--accent)'>(91% similar)</span>"))

TABLE = """
<table class="tbl cards"><thead><tr><th>Document</th><th>Type</th><th class="r">Risk score</th><th>Status</th><th class="r">Actions</th></tr></thead>
<tbody><tr><td data-th="Document"><b>SOC_SOW_Testing.docx</b><div class="faint" style="font-size:11px">v6 · 6 versions</div></td><td data-th="Type">%s</td><td data-th="Risk score" class="r num">10 <span style="color:var(--ok);font-size:12px;font-weight:600">▼2</span></td><td data-th="Status">%s</td><td data-th="Actions" class="r">%s</td></tr>
<tr class="sel"><td data-th="Document"><b>rfp_sample.pdf</b><div class="faint" style="font-size:11px">v1</div></td><td data-th="Type">%s</td><td data-th="Risk score" class="r num">25</td><td data-th="Status">%s</td><td data-th="Actions" class="r">%s</td></tr></tbody></table>
<p class="faint" style="font-size:12px;margin-top:6px">Selected row tint · hover tint · on phones each row becomes a card with the header as the label.</p>""" % (
    chip("SOW", "grey", xs=True), dot_chip("Reviewed", "ok"), btn("Review", "", size="sm"), chip("RFP", "blue", xs=True), dot_chip("Reviewed", "ok"), btn("Review", "", size="sm"))

KPIS = T("""<div class="grid g4">[[a]][[b]][[c]][[d]]</div>""",
         a=kpi("Coverage", "14.4%", "132 of 918 applicable", "accent", tip="Strict coverage. Click to see the techniques behind this number.", click=True),
         b=kpi("Critical", "6", "confirm these first", "crit", tip="Critical-severity findings. Click to filter the table.", click=True),
         c=kpi("Open findings", "896", "across 15 reviews"), d=kpi("Sign-ins", "23", "this week · 37 in 30 days"))

OVERLAYS = T("""
<div class="row wrap" style="gap:8px">[[b1]][[b2]][[b3]]</div>
<div class="row wrap" style="gap:12px;margin-top:10px;font-size:12px" class="faint"><span class="tip" data-tip="Every chip, tile and icon button has one" style="border-bottom:1px dotted var(--ink3)">Hover me for a tooltip</span><span class="kbd">⌘K</span><span class="kbd">Esc</span></div>
<div style="margin-top:12px">[[tabs]]<div style="padding:12px 2px;font-size:13px" class="sub">[[p1]][[p2]][[p3]]</div></div>
<div class="grid g2" style="margin-top:12px"><div class="empty"><h3>No documents uploaded yet</h3><p class="sub" style="font-size:13px;margin-bottom:12px">Upload a SOW, Proposal, RFP or other document for review.</p>[[b4]]</div>
<div class="card" style="padding:14px">[[s1]][[s2]][[s3]]</div></div>""",
               b1=btn("Open a sheet", "primary", attrs='onClick="{{openDemoSheet}}"'), b2=btn("Open a dialog", "", attrs='onClick="{{openDemoDlg}}"'), b3=btn("Simulate busy", "", "loader", attrs='onClick="{{simBusy}}"').replace("Simulate busy", "{{busyLabel}}"),
               tabs=tabs("t", [("a", "Findings"), ("b", "Exploit chains (6)"), ("c", "Scan details")]),
               p1=panel("t", "a", "Findings tab content: a sortable register."), p2=panel("t", "b", "Exploit chains tab content: chain cards and the attack graph."), p3=panel("t", "c", "Scan details tab content: metrics and manifest."),
               b4=btn("Upload Your First Document", "primary", size="sm"), s1=skel("55%", "14px", "margin-bottom:8px"), s2=skel("90%", "12px", "margin-bottom:8px"), s3=skel("70%", "12px"))

APPBARS = T("""<div class="stack" style="position:relative;z-index:0">
<div class="appbar" style="position:relative;z-index:0;border-radius:8px">A new version is available. [[r]]</div>
<div class="install" style="position:relative;z-index:0;transform:none;width:100%;max-width:none;left:auto;bottom:auto"><span>Install ScopeWise for offline access</span><span class="row" style="gap:6px">[[i1]][[i2]]</span></div>
<a href="#" class="btn primary sm" style="align-self:flex-start">Skip to main content</a></div>""",
              r=btn("Reload", "", size="sm").replace('class="btn  sm"', 'class="btn sm"'), i1=btn("Install", "primary", size="sm"), i2=btn("Dismiss", "ghost", size="sm"))

BODY = T("""
<div data-screen="[[stem]]" data-ready="{{ready}}" onClick="{{root}}" style="padding:28px 32px 48px;max-width:1240px;margin:0 auto">
<div class="pagehead"><div><h1 style="font-size:28px">ScopeWise design system</h1><p class="sub" style="margin-top:4px">Calm light · IBM Plex Sans · darker ink · colour only where it carries meaning. Everything on this sheet is the real primitive used by every screen.</p></div></div>
<div class="grid g2" style="gap:16px">
 <div class="card"><div class="card-h"><h3>Type ramp</h3></div><div class="card-b">[[type]]</div></div>
 <div class="card"><div class="card-h"><h3>Colour and contrast</h3><span class="faint" style="font-size:12px">ratio vs. its background</span></div><div class="card-b grid g2" style="gap:8px">[[sw]]</div></div>
 <div class="card"><div class="card-h"><h3>Buttons</h3></div><div class="card-b">[[buttons]]</div></div>
 <div class="card"><div class="card-h"><h3>Chips and status</h3></div><div class="card-b">[[chips]]</div></div>
 <div class="card"><div class="card-h"><h3>Inputs</h3></div><div class="card-b">[[inputs]]</div></div>
 <div class="card"><div class="card-h"><h3>Dropzone and alerts</h3></div><div class="card-b">[[drop]]</div></div>
 <div class="card"><div class="card-h"><h3>Table</h3></div><div class="card-b" style="padding:0 0 10px">[[table]]</div></div>
 <div class="card"><div class="card-h"><h3>KPI tiles</h3></div><div class="card-b">[[kpis]]</div></div>
 <div class="card"><div class="card-h"><h3>Sheet, dialog, tabs, tooltip, empty, skeleton</h3></div><div class="card-b">[[overlays]]</div></div>
 <div class="card"><div class="card-h"><h3>App bars</h3></div><div class="card-b">[[appbars]]</div></div>
</div>
[[sheet]]
</div>""", type=TYPE, sw=SWATCHES, buttons=BUTTONS, chips=CHIPS, inputs=INPUTS, drop=DROP, table=TABLE, kpis=KPIS, overlays=OVERLAYS, appbars=APPBARS,
         sheet=sheet("demo", '<h2 style="font-size:16px">T1078 <span class="chip ok" style="margin-left:6px">Covered</span></h2><p class="sub" style="font-size:12px">Valid Accounts · Initial Access · Persistence</p>',
                     '<div class="stack" style="gap:12px"><div><div class="lbl">What is this?</div><p style="font-size:13px">Adversaries use existing accounts to get in and stay in. Attackers use this to blend into normal activity.</p></div><div><div class="lbl">Detection rules mapped here (2)</div><div class="card" style="padding:10px 12px;box-shadow:none;font-size:13px"><b>Rule 12 · Impossible travel sign-in</b><div class="faint" style="font-size:12px">Enabled · Tagged by you · confidence 1.0 · Entra sign-in logs</div></div></div><p class="sub" style="font-size:12px">Drag the left edge or press ← / → to resize. Width is shared by all panels and remembered.</p></div>',
                     btn("Prev", "", "chevron-left", "sm") + '<span class="num faint" style="font-size:12px">3 of 29</span>' + btn("Next", "", "chevron-right", "sm"), aria="Technique details")
         + dialog("demo", "Delete review", '<p>Delete "<b>Customer portal</b>"? This can\'t be undone.</p>', btn("Cancel", "", size="sm", attrs='onClick="{{dlg.demo.close}}"') + btn("Delete", "danger", size="sm", attrs='onClick="{{dlg.demo.close}}"'), 420))

VALS = r"""
return { t: self.tabVals('t', ['a','b','c']),
  sheets: { demo: self.sheetVals('demo', 448) }, dlg: { demo: self.dlgVals('demo') },
  drop: { demo: Object.assign(self.dropVals('demo', 'acme_sentinel_usecases_v2.xlsx', '0.41 MB'), { removeAria: 'Remove acme_sentinel_usecases_v2.xlsx' }) },
  openDemoSheet: (e) => { e.stopPropagation(); self.openSheet('demo', 1, 448); }, openDemoDlg: (e) => { e.stopPropagation(); self.openDlg('demo'); },
  busyLabel: self.busy('sim') ? 'Working…' : 'Simulate busy', simBusy: (e) => { e.stopPropagation(); self.runBusy('sim', 1200); },
  dismissWarn: () => {} };
"""

SHEET_OPEN = "document.querySelector('aside.sheet').style.transform.startsWith('translateX(0')"
SHEET_CLOSED = "!document.querySelector('aside.sheet').style.transform.startsWith('translateX(0')"
CLICKS = [
    {"text": "Open a sheet", "check": SHEET_OPEN},
    {"css": "aside.sheet .sheet-h .xbtn", "check": SHEET_CLOSED},
    {"text": "Open a dialog", "check": "document.querySelector('.dlg-ov').style.pointerEvents === 'auto'"},
    {"css": ".dlg-ov[style*='pointer-events: auto'] .dlg-f .btn", "check": "document.querySelector('.dlg-ov').style.pointerEvents === 'none'"},
    {"text": "Exploit chains (6)", "expect": "chain cards and the attack graph", "check": "document.querySelector('.tab.on').textContent.includes('Exploit chains')"},
    {"text": "Drag & drop or click to select", "check": "document.querySelector('.filerow') !== null"},
]


def build(phone=False):
    props = {"view": {"editor": None, "default": "default"}}
    html = screen(STEM + ("Phone" if phone else ""), BODY, VALS, {}, {"tab": {"t": "a"}}, props=props, phone=phone)
    return [(STEM + ("Phone" if phone else ""), html)]
