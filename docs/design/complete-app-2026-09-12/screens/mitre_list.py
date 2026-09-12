"""/mitre — MITRE Assessments list. Source of truth: inventory/mitre.md §0, §1."""
from dc import T, app_shell, screen, btn, chip, icon, states, skel, esc

STEM = "MitreList"
PAGE, TITLE, ORDER = "mitre", "MITRE assessments", 10


def _spark(vals, w=110, h=26, color="var(--accent)"):
    lo, hi = min(vals), max(vals)
    span = (hi - lo) or 1
    n = len(vals)
    pts = " ".join(
        "%.1f,%.1f" % (i * w / (n - 1 if n > 1 else 1), h - 2 - (v - lo) / span * (h - 4))
        for i, v in enumerate(vals)
    )
    return ('<svg width="%d" height="%d" viewBox="0 0 %d %d" fill="none" aria-hidden="true">'
            '<polyline points="%s" stroke="%s" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"/></svg>'
            ) % (w, h, w, h, pts, color)


DATA = {
    "assessments": [
        {"id": "m1", "name": "abc ltd", "customer": "Cisco cdc", "project": None, "demo": False, "editable": True,
         "archived": False, "status": "completed", "siem": "sentinel", "auto": True,
         "pct": 14.4, "covered": 132, "applicable": 918, "domains": {"enterprise": 17.9, "ics": 5.2, "mobile": 1.6},
         "delta": 14.1, "date": "Sep 8, 2026, 08:22 PM", "version": "19.1"},
        {"id": "m2", "name": "Mitre Assessment", "customer": "cisco", "project": "Cisco cdc", "demo": False, "editable": True,
         "archived": True, "status": "completed", "siem": "splunk", "auto": False,
         "pct": 0.3, "covered": 2, "applicable": 644, "domains": {"enterprise": 0.3},
         "delta": -78.4, "date": "Aug 30, 2026, 10:05 AM", "version": "19.1"},
        {"id": "m3", "name": "Acme MITRE Assessment", "customer": "Acme Ltd", "project": None, "demo": True, "editable": False,
         "archived": False, "status": "completed", "siem": None, "auto": False,
         "pct": 10.4, "covered": 95, "applicable": 911, "domains": {"enterprise": 13, "ics": 4.1, "mobile": 0.8},
         "delta": 8.2, "date": "Aug 2, 2026, 09:14 AM", "version": "19.1"},
        {"id": "m4", "name": "Northwind Regional SOC Review", "customer": "Northwind Traders", "project": "SOC modernization",
         "demo": False, "editable": True, "archived": False, "status": "running", "siem": "sentinel", "auto": False,
         "date": "Sep 12, 2026, 07:40 AM", "version": "19.1"},
        {"id": "m5", "name": "European Subsidiary Assessment", "customer": "Contoso EU", "project": None,
         "demo": False, "editable": True, "archived": False, "status": "pending", "siem": None, "auto": False,
         "date": "Sep 10, 2026, 03:15 PM", "version": "19.1"},
        {"id": "m6", "name": "West Coast Infrastructure Review", "customer": "Meridian Energy", "project": None,
         "demo": False, "editable": True, "archived": False, "status": "failed", "siem": None, "auto": False,
         "date": "Sep 5, 2026, 11:02 AM", "version": "19.1"},
    ],
    "trend": [2.2, 3.6, 5.1, 8.4, 10.4, 14.4],
}

CARD = T("""
<div class="card rise" role="link" tabindex="0" aria-label="{{r.aria}}" style="padding:14px 16px;cursor:pointer" onClick="{{r.open}}">
  <div class="row between" style="align-items:flex-start;gap:8px">
    <div class="grow" style="min-width:0">
      <sc-if value="{{r.rn.off}}" hint-placeholder-val="{{true}}"><div style="font-weight:600;font-size:14px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap">{{r.name}}</div></sc-if>
      <sc-if value="{{r.rn.on}}" hint-placeholder-val="{{false}}">
        <div class="row" style="gap:4px" onClick="{{stop}}">
          <input class="input sm" style="width:100%" aria-label="New assessment name" value="{{r.rn.value}}" onChange="{{r.rn.set}}" onKeyDown="{{r.rn.key}}">
          <button class="btn icon sm ghost" aria-label="Save name" onClick="{{r.rn.commit}}">[[check]]</button>
          <button class="btn icon sm ghost" aria-label="Cancel rename" onClick="{{r.rn.cancel}}">[[x]]</button>
        </div>
      </sc-if>
      <div class="row wrap" style="gap:6px;margin-top:4px;font-size:12px;color:var(--ink2)">
        <span style="font-weight:500;color:var(--ink)">{{r.customer}}</span>
        <sc-if value="{{r.hasProject}}" hint-placeholder-val="{{false}}"><span class="faint">·</span><span>{{r.project}}</span></sc-if>
        <sc-if value="{{r.hasSiem}}" hint-placeholder-val="{{false}}"><span class="chip info xs">{{r.siemLabel}}</span></sc-if>
        <sc-if value="{{r.archived}}" hint-placeholder-val="{{false}}">[[archivedChip]]</sc-if>
      </div>
    </div>
    <div class="row" style="gap:2px;flex:none" onClick="{{stop}}">
      <sc-if value="{{r.demo}}" hint-placeholder-val="{{false}}">[[demoChip]]</sc-if>
      <sc-if value="{{r.showActions}}" hint-placeholder-val="{{true}}">
        <button class="btn icon sm ghost tip" aria-label="{{r.renameAria}}" data-tip="Rename" onClick="{{r.rn.start}}">[[pencil]]</button>
        <sc-if value="{{r.archived}}" hint-placeholder-val="{{false}}"><button class="btn icon sm ghost tip" aria-label="{{r.archiveAria}}" data-tip="{{r.archiveTip}}" onClick="{{r.toggleArchive}}">[[restoreIcon]]</button></sc-if>
        <sc-if value="{{r.notArchived}}" hint-placeholder-val="{{true}}"><button class="btn icon sm ghost tip" aria-label="{{r.archiveAria}}" data-tip="{{r.archiveTip}}" onClick="{{r.toggleArchive}}">[[archiveIcon]]</button></sc-if>
      </sc-if>
    </div>
  </div>

  <sc-if value="{{r.completed}}" hint-placeholder-val="{{true}}">
  <div style="margin-top:12px">
    <div class="row" style="align-items:baseline;gap:8px">
      <span class="num" style="font-size:26px;font-weight:600;color:var(--accent)">{{r.pct}}%</span>
      <sc-if value="{{r.hasDelta}}" hint-placeholder-val="{{false}}"><span class="tip num" data-tip="{{r.deltaTip}}" style="font-size:12.5px;font-weight:600;color:{{r.deltaColor}}">{{r.deltaText}}</span></sc-if>
    </div>
    <div class="sub" style="font-size:12.5px;margin-top:2px">{{r.sentence}}</div>
    <div class="stack" style="gap:5px;margin-top:10px">
      <sc-for list="{{r.domains}}" as="d" hint-placeholder-count="3">
      <div class="row" style="gap:8px">
        <span class="faint" style="width:64px;flex:none;font-size:11.5px">{{d.label}}</span>
        <div class="bar" style="flex:1"><i style="width:{{d.w}};background:var(--accent)"></i></div>
        <span class="num" style="width:38px;text-align:right;font-size:11.5px;color:var(--ink2)">{{d.pct}}%</span>
      </div>
      </sc-for>
    </div>
  </div>
  </sc-if>
  <sc-if value="{{r.notCompleted}}" hint-placeholder-val="{{false}}">
  <div class="row" style="gap:8px;padding:14px 0 4px">
    <sc-if value="{{r.running}}" hint-placeholder-val="{{false}}"><span style="display:inline-flex;color:var(--info)">[[loader]]</span></sc-if>
    <span class="sub" style="font-size:13px">{{r.statusHelp}}</span>
  </div>
  </sc-if>

  <div class="row between" style="border-top:1px solid var(--line);margin-top:10px;padding-top:8px;font-size:12px">
    <span class="row" style="gap:8px"><span class="chip {{r.statusTone}} xs">{{r.statusLabel}}</span><span class="faint">{{r.attackVer}}</span></span>
    <span class="num faint">{{r.date}}</span>
  </div>
</div>
""", check=icon("check", 13), x=icon("x", 13), pencil=icon("pencil", 14), archiveIcon=icon("archive", 14), restoreIcon=icon("archive-restore", 14),
     loader=icon("loader", 14, cls="spin"),
     demoChip=chip("Demo", "info", tip="Shared sample assessment — visible to every signed-in user, read-only", xs=True),
     archivedChip=chip("Archived", "outline", xs=True))

LIST = T("""
<div class="row wrap" style="gap:10px;margin-bottom:14px;align-items:center">
  <div class="search" style="width:280px">[[searchIcon]]<input class="input sm" type="search" placeholder="Search by name, customer, or project…" aria-label="Search assessments by name, customer, or project" value="{{q}}" onChange="{{setQ}}"></div>
  <select class="select sm" aria-label="Filter by status" value="{{statusFilter}}" onChange="{{setStatusFilter}}">
    <option value="">All statuses</option><option value="pending">Not run yet</option><option value="running">Running</option><option value="completed">Completed</option><option value="failed">Failed</option>
  </select>
  <sc-if value="{{hasArchived}}" hint-placeholder-val="{{true}}"><label class="row" style="gap:6px;font-size:13px;white-space:nowrap"><input type="checkbox" id="mtl-show-archived" checked="{{showArchived}}" onChange="{{toggleShowArchived}}">Show archived ({{archivedCount}})</label></sc-if>
  <sc-if value="{{actionErr}}" hint-placeholder-val="{{false}}"><p role="alert" class="err-line" style="margin:0">{{actionErrText}}</p></sc-if>
  <div class="grow"></div>
  <div style="text-align:right">
    <div class="lbl tip" data-tip="{{sparkTip}}" style="margin-bottom:2px">Your trend so far</div>
    <div class="row" style="gap:6px;justify-content:flex-end">[[sparkSvg]]<span class="num faint" style="font-size:11.5px">{{trendText}}</span></div>
  </div>
</div>
<sc-if value="{{noMatch}}" hint-placeholder-val="{{false}}"><p class="empty" style="padding:24px">No assessments match your search or filters.</p></sc-if>
<div class="grid g3" style="gap:12px">
  <sc-for list="{{rows}}" as="r" hint-placeholder-count="6">[[card]]</sc-for>
</div>
""", searchIcon=icon("search", 15), sparkSvg=_spark(DATA["trend"]), card=CARD)

LOADING = '<div class="grid g3" style="gap:12px">' + "".join(
    '<div class="card" style="padding:14px 16px">%s%s%s%s%s%s</div>' % (
        skel("70%", "15px", "margin-bottom:8px"), skel("45%", "12px", "margin-bottom:14px"),
        skel("30%", "26px", "margin-bottom:8px"), skel("100%", "8px", "margin-bottom:6px"),
        skel("100%", "8px", "margin-bottom:6px"), skel("60%", "12px"))
    for _ in range(3)) + "</div>"

EMPTY = T("""<div class="empty" style="padding:44px 24px">
<div style="display:flex;justify-content:center;color:var(--ink3);margin-bottom:10px">[[target]]</div>
<p class="sub" style="max-width:560px;margin:0 auto 16px">Upload your SIEM detection rules and we'll show you exactly which MITRE ATT&CK techniques you can and can't detect. You get a coverage score, a ranked gap list, and a build roadmap — tailored to the log sources you already have.</p>
[[btn]]</div>""", target=icon("target", 28), btn=btn("Start your first assessment", "primary", "plus"))

ERROR = '<div class="alert err" role="alert">Failed to load assessments</div>'

BODY = T("""
<div class="pagehead">
  <div class="row" style="gap:8px"><span style="color:var(--accent)">[[target]]</span><h1>MITRE Assessments</h1></div>
  <div class="actions">[[b1]][[b2]]</div>
</div>
[[states]]""", target=icon("target", 18), b1=btn("SIEM connections", "", size="sm"), b2=btn("New assessment", "primary", "plus", "sm"),
         states=states(LIST, LOADING, EMPTY, ERROR))

VALS = r"""
const STATUS_META = { pending: {label:'Not run yet', tone:'grey'}, running: {label:'Running', tone:'info'}, completed: {label:'Completed', tone:'ok'}, failed: {label:'Failed', tone:'crit'} };
const STATUS_HELP = { pending: 'Uploaded and parsed — open it to run the assessment.', running: 'Running now — mapping your rules to ATT&CK techniques. This takes a few minutes.', failed: "The run didn't finish — open it to see why and re-run." };
const DOMAIN_ORDER = [['enterprise', 'Enterprise'], ['ics', 'ICS / OT'], ['mobile', 'Mobile']];
const names = S.names || {};
const archOverride = S.archOverride || {};
const q = (S.search || '').toLowerCase();
const statusFilter = S.statusFilter || '';
const showArchived = !!S.showArchived;
const all = D.assessments.map(a => Object.assign({}, a, {
  name: names[a.id] || a.name,
  archived: archOverride[a.id] !== undefined ? archOverride[a.id] : a.archived,
}));
const archivedCount = all.filter(a => a.archived).length;
const hasArchived = archivedCount > 0;
const visible = all.filter(a => (showArchived || !a.archived))
  .filter(a => !statusFilter || a.status === statusFilter)
  .filter(a => !q || (a.name + ' ' + (a.customer || '') + ' ' + (a.project || '')).toLowerCase().includes(q));
const rows = visible.map(a => {
  const sm = STATUS_META[a.status];
  const domains = a.status === 'completed' ? DOMAIN_ORDER.filter(([k]) => a.domains && a.domains[k] != null).map(([k, label]) => ({ label, pct: a.domains[k], w: a.domains[k] + '%' })) : [];
  const hasDelta = a.status === 'completed' && a.delta != null;
  const rn = self.renameVals(a.id, a.name, (v) => { const n = Object.assign({}, names); n[a.id] = v; self.setState({ names: n }); });
  return Object.assign({}, a, {
    aria: 'Open assessment ' + a.name, open: () => {},
    hasProject: !!a.project, hasSiem: !!a.siem,
    siemLabel: a.siem ? ((a.siem === 'sentinel' ? 'Sentinel' : 'Splunk') + (a.auto ? ' · auto' : '')) : '',
    rn, showActions: a.editable && rn.off,
    renameAria: 'Rename ' + a.name, archiveAria: (a.archived ? 'Unarchive ' : 'Archive ') + a.name,
    archiveTip: a.archived ? 'Bring back to the default list.' : 'Hide from the default list — stays available in Compare. Nothing is deleted.',
    notArchived: !a.archived,
    toggleArchive: (e) => { e.stopPropagation(); const o = Object.assign({}, archOverride); o[a.id] = !a.archived; self.setState({ archOverride: o }); },
    completed: a.status === 'completed', notCompleted: a.status !== 'completed', running: a.status === 'running',
    statusTone: sm.tone, statusLabel: sm.label, statusHelp: STATUS_HELP[a.status] || '',
    attackVer: 'ATT&CK v' + a.version, domains,
    sentence: a.status === 'completed' ? ('coverage — your rules detect ' + a.covered + ' of ' + a.applicable + ' applicable techniques') : '',
    hasDelta, deltaText: hasDelta ? ((a.delta >= 0 ? '▲' : '▼') + Math.abs(a.delta)) : '',
    deltaColor: hasDelta && a.delta >= 0 ? 'var(--ok)' : 'var(--crit)',
    deltaTip: hasDelta ? ((a.delta > 0 ? '+' : '') + a.delta + ' points vs your previous completed run') : '',
  });
});
const noMatch = rows.length === 0 && all.length > 0;
const trend = D.trend || [];
return {
  q: S.search || '', setQ: e => self.setState({ search: e.target.value }),
  statusFilter, setStatusFilter: e => self.setState({ statusFilter: e.target.value }),
  hasArchived, archivedCount, showArchived, toggleShowArchived: () => self.setState({ showArchived: !showArchived }),
  actionErr: false, actionErrText: 'Could not update the assessment',
  sparkTip: 'Coverage % across your ' + trend.length + ' completed runs, oldest to newest.',
  trendText: (trend.length ? trend[0] : 0) + '% → ' + (trend.length ? trend[trend.length - 1] : 0) + '%',
  rows, noMatch,
};
"""

CLICKS = [
    {"label": "Rename abc ltd", "check": "document.querySelector('input[aria-label=\"New assessment name\"]') !== null"},
    {"label": "Save name", "check": "document.querySelector('input[aria-label=\"New assessment name\"]') === null"},
    {"label": "Archive abc ltd", "check": "document.querySelector('[aria-label=\"Open assessment abc ltd\"]') === null"},
    {"css": "#mtl-show-archived", "check": "document.querySelector('[aria-label=\"Open assessment abc ltd\"]') !== null && document.querySelector('[aria-label=\"Open assessment abc ltd\"]').textContent.includes('Archived')"},
    {"label": "Unarchive abc ltd", "check": "document.querySelector('[aria-label=\"Archive abc ltd\"]') !== null"},
    {"css": "select[aria-label='Filter by status']",
     "check": "(() => { const el = document.querySelector('select[aria-label=\"Filter by status\"]'); el.value = 'failed'; el.dispatchEvent(new Event('change', {bubbles:true})); return document.querySelectorAll('[role=\"link\"]').length === 1; })()"},
    {"css": "input[aria-label='Search assessments by name, customer, or project']",
     "check": "(() => { const el = document.querySelector('input[aria-label=\"Search assessments by name, customer, or project\"]'); const setter = Object.getOwnPropertyDescriptor(window.HTMLInputElement.prototype, 'value').set; setter.call(el, 'zzz-no-match'); el.dispatchEvent(new Event('input', {bubbles:true})); return document.querySelector('.empty') !== null; })()",
     "note": "Search for text that matches nothing"},
]


def build(phone=False):
    stem = STEM + ("Phone" if phone else "")
    state = {"names": {}, "archOverride": {}, "statusFilter": "", "showArchived": False}
    html = screen(stem, app_shell("mitre", BODY), VALS, DATA, state, phone=phone)
    return [(stem, html)]
