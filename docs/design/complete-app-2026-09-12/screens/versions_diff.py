"""/versions/diff — Version comparison. Source: inventory/sow.md §5."""
from dc import T, app_shell, screen, icon

STEM = "VersionsDiff"
PAGE, TITLE, ORDER = "sow", "Version comparison", 50

DATA = {"older": 5, "newer": 6}

CARD = T("""<div class="card" style="padding:10px 12px;margin-bottom:8px;border-left:3px solid {{f.bar}};background:{{f.bg}}">
  <div style="font-weight:600;font-size:13px">{{f.title}}</div>
  <div class="faint" style="font-size:12px;margin-top:3px">{{f.meta}}</div>
</div>""")


def _col(prefix):
    return T("""<div>
  <div class="row" style="gap:6px;margin-bottom:10px;cursor:pointer" onClick="{{[[p]].toggle}}">
    <button class="xbtn" aria-label="{{[[p]].toggleAria}}" style="padding:2px"><span style="display:inline-flex;transform:{{[[p]].rot}};transition:transform .15s">[[chev]]</span></button>
    <span class="dot" style="background:{{[[p]].dotColor}}"></span><h3 style="font-size:14px">{{[[p]].label}} ({{[[p]].count}})</h3>
  </div>
  <sc-if value="{{[[p]].open}}" hint-placeholder-val="{{true}}">
    <sc-for list="{{[[p]].items}}" as="f" hint-placeholder-count="2">[[card]]</sc-for>
    <sc-if value="{{[[p]].isEmpty}}" hint-placeholder-val="{{false}}"><p class="empty" style="padding:16px;font-size:13px">{{[[p]].emptyText}}</p></sc-if>
  </sc-if>
</div>""", p=prefix, chev=icon("chevron-right", 14), card=CARD)


MAIN = T("""
<div class="pagehead"><div><div class="row" style="gap:6px;font-size:13px;color:var(--ink2);margin-bottom:6px">[[back]]<a href="#" style="color:inherit">Dashboard</a></div>
<h1>Version Comparison</h1><p class="faint" style="font-size:12px;margin-top:2px">v{{older}} → v{{newer}}</p></div></div>
<div class="grid g3" style="gap:16px">[[c1]][[c2]][[c3]]</div>
""", back=icon("arrow-left", 14), c1=_col("resolved"), c2=_col("news"), c3=_col("persisted"))

LOADING = '<p class="sub" style="text-align:center;padding:48px 0">Loading...</p>'
ERROR = '<div class="alert err" role="alert">{{errorText}}</div>'

BODY = T("""
<sc-if value="{{is.loading}}" hint-placeholder-val="{{false}}">[[loading]]</sc-if>
<sc-if value="{{is.error}}" hint-placeholder-val="{{false}}">[[error]]</sc-if>
<sc-if value="{{showMain}}" hint-placeholder-val="{{true}}">[[main]]</sc-if>
""", loading=LOADING, error=ERROR, main=MAIN)

VALS = r"""
// alternate error text also in inventory sow.md §5: "Missing doc_id or other_version in the URL"
const SEV = { critical: { bar: 'var(--crit)', bg: 'var(--crit-soft)' }, major: { bar: 'var(--high)', bg: 'var(--high-soft)' },
  medium: { bar: 'var(--med)', bg: 'var(--med-soft)' }, default: { bar: 'var(--line2)', bg: '#FCFBF9' } };
const mk = (title, cat, sec, sev) => Object.assign({ title, meta: cat + ' -- ' + sec }, SEV[sev] || SEV.default);
const isEmptyView = P.view === 'empty';
const src = {
  resolved: isEmptyView ? [] : [mk('Reporting cadence unspecified', 'Governance', 'Section 4.5', 'default')],
  news: isEmptyView ? [] : [mk('Unlimited change requests at no cost', 'Commercial', 'Section 4.2', 'critical')],
  persisted: isEmptyView ? [] : [
    mk('Deliverables lack acceptance criteria', 'Scope', 'Section 4.1', 'major'),
    mk('No liability cap referenced', 'Legal', 'Section 4.4', 'major'),
    mk('Data handling clause is silent on residency', 'Security', 'Section 4.6', 'medium'),
  ],
};
const mkCol = (key, label, dotColor, emptyText) => { const ek = 'vd:' + key; const open = S.expanded[ek] !== false; const items = src[key];
  return { label, dotColor, count: items.length, items, isEmpty: items.length === 0, emptyText, open,
    toggleAria: (open ? 'Collapse ' : 'Expand ') + label, rot: open ? 'rotate(90deg)' : 'none',
    toggle: (e) => { e.stopPropagation(); self.setIn(['expanded', ek], !open); } }; };
return {
  showMain: P.view !== 'loading' && P.view !== 'error',
  older: D.older, newer: D.newer,
  errorText: 'Failed to load version diff',
  resolved: mkCol('resolved', 'Resolved', 'var(--ok)', 'Nothing resolved.'),
  news: mkCol('news', 'New', 'var(--accent)', 'No new findings.'),
  persisted: mkCol('persisted', 'Persisted', 'var(--crit)', 'Nothing persisted.'),
};
"""

CLICKS = [
    {"label": "Collapse Resolved", "check": "document.querySelector('[aria-label=\"Expand Resolved\"]') !== null"},
    {"label": "Expand Resolved", "check": "document.querySelector('[aria-label=\"Collapse Resolved\"]') !== null"},
    {"label": "Collapse New", "check": "document.querySelector('[aria-label=\"Expand New\"]') !== null"},
    {"label": "Expand New", "check": "document.querySelector('[aria-label=\"Collapse New\"]') !== null"},
    {"label": "Collapse Persisted", "check": "document.querySelector('[aria-label=\"Expand Persisted\"]') !== null"},
    {"label": "Expand Persisted", "check": "document.querySelector('[aria-label=\"Collapse Persisted\"]') !== null"},
]


def build(phone=False):
    stem = STEM + ("Phone" if phone else "")
    props = {"view": {"editor": "enum", "options": ["default", "loading", "empty", "error"], "default": "default", "section": "State"}}
    html = screen(stem, app_shell("dashboard", BODY), VALS, DATA, {"expanded": {}}, props=props, phone=phone)
    return [(stem, html)]
