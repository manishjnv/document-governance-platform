"""/mitre/connections — SIEM connections. Source of truth: inventory/mitre.md §4."""
from dc import T, app_shell, screen, btn, icon, dialog, states, skel, dth, dcell, tabs

STEM = "MitreConnections"
PAGE, TITLE, ORDER = "mitre", "SIEM connections", 40


def _spark(vals, w=64, h=18, color="var(--accent)"):
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
    "connections": [
        {"id": "c1", "name": "abc ltd Sentinel", "platform": "sentinel",
         "tenant": "8f2c1a6e-91b4-4d3a-9c2e-1a7f5b8d3e60", "client": "2b6d4f1a-7c3e-4a9b-8d5f-6e1c2a9b4d70",
         "sub": "5a1e3c7b-2f4d-4b8a-9e6c-3d7a1f5b2c90", "rg": "acme-sec-rg", "workspace": "acme-sec-ops",
         "schedule": "weekly", "hour": "02:00", "day": "Mon",
         "last_pull": "Sep 8, 2026", "last_status": "completed",
         "health_ok": True, "fail_count": 0,
         "pct": 14.4, "delta": 14.1, "trend": [2.2, 3.6, 5.1, 8.4, 10.4, 14.4],
         "last_error": None},
        {"id": "c2", "name": "Cisco CDC Splunk", "platform": "splunk",
         "host": "splunk.cisco-cdc.internal", "port": "8089", "app": "",
         "schedule": "off", "hour": "00:00", "day": "Mon",
         "last_pull": None, "last_status": None,
         "health_ok": False, "fail_count": 2,
         "pct": None, "delta": None, "trend": [],
         "last_error": "Connection refused: management port 8089 unreachable"},
    ],
}

COLS = "minmax(0,1.7fr) minmax(0,1.05fr) minmax(0,1fr) minmax(0,0.9fr) minmax(0,1.2fr) minmax(0,1.5fr) minmax(0,1.5fr)"
HOUR_OPTS = "".join('<option value="%02d:00">%02d:00 UTC</option>' % (h, h) for h in range(24))
DAY_OPTS = "".join('<option value="%s">%s</option>' % (d, d) for d in ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"])
# ponytail: sparkline SVG is baked as static markup (a hole can only render text, never raw
# HTML), so it's rendered via one sc-if branch keyed on hasTrend rather than per-row from data.
# Correct as long as only one sample row has a trend; if a second trended connection is added,
# give the row template its own per-id branch (or move to a tiny canvas-drawn sparkline).
SPARK_C1 = _spark(DATA["connections"][0]["trend"])

PLATFORM_TABS = tabs("platform", [("sentinel", "Microsoft Sentinel"), ("splunk", "Splunk")]).replace(
    '<div class="tabs" role="tablist">', '<div class="tabs" role="tablist" aria-label="Platform">')

FORM = T("""
<div class="card rise" id="mtc-form" style="padding:16px;margin-bottom:14px">
  <h2 style="font-size:15px">{{formHeading}}</h2>
  <p class="sub" style="font-size:12.5px;margin:4px 0 12px;max-width:640px">{{blurb}}</p>
  [[tabs]]
  <div class="grid g2" style="gap:12px;margin-top:12px">
    <div><label class="label">Name (optional)</label><input class="input" style="width:100%" value="{{form.name}}" onChange="{{setName}}"></div>
    <sc-if value="{{isSentinel}}" hint-placeholder-val="{{true}}">
      <div><label class="label">Tenant ID (GUID)</label><input class="input" style="width:100%" value="{{form.tenant}}" onChange="{{setTenant}}"></div>
      <div><label class="label">Client ID (GUID)</label><input class="input" style="width:100%" value="{{form.client}}" onChange="{{setClient}}"></div>
      <div><label class="label">Subscription ID (GUID)</label><input class="input" style="width:100%" value="{{form.sub}}" onChange="{{setSub}}"></div>
      <div><label class="label">Resource group</label><input class="input" style="width:100%" value="{{form.rg}}" onChange="{{setRg}}"></div>
      <div><label class="label">Log Analytics workspace</label><input class="input" style="width:100%" value="{{form.workspace}}" onChange="{{setWorkspace}}"></div>
    </sc-if>
    <sc-if value="{{isSplunk}}" hint-placeholder-val="{{false}}">
      <div><label class="label">Host (e.g. acme.splunkcloud.com)</label><input class="input" style="width:100%" value="{{form.host}}" onChange="{{setHost}}"></div>
      <div><label class="label">Management port</label><input class="input" style="width:100%" value="{{form.port}}" onChange="{{setPort}}" placeholder="8089"></div>
      <div><label class="label">App (optional — all apps if empty)</label><input class="input" style="width:100%" value="{{form.app}}" onChange="{{setApp}}"></div>
    </sc-if>
    <div><label class="label">{{secretLabel}}{{secretSuffix}}</label><input class="input" type="password" style="width:100%" value="{{form.secret}}" onChange="{{setSecret}}"></div>
    <div><label class="label">Auto-pull schedule</label><select class="select" style="width:100%" value="{{form.schedule}}" onChange="{{setSchedule}}"><option value="off">Off — manual pulls only</option><option value="daily">Daily</option><option value="weekly">Weekly</option></select></div>
    <sc-if value="{{showHour}}" hint-placeholder-val="{{false}}"><div><label class="label">Hour (UTC)</label><select class="select" style="width:100%" value="{{form.hour}}" onChange="{{setHour}}">[[hourOpts]]</select></div></sc-if>
    <sc-if value="{{showDay}}" hint-placeholder-val="{{false}}"><div><label class="label">Day of week</label><select class="select" style="width:100%" value="{{form.day}}" onChange="{{setDay}}">[[dayOpts]]</select></div></sc-if>
  </div>
  <sc-if value="{{hasFormErr}}" hint-placeholder-val="{{false}}"><p class="err-line" style="margin-top:10px">{{formErr}}</p></sc-if>
  <sc-if value="{{saveErr}}" hint-placeholder-val="{{false}}"><p class="err-line" style="margin-top:10px">Could not save the connection</p></sc-if>
  <div class="row" style="margin-top:14px;gap:8px">
    <button class="btn primary" onClick="{{save}}">{{saveLabel}}</button>
    <button class="btn" onClick="{{closeForm}}">Cancel</button>
  </div>
</div>
""", tabs=PLATFORM_TABS, hourOpts=HOUR_OPTS, dayOpts=DAY_OPTS)

HEAD_ROW = T('<div class="dr dh" style="grid-template-columns:[[cols]]">[[c1]][[c2]][[c3]][[c4]][[c5]][[c6]][[c7]]</div>',
             cols=COLS,
             c1=dth("conn", "name", "Connection", sortable=False), c2=dth("conn", "sched", "Schedule", sortable=False),
             c3=dth("conn", "pull", "Last pull", sortable=False), c4=dth("conn", "health", "Health", sortable=False),
             c5=dth("conn", "trend", "Coverage trend", sortable=False), c6=dth("conn", "err", "Last error", sortable=False),
             c7=dth("conn", "acts", "Actions", "r", sortable=False))

TREND_CELL = T("""
<sc-if value="{{c.hasTrend}}" hint-placeholder-val="{{true}}"><div class="row" style="gap:6px"><a href="#" class="num">{{c.pct}}%</a><span class="num" style="font-size:12px;font-weight:600;color:{{c.deltaColor}}">{{c.deltaText}}</span><span class="tip" data-tip="{{c.trendTip}}">[[spark]]</span></div></sc-if>
<sc-if value="{{c.noTrend}}" hint-placeholder-val="{{false}}"><span class="faint">—</span></sc-if>
""", spark=SPARK_C1)

ROW = T("""
<div class="dr" style="grid-template-columns:[[cols]]">
  [[c1]][[c2]][[c3]][[c4]][[c5]][[c6]]
  <div class="dc acts" data-th="Actions">
    <button class="lnk" onClick="{{c.test}}">{{c.testLabel}}</button><button class="lnk" onClick="{{c.pull}}">{{c.pullLabel}}</button>
    <button class="btn icon sm ghost tip" aria-label="{{c.editAria}}" data-tip="Edit" onClick="{{c.openEdit}}">[[pencil]]</button>
    <button class="btn icon sm ghost tip" aria-label="{{c.deleteAria}}" data-tip="Delete" onClick="{{c.openDelete}}">[[trash]]</button>
  </div>
</div>""", cols=COLS,
           c1=dcell("Connection", '<div><div style="font-weight:600">{{c.name}}</div><div class="faint" style="font-size:12px">{{c.subtitle}}</div></div>'),
           c2=dcell("Schedule", "{{c.schedText}}"),
           c3=dcell("Last pull", '<span class="num">{{c.lastPull}}</span>'),
           c4=dcell("Health", '<span class="chip {{c.healthTone}} xs">{{c.healthLabel}}</span>'),
           c5=dcell("Coverage trend", TREND_CELL),
           c6=dcell("Last error", '<span class="sub" style="font-size:12.5px">{{c.lastErrorText}}</span>'),
           pencil=icon("pencil", 14), trash=icon("trash", 14))

TABLE_VIEW = T("""
<sc-if value="{{loadErr}}" hint-placeholder-val="{{false}}"><div class="alert err" style="margin-bottom:12px">Failed to load connections</div></sc-if>
<sc-if value="{{delErr}}" hint-placeholder-val="{{false}}"><p role="alert" class="err-line" style="margin-bottom:8px">Could not delete the connection</p></sc-if>
<div class="dt">[[head]]<sc-for list="{{rows}}" as="c" hint-placeholder-count="2">[[row]]</sc-for></div>
""", head=HEAD_ROW, row=ROW)

LOADING = '<div class="dt">' + HEAD_ROW + "".join(
    '<div class="dr" style="grid-template-columns:%s">%s%s%s%s%s%s%s</div>' % (
        COLS, dcell("Connection", skel("70%")), dcell("Schedule", skel("60%")), dcell("Last pull", skel("60%")),
        dcell("Health", skel("50%")), dcell("Coverage trend", skel("70%")), dcell("Last error", skel("50%")), dcell("Actions", skel("40%"), "r"))
    for _ in range(2)) + "</div>"

EMPTY = '<div class="empty" style="padding:40px 24px"><p class="sub" style="max-width:520px;margin:0 auto">No saved connections yet. Add one to pull detection rules straight from Microsoft Sentinel or Splunk — on a schedule if you like. Saved secrets are encrypted at rest and never shown again.</p></div>'

ERROR = '<div class="alert err" role="alert">SIEM connections are managed by org admins.</div>'

BODY = T("""
<div class="pagehead">
  <div class="row" style="gap:8px"><span style="color:var(--accent)">[[plug]]</span><h1>SIEM connections</h1></div>
  <div class="actions">[[b1]][[b2]]</div>
</div>
<sc-if value="{{formOpen}}" hint-placeholder-val="{{false}}">[[form]]</sc-if>
[[states]]
[[dlg]]""", plug=icon("plug", 18), b1=btn("Add connection", "primary", "plus", "sm", attrs='onClick="{{openAdd}}"'), b2=btn("Assessments", "", "arrow-left", "sm"),
         form=FORM, states=states(TABLE_VIEW, LOADING, EMPTY, ERROR),
         dlg=dialog("delete", "Delete connection", '<p>Delete "<b>{{delName}}</b>"? Scheduled pulls stop; past assessments are kept.</p>',
                    btn("Cancel", "", size="sm", attrs='onClick="{{dlg.delete.close}}"') + btn("Delete", "danger", size="sm", attrs='onClick="{{confirmDelete}}"'), 440))

VALS = r"""
const removed = S.removed || {};
const rowMsg = S.rowMsg || {};
const form = S.form || {};
const editId = S.editId;
const formOpen = !!S.formOpen;
const platTab = self.tabVals('platform', ['sentinel', 'splunk']);
const isSentinel = platTab.current === 'sentinel', isSplunk = !isSentinel;
const secretLabel = isSentinel ? 'Client secret' : 'Auth token';
const secretSuffix = editId ? ' (blank = keep saved)' : ' (stored encrypted)';
const blurb = 'Read-only pull of your detection rules. The ' + (isSentinel ? 'client secret' : 'auth token') + ' is stored encrypted and never shown again.' + (isSentinel ? ' The service principal needs the Microsoft Sentinel Reader role.' : '');
const editRow = editId ? D.connections.find(x => x.id === editId) : null;
const formHeading = editRow ? ('Edit ' + editRow.name) : 'Add connection';
const setField = (k) => (e) => self.setIn(['form', k], e.target.value);
const FIELDS = ['name', 'tenant', 'client', 'sub', 'rg', 'workspace', 'host', 'port', 'app', 'secret', 'schedule', 'hour', 'day'];
const setters = {}; FIELDS.forEach(k => { setters['set' + k[0].toUpperCase() + k.slice(1)] = setField(k); });
const defaultForm = () => ({ name: '', tenant: '', client: '', sub: '', rg: '', workspace: '', host: '', port: '8089', app: '', secret: '', schedule: 'off', hour: '00:00', day: 'Mon' });
const openAdd = () => self.setState({ formOpen: true, editId: null, formErr: '', form: defaultForm(), tab: Object.assign({}, S.tab, { platform: 'sentinel' }) });
const openEdit = (c) => (e) => { e.stopPropagation(); self.setState({ formOpen: true, editId: c.id, formErr: '', form: Object.assign(defaultForm(), c, { secret: '' }), tab: Object.assign({}, S.tab, { platform: c.platform }) }); };
const closeForm = () => self.setState({ formOpen: false, editId: null, formErr: '' });
const save = () => {
  if (!editId && !(form.secret || '').trim()) { self.setState({ formErr: isSentinel ? 'The client secret is required — it is stored encrypted and never shown again.' : 'The auth token is required — it is stored encrypted and never shown again.' }); return; }
  self.setState({ formErr: '' });
  self.runBusy('save', 900, () => self.setState({ formOpen: false, editId: null }));
};
const rows = D.connections.filter(c => !removed[c.id]).map(c => {
  const subtitle = c.platform === 'sentinel' ? ('Sentinel · ' + c.workspace) : ('Splunk · ' + c.host);
  const schedText = c.schedule === 'off' ? 'Off' : c.schedule === 'daily' ? ('Daily · ' + c.hour + ' UTC') : ('Weekly · ' + c.day + ' ' + c.hour + ' UTC');
  const lastPull = c.last_pull ? (c.last_pull + ' · ' + c.last_status) : 'never';
  const hasTrend = c.pct != null;
  const msg = rowMsg[c.id];
  return Object.assign({}, c, {
    subtitle, schedText, lastPull, hasTrend, noTrend: !hasTrend,
    healthTone: c.health_ok ? 'ok' : 'crit', healthLabel: c.health_ok ? 'Healthy' : (c.fail_count + ' failed in a row'),
    deltaText: hasTrend && c.delta != null ? ((c.delta >= 0 ? '▲' : '▼') + Math.abs(c.delta)) : '',
    deltaColor: c.delta >= 0 ? 'var(--ok)' : 'var(--crit)',
    trendTip: 'Coverage % across your ' + (c.trend || []).length + ' completed runs, oldest to newest.',
    lastErrorText: msg || c.last_error || '—',
    testLabel: self.busy('test-' + c.id) ? 'Testing…' : 'Test',
    pullLabel: self.busy('pull-' + c.id) ? 'Pulling…' : 'Pull now',
    test: () => { self.runBusy('test-' + c.id, 900, () => { const m2 = Object.assign({}, self.state.rowMsg); m2[c.id] = c.health_ok ? 'OK — 175 rules reachable' : 'Test failed'; self.setState({ rowMsg: m2 }); }); },
    pull: () => { self.runBusy('pull-' + c.id, 900, () => { const m2 = Object.assign({}, self.state.rowMsg); m2[c.id] = c.health_ok ? null : 'Pull failed'; self.setState({ rowMsg: m2 }); }); },
    editAria: 'Edit ' + c.name, deleteAria: 'Delete ' + c.name,
    openEdit: openEdit(c), openDelete: (e) => { e.stopPropagation(); self.openDlg('delete', c.id); },
  });
});
const cur = D.connections.find(c => c.id === S.dlgArg) || {};
return Object.assign({
  platform: platTab, formOpen, editId, isSentinel, isSplunk, secretLabel, secretSuffix, blurb, formHeading,
  form, openAdd, closeForm, save, saveLabel: self.busy('save') ? 'Saving…' : (editId ? 'Save changes' : 'Save connection'),
  hasFormErr: !!S.formErr, formErr: S.formErr || '', saveErr: false,
  showHour: form.schedule && form.schedule !== 'off', showDay: form.schedule === 'weekly',
  loadErr: false, delErr: false,
  rows, dlg: { delete: self.dlgVals('delete') }, delName: cur.name || '',
  confirmDelete: () => { const rm = Object.assign({}, removed); rm[S.dlgArg] = true; self.setState({ removed: rm, dlg: null, dlgArg: null }); },
}, setters);
"""

DLG_OPEN = "Array.from(document.querySelectorAll('.dlg-ov')).some(d => d.style.pointerEvents === 'auto')"
DLG_CLOSED = "Array.from(document.querySelectorAll('.dlg-ov')).every(d => d.style.pointerEvents === 'none')"
OPEN_DLG_CANCEL = ".dlg-ov[style*='pointer-events: auto'] .dlg-f .btn:not(.primary):not(.danger)"
CLICKS = [
    {"text": "Add connection", "check": "document.getElementById('mtc-form') !== null"},
    {"text": "Splunk", "check": "document.getElementById('mtc-form').textContent.includes('Host (e.g. acme.splunkcloud.com)')"},
    {"css": "#mtc-form select",
     "check": "(() => { const el = document.querySelector('#mtc-form select'); el.value = 'weekly'; el.dispatchEvent(new Event('change', {bubbles:true})); return document.querySelectorAll('#mtc-form select').length === 3; })()"},
    {"text": "Cancel", "check": "document.getElementById('mtc-form') === null"},
    {"label": "Edit abc ltd Sentinel", "check": "document.getElementById('mtc-form') !== null && document.getElementById('mtc-form').textContent.includes('blank = keep saved')"},
    {"text": "Save changes", "check": "document.body.innerText.includes('Saving…')"},
    {"check": "document.getElementById('mtc-form') === null", "note": "Wait for save to finish and the form to close"},
    {"label": "Delete Cisco CDC Splunk", "check": DLG_OPEN},
    {"css": OPEN_DLG_CANCEL, "check": DLG_CLOSED},
    {"text": "Test", "check": "document.body.innerText.includes('Testing…')"},
    {"text": "Pull now", "check": "document.body.innerText.includes('Pulling…')"},
]


def build(phone=False):
    stem = STEM + ("Phone" if phone else "")
    state = {"removed": {}, "rowMsg": {}, "formOpen": False, "editId": None, "form": {}, "formErr": ""}
    html = screen(stem, app_shell("mitre", BODY), VALS, DATA, state, phone=phone)
    return [(stem, html)]
