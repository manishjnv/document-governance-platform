"""/projects/[id] — Project detail. Source: inventory/sow.md §4."""
from dc import T, app_shell, screen, btn, icon, kpi, dth, dcell, states

STEM = "ProjectDetail"
PAGE, TITLE, ORDER = "sow", "Project detail", 40

DATA = {
    "project": {"name": "NovaRetail Software Solutions", "avg": 13, "critical": 7},
    "docs": [
        {"id": "d1", "filename": "SOC_SOW_Testing.docx", "type": "SOW", "score": 10, "uploaded": "24 Jul 2026", "ts": 20260724},
        {"id": "d2", "filename": "Master_Services_Agreement.docx", "type": "SOW", "score": 22, "uploaded": "20 Jul 2026", "ts": 20260720},
        {"id": "d3", "filename": "Statement_of_Work_Addendum.pdf", "type": None, "score": None, "uploaded": "15 Jul 2026", "ts": 20260715},
        {"id": "d4", "filename": "Pricing_Schedule.xlsx", "type": "Proposal", "score": 64, "uploaded": "10 Jul 2026", "ts": 20260710},
        {"id": "d5", "filename": "NDA_Draft.docx", "type": "Other", "score": None, "uploaded": "02 Jul 2026", "ts": 20260702},
    ],
}

ROW = T("""<div class="dr" style="grid-template-columns:2.4fr 1fr .8fr 1fr">
  [[c1]][[c2]][[c3]][[c4]]
</div>""", c1=dcell("Filename", '<span style="font-weight:500">{{r.filename}}</span>'),
           c2=dcell("Type", '<span class="chip grey xs">{{r.type}}</span>'),
           c3=dcell("Score", '<span class="num" style="color:{{r.scoreColor}};font-weight:500">{{r.score}}</span>', "r"),
           c4=dcell("Uploaded", '<span class="sub num">{{r.uploaded}}</span>'))

TABLE = T("""<div class="dt">
  <div class="dr dh" style="grid-template-columns:2.4fr 1fr .8fr 1fr">[[h1]][[h2]][[h3]][[h4]]</div>
  <sc-for list="{{tbl.rows}}" as="r" hint-placeholder-count="5">[[row]]</sc-for>
</div>""", h1=dth("tbl", "filename", "Filename"), h2=dth("tbl", "type", "Type"),
           h3=dth("tbl", "score", "Score", "r"), h4=dth("tbl", "uploaded", "Uploaded"), row=ROW)

MAIN = T("""
<div class="grid g3" style="gap:12px;margin-bottom:18px">[[k1]][[k2]][[k3]]</div>
[[table]]""", k1=kpi("Documents", "{{stats.docs}}"), k2=kpi("Average score", "{{stats.avg}}"),
           k3=kpi("Open critical findings", "{{stats.critical}}", tone="crit"), table=TABLE)

LOADING = '<p class="sub" style="text-align:center;padding:48px 0">Loading project...</p>'
EMPTY = T('<div class="empty" style="padding:44px 20px"><h3>No documents in this project yet.</h3>[[b]]</div>',
          b=btn("Upload to this project", "primary", attrs='style="margin-top:8px"'))
ERROR = '<div class="alert err" role="alert">Failed to load project</div>'

BODY = T("""
<div class="pagehead">
  <div><div class="row" style="gap:6px;font-size:13px;color:var(--ink2);margin-bottom:6px">[[back]]<a href="#" style="color:inherit">Dashboard</a></div><h1>{{project.name}}</h1></div>
  <div class="actions">[[upload]]</div>
</div>
[[states]]""", back=icon("arrow-left", 14), upload=btn("Upload to this project", "primary"), states=states(MAIN, LOADING, EMPTY, ERROR))

VALS = r"""
const project = D.project;
const docs = D.docs;
// alternate error text also in inventory sow.md §4: "Project not found"
const scoreColor = v => v == null ? 'var(--ink3)' : v >= 80 ? 'var(--ok)' : v >= 50 ? 'var(--med)' : 'var(--crit)';
const rows = docs.map(d => ({ filename: d.filename, type: d.type || 'Unknown', score: d.score == null ? '-' : String(d.score), scoreColor: scoreColor(d.score), uploaded: d.uploaded, ts: d.ts }));
const tbl = self.sortVals('tbl', rows, [{ key: 'filename' }, { key: 'type' }, { key: 'score' }, { key: 'uploaded', get: r => r.ts }], 'filename', 'asc');
return {
  project,
  stats: { docs: String(docs.length), avg: String(project.avg), critical: String(project.critical) },
  tbl,
};
"""

CLICKS = [
    {"css": ".dt .dh button:has-text('Score')", "check": "document.querySelector(\".dt .dh .dc[aria-sort='ascending'] button\") && document.querySelector(\".dt .dh .dc[aria-sort='ascending'] button\").textContent.includes('Score')"},
    {"css": ".dt .dh button:has-text('Uploaded')", "check": "document.querySelector(\".dt .dh .dc[aria-sort='ascending'] button\") && document.querySelector(\".dt .dh .dc[aria-sort='ascending'] button\").textContent.includes('Uploaded')"},
    {"css": ".dt .dh button:has-text('Filename')", "check": "document.querySelector(\".dt .dh .dc[aria-sort='ascending'] button\") && document.querySelector(\".dt .dh .dc[aria-sort='ascending'] button\").textContent.includes('Filename')"},
]


# dc.py's shared phone CSS hides `.dt .dh` entirely (row data becomes labelled cards instead, so a
# header row is normally redundant). This screen's headers are the sort control though, so re-enable
# them on phone as a compact vertical button stack (ponytail: scoped to this artboard's own <style>
# block only -- screen() emits one self-contained file per artboard, so this cannot affect any other
# screen).
PHONE_CSS = ("<style>@media (max-width:760px){"
             ".dt .dh{display:flex!important;flex-direction:column;gap:4px;padding:8px 12px}"
             ".dt .dh .dc{justify-content:flex-start!important;text-align:left!important}"
             "}</style>")


def build(phone=False):
    stem = STEM + ("Phone" if phone else "")
    html = screen(stem, app_shell("dashboard", BODY), VALS, DATA, {}, extra_css=PHONE_CSS, phone=phone)
    return [(stem, html)]
