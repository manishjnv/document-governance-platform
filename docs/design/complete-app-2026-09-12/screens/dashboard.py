"""/dashboard — SOW Review home. Source: inventory/sow.md §1."""
from dc import T, app_shell, screen, btn, chip, icon, dialog, states, dcell, alert, request_access_form

STEM = "Dashboard"
PAGE, TITLE, ORDER = "sow", "SOW Review dashboard", 10

COLS = "minmax(0,2.4fr) minmax(0,.9fr) minmax(0,1fr) minmax(0,1fr) minmax(0,1.1fr) minmax(0,2.6fr)"

DATA = {
    "projects": [
        {"id": "p1", "name": "NovaRetail Software Solutions", "avg": 13, "critical": 7},
        {"id": "p2", "name": "ConflictTest", "avg": 8, "critical": 2},
        {"id": "p3", "name": "RFPValidation", "avg": 25, "critical": 1},
        {"id": "p4", "name": "Acme", "avg": 0, "critical": 0},
    ],
    "docs": [
        {"id": "d1", "group": "g1", "version": 6, "versions": 6, "filename": "SOC_SOW_Testing.docx", "type": "SOW", "completeness": 0, "accuracy": 10, "trend": -2, "uploaded": "24 Jul 2026", "project": "p1", "reviewed": True, "prev": 5},
        {"id": "d1b", "group": "g1", "version": 5, "filename": "SOC_SOW_Testing.docx", "type": "SOW", "completeness": 0, "accuracy": 12, "uploaded": "24 Jul 2026", "project": "p1", "reviewed": True},
        {"id": "d1c", "group": "g1", "version": 4, "filename": "SOC_SOW_Testing.docx", "type": "SOW", "completeness": 0, "accuracy": 14, "uploaded": "23 Jul 2026", "project": "p1", "reviewed": True},
        {"id": "d1d", "group": "g1", "version": 3, "filename": "SOC_SOW_Testing.docx", "type": "SOW", "completeness": 0, "accuracy": 15, "uploaded": "23 Jul 2026", "project": "p1", "reviewed": True},
        {"id": "d1e", "group": "g1", "version": 2, "filename": "SOC_SOW_Testing.docx", "type": "SOW", "completeness": 0, "accuracy": 18, "uploaded": "23 Jul 2026", "project": "p1", "reviewed": True},
        {"id": "d1f", "group": "g1", "version": 1, "filename": "SOC_SOW_Testing.docx", "type": "SOW", "completeness": 0, "accuracy": 21, "uploaded": "23 Jul 2026", "project": "p1", "reviewed": True},
        {"id": "d2", "group": "g2", "version": 1, "versions": 1, "filename": "SOC_SOW_Testing.docx", "type": "SOW", "completeness": 0, "accuracy": 12, "uploaded": "23 Jul 2026", "project": "p1", "reviewed": True},
        {"id": "d3", "group": "g3", "version": 2, "versions": 2, "filename": "Subtle_Conflicts_Test.docx", "type": "SOW", "completeness": 0, "accuracy": 12, "trend": 2, "uploaded": "24 Jul 2026", "project": "p2", "reviewed": True, "prev": 1},
        {"id": "d3b", "group": "g3", "version": 1, "filename": "Subtle_Conflicts_Test.docx", "type": "SOW", "completeness": 0, "accuracy": 10, "uploaded": "24 Jul 2026", "project": "p2", "reviewed": True},
        {"id": "d4", "group": "g4", "version": 1, "versions": 1, "filename": "rfp_sample.pdf", "type": "RFP", "completeness": 29, "accuracy": 25, "uploaded": "23 Jul 2026", "project": "p3", "reviewed": True},
        {"id": "d5", "group": "g5", "version": 1, "versions": 1, "filename": "sample_rfp.docx", "type": "RFP", "completeness": None, "accuracy": None, "uploaded": "18 Jul 2026", "project": "p4", "reviewed": False},
        {"id": "d6", "group": "g6", "version": 1, "versions": 1, "filename": "vendor_proposal_draft.docx", "type": "Proposal", "completeness": None, "accuracy": None, "uploaded": "12 Sep 2026", "project": None, "reviewed": False},
    ],
    "search": [
        {"id": "d1", "filename": "SOC_SOW_Testing.docx", "type": "SOW", "relevance": "92%", "snippet": "…the Supplier shall accommodate Client requests as they arise, including but not limited to…", "uploaded": "24 Jul 2026"},
        {"id": "d4", "filename": "rfp_sample.pdf", "type": "RFP", "relevance": "61%", "snippet": "…proposals must include a fixed price schedule and a liability cap not lower than…", "uploaded": "23 Jul 2026"},
    ],
}

ROW = T("""
<div class="dr {{r.cls}}" style="grid-template-columns:[[cols]]">
  <div class="dc nolbl" data-th="Filename">
    <div class="row" style="gap:6px">
      <sc-if value="{{r.expandable}}" hint-placeholder-val="{{false}}"><button class="xbtn" style="padding:2px" aria-label="{{r.expAria}}" onClick="{{r.toggleVersions}}"><span style="display:inline-flex;transition:transform .15s;transform:{{r.expRot}}">[[chev]]</span></button></sc-if>
      <span style="font-weight:500;overflow:hidden;text-overflow:ellipsis;white-space:nowrap">{{r.label}}</span>
      <sc-if value="{{r.expandable}}" hint-placeholder-val="{{false}}"><span class="faint" style="font-size:12px;white-space:nowrap">{{r.verChip}}</span></sc-if>
    </div>
  </div>
  <div class="dc" data-th="Type">
    <sc-if value="{{r.typeEditing}}" hint-placeholder-val="{{false}}"><select class="select sm" aria-label="Document type" value="{{r.type}}" onChange="{{r.setType}}" onBlur="{{r.closeType}}"><option value="" disabled>Select type</option><option>SOW</option><option>Proposal</option><option>RFP</option><option>Other</option></select></sc-if>
    <sc-if value="{{r.typeIdle}}" hint-placeholder-val="{{true}}"><button class="chip {{r.typeTone}} xs tip" data-tip="Click to change" onClick="{{r.editType}}" style="cursor:pointer;border:0">{{r.type}}</button></sc-if>
  </div>
  <div class="dc r num" data-th="Completeness" style="color:{{r.compColor}};font-weight:500">{{r.comp}}</div>
  <div class="dc r num" data-th="Accuracy"><span style="color:{{r.accColor}};font-weight:500">{{r.acc}}</span><sc-if value="{{r.hasTrend}}" hint-placeholder-val="{{false}}"><span class="tip" data-tip="{{r.trendTip}}" style="margin-left:4px;color:{{r.trendColor}};font-size:12px;font-weight:600">{{r.trendArrow}}</span></sc-if></div>
  <div class="dc num sub" data-th="Uploaded">{{r.uploaded}}</div>
  <div class="dc acts" data-th="Actions">
    <button class="lnk" onClick="{{r.review}}">{{r.reviewLabel}}</button><span class="faint">•</span>
    <a href="#">View</a><span class="faint">•</span>
    <a href="#">New version</a>
    <sc-if value="{{r.noProject}}" hint-placeholder-val="{{false}}"><span class="faint">•</span>
      <sc-if value="{{r.assignIdle}}" hint-placeholder-val="{{true}}"><button class="lnk" onClick="{{r.startAssign}}">Assign project</button></sc-if>
      <sc-if value="{{r.assignEditing}}" hint-placeholder-val="{{false}}"><span class="row" style="gap:6px" onClick="{{stop}}"><input class="input sm" list="dash-projects" placeholder="Project name" style="width:160px" value="{{assignValue}}" onChange="{{setAssign}}" onKeyDown="{{assignKey}}"><button class="lnk" onClick="{{saveAssign}}">Save</button><button class="lnk" style="color:var(--ink3)" onClick="{{cancelAssign}}">Cancel</button></span></sc-if>
    </sc-if>
    <sc-if value="{{r.hasCompare}}" hint-placeholder-val="{{false}}"><span class="faint">•</span><a href="#">{{r.compare}}</a></sc-if>
    <span class="faint">•</span><button class="lnk danger" onClick="{{r.remove}}">Delete</button>
  </div>
</div>""", cols=COLS, chev=icon("chevron-right", 13))

GROUP = T("""
<div class="dr band" style="grid-template-columns:1fr">
  <div class="dc nolbl row wrap" style="gap:8px">
    <button class="xbtn" style="padding:2px" aria-expanded="{{g.ariaOpen}}" aria-label="{{g.toggleAria}}" onClick="{{g.toggle}}"><span style="display:inline-flex;transition:transform .15s;transform:{{g.rot}}">[[chev]]</span></button>
    <span style="color:var(--ink3)">[[folder]]</span><span style="font-weight:600">{{g.name}}</span><span class="faint">· {{g.count}}</span>
    <span class="row wrap" style="margin-left:auto;gap:10px;font-size:12px">
      <sc-if value="{{g.hasStats}}" hint-placeholder-val="{{true}}"><span class="sub">Avg score <b class="num" style="color:var(--ink)">{{g.avg}}</b></span>
      <sc-if value="{{g.hasCrit}}" hint-placeholder-val="{{true}}">[[crit]]</sc-if>
      <a href="#" style="font-weight:500">View project</a></sc-if>
    </span>
  </div>
</div>
<sc-if value="{{g.open}}" hint-placeholder-val="{{true}}"><sc-for list="{{g.rows}}" as="r" hint-placeholder-count="2">[[row]]<sc-if value="{{r.childrenOpen}}" hint-placeholder-val="{{false}}"><sc-for list="{{r.children}}" as="r" hint-placeholder-count="2">[[row]]</sc-for></sc-if></sc-for></sc-if>
""", chev=icon("chevron-right", 14), folder=icon("folder", 14), crit=chip("{{g.critLabel}}", "crit", xs=True), row=ROW)

TABLE = T("""
<div class="dt">
  <div class="dr dh" style="grid-template-columns:[[cols]]"><div class="dc">Filename</div><div class="dc">Type</div><div class="dc r">Completeness</div><div class="dc r">Accuracy</div><div class="dc">Uploaded</div><div class="dc r">Actions</div></div>
  <sc-for list="{{groups}}" as="g" hint-placeholder-count="4">[[group]]</sc-for>
</div>
<datalist id="dash-projects"><option value="NovaRetail Software Solutions"></option><option value="ConflictTest"></option><option value="RFPValidation"></option><option value="Acme"></option></datalist>""", cols=COLS, group=GROUP)

SEARCH_MODE = T("""
<div class="card" style="overflow:hidden">
  <div class="row between" style="padding:10px 14px;border-bottom:1px solid var(--line);background:#FBFAF8;font-size:13px"><span>Search results ({{hits}}) for "{{q}}"</span><span class="faint" style="display:inline-flex">[[spin]]</span></div>
  <sc-if value="{{noHits}}" hint-placeholder-val="{{false}}"><p class="sub" style="padding:32px;text-align:center;font-size:13px">No documents match "{{q}}"</p></sc-if>
  <sc-if value="{{hasHits}}" hint-placeholder-val="{{true}}">
  <div class="dt" style="border:0;border-radius:0">
    <div class="dr dh" style="grid-template-columns:2fr .8fr .8fr 3fr 1fr 1.2fr"><div class="dc">Filename</div><div class="dc">Type</div><div class="dc r">Relevance</div><div class="dc">Snippet</div><div class="dc">Uploaded</div><div class="dc r">Actions</div></div>
    <sc-for list="{{results}}" as="s" hint-placeholder-count="2">
    <div class="dr" style="grid-template-columns:2fr .8fr .8fr 3fr 1fr 1.2fr">[[c1]][[c2]][[c3]][[c4]][[c5]]<div class="dc acts" data-th="Actions"><button class="lnk" onClick="{{s.review}}">{{s.reviewLabel}}</button><span class="faint">•</span><a href="#">View</a></div></div>
    </sc-for>
  </div></sc-if>
</div>""", spin=icon("loader", 14, cls="spin"),
                c1=dcell("Filename", '<span style="font-weight:500">{{s.filename}}</span>'), c2=dcell("Type", '<span class="chip grey xs">{{s.type}}</span>'),
                c3=dcell("Relevance", "{{s.relevance}}", "r"), c4=dcell("Snippet", '<span class="sub tip left" data-tip="{{s.snippet}}" style="overflow:hidden;text-overflow:ellipsis;white-space:nowrap;display:block;max-width:100%">{{s.snippet}}</span>'),
                c5=dcell("Uploaded", '<span class="sub num">{{s.uploaded}}</span>'))

MAIN = T("""
<sc-if value="{{suggestion}}" hint-placeholder-val="{{true}}">
<div class="alert blue row" style="margin-bottom:14px;align-items:center;gap:12px"><div class="grow"><b>SOC_SOW_Testing_v7.docx</b> looks like it could be a new version of <b>SOC_SOW_Testing.docx</b> (v6) -- link as v7? <span style="opacity:.8">(93% similar)</span></div><button class="btn link" style="font-size:13px;font-weight:500" onClick="{{acceptSuggestion}}">Link as v7</button><button class="btn link" style="font-size:13px;color:var(--ink2)" onClick="{{dismissSuggestion}}">Dismiss</button></div>
</sc-if>
<div class="row between wrap" style="margin-bottom:14px;gap:10px">
  <div class="row" style="gap:0;border:1px solid var(--line);border-radius:var(--r);background:#fff;font-size:13px;overflow:hidden">
    <span style="padding:6px 12px;border-right:1px solid var(--line)"><span class="sub">Total</span> <b class="num">{{stats.total}}</b></span>
    <span style="padding:6px 12px;border-right:1px solid var(--line)"><span class="sub">SOW</span> <b class="num">{{stats.sow}}</b></span>
    <span style="padding:6px 12px;border-right:1px solid var(--line)"><span class="sub">Proposal</span> <b class="num">{{stats.proposal}}</b></span>
    <span style="padding:6px 12px;border-right:1px solid var(--line)"><span class="sub">RFP</span> <b class="num">{{stats.rfp}}</b></span>
    <span style="padding:6px 12px"><span class="sub">Other</span> <b class="num">{{stats.other}}</b></span>
  </div>
  <label class="row" style="gap:8px;font-size:13px;white-space:nowrap">Filter by Type <select class="select sm" id="filterType" value="{{typeFilter}}" onChange="{{setTypeFilter}}"><option value="">All Types</option><option>SOW</option><option>Proposal</option><option>RFP</option><option>Other</option></select></label>
</div>
<sc-if value="{{is.error}}" hint-placeholder-val="{{false}}">[[err]]</sc-if>
[[table]]
""", err=alert("err", "Failed to fetch documents").replace('class="alert err row"', 'class="alert err row" style="margin-bottom:14px"'), table=TABLE)

LOADING = '<p class="sub" style="text-align:center;padding:48px 0">Loading documents...</p>'
EMPTY = T('<div class="empty" style="padding:44px 20px"><h3>No documents uploaded yet</h3>[[b]]</div>', b=btn("Upload Your First Document", "primary", attrs='style="margin-top:8px"'))

BODY = T("""
<div class="pagehead">
  <div><h1>SOW Review</h1><p class="faint" style="font-size:12px;margin-top:2px">{{runsHint}}</p></div>
  <div class="actions">
    <div class="search" style="width:280px">[[search]]<input class="input" placeholder="Search all documents..." aria-label="Search all documents" value="{{q}}" onChange="{{setQ}}"><sc-if value="{{hasQ}}" hint-placeholder-val="{{false}}"><button class="xbtn" aria-label="Clear search" style="position:absolute;right:6px;top:50%;transform:translateY(-50%)" onClick="{{clearQ}}">[[x]]</button></sc-if></div>
    [[upload]]
  </div>
</div>
<sc-if value="{{hasQ}}" hint-placeholder-val="{{false}}">[[searchmode]]</sc-if>
<sc-if value="{{noQ}}" hint-placeholder-val="{{true}}">[[states]]</sc-if>
[[dlgs]]""", search=icon("search", 15), x=icon("x", 14), upload=btn("Upload Document", "primary"), searchmode=SEARCH_MODE,
         states=states(MAIN, LOADING, EMPTY, MAIN, MAIN),
         dlgs=dialog("request", "Request access to run reviews", request_access_form(heading=False).replace('class="card card-b rise"', 'class="rise"').replace("max-width:520px", ""), "", 520)
         + dialog("delete", "Delete document", "<p>Permanently delete this document, its reviews, and all findings? This cannot be undone.</p>",
                  btn("Cancel", "", size="sm", attrs='onClick="{{dlg.delete.close}}"') + btn("Delete", "danger", size="sm", attrs='onClick="{{confirmDelete}}"'), 460))

VALS = r"""
const removed = S.removed || {}, types = S.types || {}, projOf = S.projOf || {};
const q = S.search || '', typeF = S.typeFilter || '';
const gated = P.view === 'gated';
const projName = id => { const p = D.projects.find(x => x.id === id); return p ? p.name : null; };
const docs = D.docs.filter(d => !removed[d.id]).map(d => Object.assign({}, d, { type: types[d.id] || d.type, project: projOf[d.id] !== undefined ? projOf[d.id] : d.project }));
const stats = { total: docs.length, sow: docs.filter(d => d.type === 'SOW').length, proposal: docs.filter(d => d.type === 'Proposal').length, rfp: docs.filter(d => d.type === 'RFP').length, other: docs.filter(d => d.type === 'Other').length };
const shown = docs.filter(d => !typeF || d.type === typeF);
const scoreColor = v => v == null ? 'var(--ink3)' : v >= 80 ? 'var(--ok)' : v >= 50 ? 'var(--med)' : 'var(--crit)';
const tone = t => t === 'RFP' ? 'blue' : t === 'Proposal' ? 'info' : t === 'Other' ? 'grey' : 'grey';
const latestV = {}; D.docs.forEach(d => { latestV[d.group] = Math.max(latestV[d.group] || 0, d.version); });
const mkRow = (d, child) => ({ id: d.id, cls: child ? 'child' : '', label: child ? ('v' + d.version + ' -- ' + d.filename) : d.filename,
  expandable: !child && d.versions > 1, verChip: 'v' + d.version + ' (' + d.versions + ' versions)', expAria: self.isOpen('g:' + d.group) ? 'Collapse versions' : 'Expand versions',
  expRot: self.isOpen('g:' + d.group) ? 'rotate(90deg)' : 'none', toggleVersions: (e) => { e.stopPropagation(); self.toggleOpen('g:' + d.group); },
  childrenOpen: !child && d.versions > 1 && self.isOpen('g:' + d.group),
  children: child ? [] : shown.filter(x => x.group === d.group && x.id !== d.id).map(x => mkRow(x, true)),
  type: d.type, typeTone: tone(d.type), typeEditing: S.editType === d.id, typeIdle: S.editType !== d.id,
  editType: (e) => { e.stopPropagation(); self.setState({ editType: d.id }); }, closeType: () => self.setState({ editType: null }),
  setType: (e) => { const t = Object.assign({}, types); t[d.id] = e.target.value; self.setState({ types: t, editType: null }); },
  comp: d.completeness == null ? '-' : String(d.completeness), compColor: scoreColor(d.completeness),
  acc: d.accuracy == null ? '-' : String(d.accuracy), accColor: scoreColor(d.accuracy),
  hasTrend: !child && d.trend != null, trendArrow: d.trend > 0 ? '▲' : '▼', trendColor: d.trend > 0 ? 'var(--ok)' : 'var(--crit)', trendTip: (d.trend > 0 ? '+' : '') + d.trend + ' vs previous version',
  uploaded: d.uploaded, noProject: !d.project, assignIdle: S.assign !== d.id, assignEditing: S.assign === d.id,
  startAssign: (e) => { e.stopPropagation(); self.setState({ assign: d.id, assignValue: '' }); },
  hasCompare: !child ? d.versions > 1 : true, compare: child ? 'Compare vs v' + latestV[d.group] : 'Compare vs v' + d.prev,
  reviewLabel: self.busy('rev-' + d.id) ? 'Reviewing... (~20s)' : 'Review',
  review: (e) => { e.stopPropagation(); if (gated) { self.openDlg('request'); return; } self.runBusy('rev-' + d.id, 1600); },
  remove: (e) => { e.stopPropagation(); self.openDlg('delete', d.id); } });
const latest = shown.filter(d => d.versions);
const groupsList = D.projects.map(p => ({ id: p.id, name: p.name, stats: p })).concat([{ id: null, name: 'No Project', stats: null }]);
const groups = groupsList.map(g => { const rows = latest.filter(d => (d.project || null) === g.id); const all = shown.filter(d => (d.project || null) === g.id);
  const key = 'p:' + (g.id || 'none'); const open = S.expanded[key] !== false;
  return { key, name: g.name, count: String(all.length), open, ariaOpen: open ? 'true' : 'false', toggleAria: (open ? 'Collapse ' : 'Expand ') + g.name, rot: open ? 'rotate(90deg)' : 'none',
    toggle: (e) => { e.stopPropagation(); self.setIn(['expanded', key], !open); },
    hasStats: !!g.stats, avg: g.stats ? String(g.stats.avg) : '', hasCrit: !!(g.stats && g.stats.critical > 0), critLabel: g.stats ? g.stats.critical + ' critical' : '',
    rows: rows.map(d => mkRow(d, false)) }; }).filter(g => g.rows.length > 0 || g.id !== null);
const results = q ? D.search.filter(s => (s.filename + ' ' + s.snippet).toLowerCase().includes(q.toLowerCase())).map(s => Object.assign({}, s, { reviewLabel: self.busy('srev-' + s.id) ? 'Reviewing... (~20s)' : 'Review', review: (e) => { e.stopPropagation(); if (gated) { self.openDlg('request'); return; } self.runBusy('srev-' + s.id, 1600); } })) : [];
const remaining = S.runs == null ? 3 : S.runs;
return { q, hasQ: !!q, noQ: !q, setQ: e => self.setState({ search: e.target.value }), clearQ: () => self.setState({ search: '' }),
  runsHint: remaining === 1 ? '1 run remaining for your organisation' : remaining + ' runs remaining for your organisation',
  suggestion: S.suggestion !== false, acceptSuggestion: () => self.setState({ suggestion: false }), dismissSuggestion: () => self.setState({ suggestion: false }),
  stats: { total: String(stats.total), sow: String(stats.sow), proposal: String(stats.proposal), rfp: String(stats.rfp), other: String(stats.other) },
  typeFilter: typeF, setTypeFilter: e => self.setState({ typeFilter: e.target.value }),
  groups, results, hits: String(results.length), noHits: results.length === 0, hasHits: results.length > 0,
  assignValue: S.assignValue || '', setAssign: e => self.setState({ assignValue: e.target.value }),
  saveAssign: (e) => { e && e.stopPropagation && e.stopPropagation(); const v = (S.assignValue || '').trim(); if (!v) return; const p = D.projects.find(x => x.name.toLowerCase() === v.toLowerCase()); const po = Object.assign({}, projOf); po[S.assign] = p ? p.id : 'p1'; self.setState({ projOf: po, assign: null, assignValue: '' }); },
  cancelAssign: (e) => { e && e.stopPropagation && e.stopPropagation(); self.setState({ assign: null, assignValue: '' }); },
  assignKey: (e) => { if (e.key === 'Escape') self.setState({ assign: null, assignValue: '' }); if (e.key === 'Enter') { const v = (S.assignValue || '').trim(); if (!v) return; const p = D.projects.find(x => x.name.toLowerCase() === v.toLowerCase()); const po = Object.assign({}, projOf); po[S.assign] = p ? p.id : 'p1'; self.setState({ projOf: po, assign: null, assignValue: '' }); } },
  dlg: { request: self.dlgVals('request'), delete: self.dlgVals('delete') },
  confirmDelete: () => { const rm = Object.assign({}, removed); rm[S.dlgArg] = true; self.setState({ removed: rm, dlg: null, dlgArg: null }); } };
"""

DLG_OPEN = "Array.from(document.querySelectorAll('.dlg-ov')).some(d => d.style.pointerEvents === 'auto')"
CLICKS = [
    {"label": "Collapse NovaRetail Software Solutions", "check": "document.querySelector('[aria-label=\"Expand NovaRetail Software Solutions\"]') !== null"},
    {"label": "Expand NovaRetail Software Solutions", "check": "document.querySelector('[aria-label=\"Collapse NovaRetail Software Solutions\"]') !== null"},
    {"label": "Expand versions", "check": "document.querySelectorAll('.dt .dr.child').length >= 5", "note": "Expand versions (chevron on a document)"},
    {"css": ".dt .dr:not(.band) .dc[data-th='Type'] button", "check": "document.querySelector('select[aria-label=\"Document type\"]') !== null", "note": "Click a type to change it"},
    {"text": "Assign project", "check": "document.querySelector('input[list=\"dash-projects\"]') !== null"},
    {"text": "Cancel", "check": "document.querySelector('input[list=\"dash-projects\"]') === null"},
    {"text": "Dismiss", "check": "document.querySelector('.alert.blue') === null"},
    {"css": ".dt .acts button.danger", "check": DLG_OPEN, "note": "Delete (destructive dialog)"},
    {"css": ".dlg-ov[style*='pointer-events: auto'] .dlg-f .btn:not(.danger)", "check": "!(" + DLG_OPEN + ")"},
    {"label": "Search all documents", "check": "true", "note": "Type in the search box to enter search mode"},
]


def build(phone=False):
    stem = STEM + ("Phone" if phone else "")
    props = {"view": {"editor": "enum", "options": ["default", "loading", "empty", "error", "gated"], "default": "default", "section": "State"}}
    html = screen(stem, app_shell("dashboard", BODY), VALS, DATA, {"expanded": {}, "suggestion": True, "typeFilter": "", "removed": {}, "types": {}, "projOf": {}}, props=props, phone=phone)
    return [(stem, html)]
