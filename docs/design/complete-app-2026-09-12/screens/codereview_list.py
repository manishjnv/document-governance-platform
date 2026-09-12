"""/codereview — Code Security Reviews list. Source of truth: apps/web/app/codereview/page.tsx."""
from dc import T, app_shell, screen, btn, chip, icon, kebab, dialog, states, skel, esc

STEM = "CodeReviewList"
PAGE, TITLE, ORDER = "code", "Code Security Review · list", 10

DATA = {
    "reviews": [
        {"id": "r1", "name": "NodeGoat golden scan (VVAH 1.3.0)", "repo": "target-nodegoat", "sha": "c5cb68a", "fullSha": "c5cb68a7084e4ae7dcc60e6a98768720a81841e8",
         "demo": True, "editable": False, "fmt": "findings.json", "date": "Sep 12, 2026, 02:25", "ts": 20260912, "sev": {"critical": 6, "high": 5, "medium": 18, "low": 0, "info": 0}},
        {"id": "r2", "name": "Payments API · Q3 scan", "repo": "acme/payments-api", "sha": "9f1e2a4", "fullSha": "9f1e2a4c0b7d5e6f8a9b0c1d2e3f4a5b6c7d8e9f",
         "demo": False, "editable": True, "fmt": "SARIF", "date": "Sep 9, 2026, 16:40", "ts": 20260909, "sev": {"critical": 2, "high": 4, "medium": 7, "low": 3, "info": 1}},
        {"id": "r3", "name": "Customer portal", "repo": "acme/portal-web", "sha": "b21d0f9", "fullSha": "b21d0f9e8d7c6b5a4f3e2d1c0b9a8f7e6d5c4b3a",
         "demo": False, "editable": True, "fmt": "findings.json", "date": "Aug 28, 2026, 11:05", "ts": 20260828, "sev": {"critical": 0, "high": 1, "medium": 4, "low": 2, "info": 0}},
        {"id": "r4", "name": "Internal tools (pre-audit)", "repo": "acme/ops-tools", "sha": "44ac1e0", "fullSha": "44ac1e07b6a5c4d3e2f1a0b9c8d7e6f5a4b3c2d1",
         "demo": False, "editable": True, "fmt": "findings.json", "date": "Aug 20, 2026, 09:12", "ts": 20260820, "sev": {"critical": 0, "high": 0, "medium": 0, "low": 0, "info": 0}},
    ]
}

CARD = T("""
<div class="card rise" role="link" tabindex="0" aria-label="{{r.aria}}" style="padding:14px 16px;cursor:pointer;transition:border-color .16s,background .16s" onClick="{{r.open}}">
  <div class="row between" style="align-items:flex-start">
    <div class="grow">
      <div class="row" style="gap:8px"><span style="font-weight:600;font-size:14px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap">{{r.name}}</span>
        <sc-if value="{{r.demo}}" hint-placeholder-val="{{false}}">[[demo]]</sc-if></div>
      <div class="row" style="gap:8px;margin-top:4px;font-size:12px;color:var(--ink2)"><span>{{r.repo}}</span><span class="chip outline xs mono tip" data-tip="{{r.fullSha}}">{{r.sha}}</span></div>
    </div>
    <sc-if value="{{r.editable}}" hint-placeholder-val="{{true}}">[[kebab]]</sc-if>
  </div>
  <div class="bar tip" data-tip="{{r.barTip}}" style="margin-top:12px;display:flex;background:var(--na)">
    <i style="width:{{r.wCrit}};background:var(--crit);border-radius:0"></i><i style="width:{{r.wHigh}};background:var(--high);border-radius:0"></i><i style="width:{{r.wMed}};background:var(--med);border-radius:0"></i><i style="width:{{r.wLow}};background:var(--low);border-radius:0"></i><i style="width:{{r.wInfo}};background:var(--info);border-radius:0"></i>
  </div>
  <div style="font-size:12px;color:var(--ink2);margin-top:6px">{{r.sentence}}</div>
  <div class="row between" style="border-top:1px solid var(--line);margin-top:10px;padding-top:8px;font-size:12px;color:var(--ink2)">
    <span class="row" style="gap:8px"><span class="num">{{r.countLabel}}</span><span class="chip outline xs tip" data-tip="Import source format">{{r.fmt}}</span></span>
    <span class="num faint">{{r.date}}</span>
  </div>
</div>""", demo=chip("Demo", "info", tip="Shared sample review — visible to every signed-in user, read-only", xs=True),
         kebab=kebab("r.menu", [("Rename", "{{r.rename}}", "", "pencil"), ("Delete", "{{r.remove}}", "danger", "trash")], aria="{{r.menuAria}}"))

LIST = T("""
<div class="row wrap" style="gap:8px;margin-bottom:14px">
  <div class="search" style="width:260px">[[search]]<input class="input sm" type="search" placeholder="Search by name or repo…" aria-label="Search reviews by name or repo" value="{{q}}" onChange="{{setQ}}"></div>
  <select class="select sm" aria-label="Sort reviews" value="{{sortKey}}" onChange="{{setSort}}"><option value="newest">Newest</option><option value="oldest">Oldest</option><option value="most_findings">Most findings</option><option value="name">Name</option></select>
  <sc-if value="{{actionErr}}" hint-placeholder-val="{{false}}"><p role="alert" class="err-line">{{actionErrText}}</p></sc-if>
</div>
<sc-if value="{{noMatch}}" hint-placeholder-val="{{false}}"><p class="empty" style="padding:24px">No reviews match your search.</p></sc-if>
<div class="grid g3" style="gap:12px">
  <sc-for list="{{rows}}" as="r" hint-placeholder-count="4">[[card]]</sc-for>
</div>""", search=icon("search", 15), card=CARD)

LOADING = '<div class="grid g3" style="gap:12px">' + "".join(
    '<div class="card" style="padding:14px 16px">%s%s%s%s</div>' % (skel("60%", "14px", "margin-bottom:8px"), skel("40%", "12px", "margin-bottom:14px"), skel("100%", "6px", "margin-bottom:10px"), skel("70%", "12px"))
    for _ in range(3)) + "</div>"

EMPTY = T("""<div class="empty" style="padding:40px 24px">
<div style="display:flex;justify-content:center;color:var(--ink3);margin-bottom:10px">[[bug]]</div>
<p class="sub" style="max-width:560px;margin:0 auto 6px">Run the Visa Vulnerability Agentic Harness scan on your repo and upload its findings.json to get a reviewable findings register plus client-ready XLSX and PPTX deliverables.</p>
<p class="faint" style="font-size:12px;max-width:560px;margin:0 auto 16px">Built on Visa's open-source Vulnerability Agentic Harness (Apache-2.0). ScopeWise is not affiliated with or endorsed by Visa, Inc.</p>
<div class="row" style="justify-content:center">[[b1]][[b2]]</div></div>""", bug=icon("bug", 28), b1=btn("Get scanner", "", size="sm"), b2=btn("New review", "primary", "plus", "sm"))

ERROR = alert = '<div class="alert err" role="alert">Failed to load reviews</div>'

BODY = T("""
<div class="pagehead">
  <div class="row" style="gap:8px"><span style="color:var(--accent)">[[bug]]</span><h1>Code Security Reviews</h1></div>
  <div class="actions">[[b1]][[b2]]</div>
</div>
[[states]]
[[dlgs]]""", bug=icon("bug", 18), b1=btn("Get scanner", "", size="sm"), b2=btn("New review", "primary", "plus", "sm"),
         states=states(LIST, LOADING, EMPTY, ERROR),
         dlgs=dialog("rename", "Rename review",
                     '<input class="input" style="width:100%" aria-label="New review name" value="{{renameValue}}" onChange="{{setRename}}" onKeyDown="{{renameKey}}">',
                     btn("Cancel", "", size="sm", attrs='onClick="{{dlg.rename.close}}"') + btn("Save", "primary", size="sm", attrs='onClick="{{saveRename}}"'), 400)
         + dialog("delete", "Delete review", '<p>Delete "<b>{{delName}}</b>"? This can\'t be undone.</p>',
                  btn("Cancel", "", size="sm", attrs='onClick="{{dlg.delete.close}}"') + btn("Delete", "danger", size="sm", attrs='onClick="{{confirmDelete}}"'), 420))

VALS = r"""
const names = Object.assign({}, S.names || {});
const removed = S.removed || {};
const q = (S.search || '').toLowerCase();
const sortKey = S.sortKey || 'newest';
let rows = D.reviews.filter(r => !removed[r.id]).map(r => Object.assign({}, r, { name: names[r.id] || r.name }));
rows = rows.filter(r => !q || r.name.toLowerCase().includes(q) || r.repo.toLowerCase().includes(q));
const total = r => Object.values(r.sev).reduce((a, b) => a + b, 0);
rows.sort((a, b) => sortKey === 'newest' ? b.ts - a.ts : sortKey === 'oldest' ? a.ts - b.ts : sortKey === 'most_findings' ? total(b) - total(a) : a.name.localeCompare(b.name));
const labels = { critical: 'critical', high: 'high', medium: 'medium', low: 'low', info: 'info' };
const items = rows.map(r => { const t = total(r); const pct = k => t ? (100 * r.sev[k] / t) + '%' : '0%';
  const parts = Object.keys(labels).filter(k => r.sev[k] > 0).map(k => r.sev[k] + ' ' + labels[k]);
  return Object.assign({}, r, { aria: 'Open review ' + r.name, menuAria: 'Actions for ' + r.name,
    wCrit: pct('critical'), wHigh: pct('high'), wMed: pct('medium'), wLow: pct('low'), wInfo: pct('info'),
    barTip: t ? parts.join(' · ') : 'No findings', sentence: t ? parts.join(' · ') : 'No findings',
    countLabel: t + (t === 1 ? ' finding' : ' findings'),
    open: () => {}, menu: self.menuVals(r.id),
    rename: (e) => { e.stopPropagation(); self.setState({ renameValue: r.name }); self.openDlg('rename', r.id); },
    remove: (e) => { e.stopPropagation(); self.openDlg('delete', r.id); } }); });
const cur = D.reviews.find(r => r.id === S.dlgArg) || {};
return { rows: items, q: S.search, setQ: e => self.setState({ search: e.target.value }), sortKey, setSort: e => self.setState({ sortKey: e.target.value }),
  noMatch: items.length === 0 && D.reviews.length > 0, actionErr: false, actionErrText: '',
  dlg: { rename: self.dlgVals('rename'), delete: self.dlgVals('delete') },
  renameValue: S.renameValue || '', setRename: e => self.setState({ renameValue: e.target.value }),
  renameKey: e => { if (e.key === 'Enter') { const n = Object.assign({}, names); n[S.dlgArg] = S.renameValue; self.setState({ names: n, dlg: null, dlgArg: null }); } },
  saveRename: () => { const n = Object.assign({}, names); n[S.dlgArg] = S.renameValue; self.setState({ names: n, dlg: null, dlgArg: null }); },
  delName: names[cur.id] || cur.name || '',
  confirmDelete: () => { const rm = Object.assign({}, removed); rm[S.dlgArg] = true; self.setState({ removed: rm, dlg: null, dlgArg: null }); } };
"""

# Harness clicks: each step = {"label": text or aria-label to click, "expect": text that must appear after}
DLG_OPEN = "Array.from(document.querySelectorAll('.dlg-ov')).some(d => d.style.pointerEvents === 'auto')"
DLG_CLOSED = "Array.from(document.querySelectorAll('.dlg-ov')).every(d => d.style.pointerEvents === 'none')"
OPEN_DLG_CANCEL = ".dlg-ov[style*='pointer-events: auto'] .dlg-f .btn:not(.primary):not(.danger)"
CLICKS = [
    {"label": "Actions for Payments API · Q3 scan", "check": "document.querySelector('.menu.open') !== null"},
    {"css": ".menu.open button:first-child", "check": DLG_OPEN},
    {"css": OPEN_DLG_CANCEL, "check": DLG_CLOSED},
    {"label": "Actions for Customer portal", "check": "document.querySelector('.menu.open') !== null"},
    {"css": ".menu.open button.danger", "check": DLG_OPEN},
    {"css": OPEN_DLG_CANCEL, "check": DLG_CLOSED},
    {"label": "Sort reviews", "check": "true"},
]


def build(phone=False):
    html = screen(STEM + ("Phone" if phone else ""), app_shell("codereview", BODY), VALS, DATA, {"sortKey": "newest", "names": {}, "removed": {}, "renameValue": ""}, phone=phone)
    return [(STEM + ("Phone" if phone else ""), html)]
