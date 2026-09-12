"""/admin — platform admin. Source: inventory/codereview_admin_login.md §B."""
from dc import T, app_shell, screen, btn, chip, icon, kpi, dcell, alert, states, skel

STEM = "Admin"
PAGE, TITLE, ORDER = "admin", "Admin", 10

DATA = {
    "orgs": [
        {"id": "o1", "name": "Default Org", "email": "manishjnvk@gmail.com · platform admin", "tier": "free", "members": 1, "created": "18/07/2026"},
        {"id": "o2", "name": "starshrishail's Workspace", "email": "starshrishail@gmail.com", "tier": "free", "members": 1, "created": "21/07/2026"},
        {"id": "o3", "name": "manishkumarjnvk's Workspace", "email": "manishkumarjnvk@gmail.com", "tier": "free", "members": 1, "created": "23/07/2026"},
        {"id": "o4", "name": "manishjnvk1's Workspace", "email": "manishjnvk1@gmail.com", "tier": "free", "members": 1, "created": "23/07/2026"},
        {"id": "o5", "name": "veena9jan's Workspace", "email": "veena9jan@gmail.com", "tier": "free", "members": 1, "created": "24/07/2026"},
        {"id": "o6", "name": "urdineshnaidu's Workspace", "email": "urdineshnaidu@gmail.com", "tier": "free", "members": 1, "created": "04/08/2026"},
        {"id": "o7", "name": "hemantsawant48's Workspace", "email": "hemantsawant48@gmail.com", "tier": "free", "members": 1, "created": "07/08/2026"},
        {"id": "o8", "name": "talk2maq's Workspace", "email": "talk2maq@gmail.com", "tier": "free", "members": 1, "created": "12/09/2026"},
        {"id": "o9", "name": "rajendra19sep's Workspace", "email": "rajendra19sep@gmail.com", "tier": "free", "members": 1, "created": "12/09/2026"},
    ],
    "people": [
        {"name": "Manish Kumar", "email": "manishjnvk@gmail.com", "role": "Admin", "ws": "Default Org", "status": "Active", "joined": "1 month ago", "signin": "1 min ago", "docs": 11, "reviews": 15, "active": "1 min ago"},
        {"name": "Shrishail Potadar", "email": "starshrishail@gmail.com", "role": "Admin", "ws": "starshrishail's Workspace", "status": "Active", "joined": "1 month ago", "signin": "1 month ago", "docs": 0, "reviews": 0, "active": "1 month ago"},
        {"name": "Manish Kumar", "email": "manishkumarjnvk@gmail.com", "role": "Admin", "ws": "manishkumarjnvk's Workspace", "status": "Active", "joined": "1 month ago", "signin": "2 hours ago", "docs": 0, "reviews": 0, "active": "1 hour ago"},
        {"name": "Manish Kumar", "email": "manishjnvk1@gmail.com", "role": "Admin", "ws": "manishjnvk1's Workspace", "status": "Active", "joined": "1 month ago", "signin": "1 month ago", "docs": 0, "reviews": 0, "active": "1 month ago"},
        {"name": "Veena Kumari", "email": "veena9jan@gmail.com", "role": "Admin", "ws": "veena9jan's Workspace", "status": "Active", "joined": "1 month ago", "signin": "1 month ago", "docs": 0, "reviews": 0, "active": "1 month ago"},
        {"name": "Dinesh Naidu", "email": "urdineshnaidu@gmail.com", "role": "Admin", "ws": "urdineshnaidu's Workspace", "status": "Active", "joined": "1 month ago", "signin": "29 days ago", "docs": 0, "reviews": 0, "active": "29 days ago"},
        {"name": "Hemant Sawant (hems)", "email": "hemantsawant48@gmail.com", "role": "Admin", "ws": "hemantsawant48's Workspace", "status": "Active", "joined": "1 month ago", "signin": "1 month ago", "docs": 0, "reviews": 0, "active": "1 month ago"},
        {"name": "Mohammed Shaik", "email": "talk2maq@gmail.com", "role": "Admin", "ws": "talk2maq's Workspace", "status": "Active", "joined": "5 hours ago", "signin": "5 hours ago", "docs": 0, "reviews": 0, "active": "5 hours ago"},
        {"name": "Rajendra Sah", "email": "rajendra19sep@gmail.com", "role": "Admin", "ws": "rajendra19sep's Workspace", "status": "Suspended", "joined": "5 hours ago", "signin": "5 hours ago", "docs": 0, "reviews": 0, "active": "5 hours ago"},
    ],
    "signins": [
        {"who": "Manish Kumar", "how": "Google", "device": "Chrome on Windows", "ip": "49.205.203.76", "when": "1 min ago"},
        {"who": "Rajendra Sah", "how": "Email code", "device": "Chrome on Android", "ip": "103.21.58.14", "when": "5 hours ago"},
        {"who": "Mohammed Shaik", "how": "Google", "device": "Safari on macOS", "ip": "182.73.44.9", "when": "5 hours ago"},
        {"who": "Manish Kumar", "how": "Google", "device": "Chrome on Windows", "ip": "49.205.203.76", "when": "2 hours ago"},
        {"who": "Dinesh Naidu", "how": "Google", "device": "Edge on Windows", "ip": "117.196.31.2", "when": "29 days ago"},
    ],
    "activity": [
        {"who": "Manish Kumar", "what": "Signed in with Google", "when": "1 min ago"},
        {"who": "Rajendra Sah", "what": "Was given access", "when": "5 hours ago"},
        {"who": "Rajendra Sah", "what": "Created the workspace", "when": "5 hours ago"},
        {"who": "Mohammed Shaik", "what": "Signed in with an email code", "when": "5 hours ago"},
        {"who": "Manish Kumar", "what": "Uploaded a document", "when": "2 hours ago"},
        {"who": "Manish Kumar", "what": "Ran an AI review", "when": "1 day ago"},
    ],
}

ORG_COLS = "minmax(0,2.2fr) minmax(0,.8fr) minmax(0,1.5fr) minmax(0,.7fr) minmax(0,1fr) minmax(0,1.3fr)"
PEOPLE_COLS = "minmax(0,1.4fr) minmax(0,1.8fr) minmax(0,.7fr) minmax(0,1.6fr) minmax(0,.9fr) minmax(0,1fr) minmax(0,1fr) minmax(0,.8fr) minmax(0,.7fr) minmax(0,1fr)"

ORG_ROW = T("""
<div class="dr" style="grid-template-columns:[[cols]]">
  [[c_org]]
  [[c_tier]]
  <div class="dc" data-th="Runs">
    <sc-if value="{{o.free}}" hint-placeholder-val="{{true}}"><span class="row" style="gap:6px" onClick="{{stop}}"><input class="input sm num" type="number" min="0" max="1000" aria-label="Runs to grant" style="width:76px" value="{{o.draft}}" onChange="{{o.setDraft}}">[[setbtn]]<span class="faint num" style="font-size:12px">{{o.runsNote}}</span></span></sc-if>
    <sc-if value="{{o.paid}}" hint-placeholder-val="{{false}}"><span class="sub">Unlimited</span></sc-if>
  </div>
  [[c_members]]
  [[c_created]]
  <div class="dc r" data-th="Actions"><select class="select sm" aria-label="{{o.tierAria}}" value="{{o.tier}}" onChange="{{o.setTier}}" onClick="{{stop}}"><option value="free">free</option><option value="pro">pro</option><option value="enterprise">enterprise</option></select></div>
</div>""", cols=ORG_COLS,
            c_org=dcell("Organisation", '<div><div style="font-weight:500">{{o.name}}</div><div class="faint" style="font-size:11.5px">{{o.email}}</div></div>'),
            c_tier=dcell("Tier", '<span class="chip {{o.tierTone}} xs" style="text-transform:uppercase;letter-spacing:.04em">{{o.tier}}</span>'),
            setbtn=btn("Set", "", size="sm", attrs='onClick="{{o.setRuns}}"'),
            c_members=dcell("Members", '<span class="num">{{o.members}}</span>', "r"), c_created=dcell("Created", '<span class="sub num">{{o.created}}</span>'))

ORGS = T("""
<div class="card" style="margin-bottom:16px">
  <div class="card-h" style="align-items:flex-start;flex-direction:column;gap:4px"><h3>Organisations</h3>
    <p class="sub" style="font-size:12.5px">Free-tier organisations can upload and configure but cannot start reviews or MITRE assessments. Grant a number of runs, or set pro/enterprise for unlimited. Requests arrive by email with source assessment_request / review_request.</p>
    <sc-if value="{{is.error}}" hint-placeholder-val="{{false}}"><p role="alert" class="err-line">Could not load organisations.</p></sc-if>
  </div>
  <div class="card-b" style="padding:12px">
    <sc-if value="{{is.loading}}" hint-placeholder-val="{{false}}"><p class="faint" style="font-size:12px">Loading…</p></sc-if>
    <sc-if value="{{is.empty}}" hint-placeholder-val="{{false}}"><p class="sub" style="font-size:13px">No organisations yet.</p></sc-if>
    <sc-if value="{{showOrgs}}" hint-placeholder-val="{{true}}">
    <div class="dt">
      <div class="dr dh" style="grid-template-columns:[[cols]]"><div class="dc">Organisation</div><div class="dc">Tier</div><div class="dc">Runs</div><div class="dc r">Members</div><div class="dc">Created</div><div class="dc r">Actions</div></div>
      <sc-for list="{{orgs}}" as="o" hint-placeholder-count="3">[[row]]</sc-for>
    </div></sc-if>
  </div>
</div>""", cols=ORG_COLS, row=ORG_ROW)

PERSON = T("""
<div class="dr" style="grid-template-columns:[[cols]]">[[c1]][[c2]][[c3]][[c4]]<div class="dc" data-th="Status"><span class="chip {{p.tone}} xs" style="text-transform:uppercase;letter-spacing:.04em">{{p.status}}</span></div>[[c6]][[c7]][[c8]][[c9]][[c10]]</div>""",
           cols=PEOPLE_COLS, c1=dcell("Name", '<span style="font-weight:500">{{p.name}}</span>'), c2=dcell("Email", '<span class="sub" style="overflow:hidden;text-overflow:ellipsis;white-space:nowrap;display:block">{{p.email}}</span>'),
           c3=dcell("Role", "{{p.role}}"), c4=dcell("Workspace", '<span style="overflow:hidden;text-overflow:ellipsis;white-space:nowrap;display:block">{{p.ws}}</span>'),
           c6=dcell("Joined", '<span class="sub">{{p.joined}}</span>'), c7=dcell("Last sign-in", '<span class="sub">{{p.signin}}</span>'), c8=dcell("Documents", '<span class="num">{{p.docs}}</span>', "r"),
           c9=dcell("Reviews", '<span class="num">{{p.reviews}}</span>', "r"), c10=dcell("Last active", '<span class="sub">{{p.active}}</span>'))

PEOPLE = T("""
<div class="card" style="margin-bottom:16px">
  <div class="card-h"><h3>People</h3><div class="search" style="width:220px">[[s]]<input class="input sm" placeholder="Search people…" aria-label="Search people…" value="{{qPeople}}" onChange="{{setQPeople}}"></div></div>
  <div class="card-b" style="padding:12px">
    <sc-if value="{{noPeople}}" hint-placeholder-val="{{false}}"><p class="sub" style="font-size:13px;padding:8px 4px">No people match your search.</p></sc-if>
    <sc-if value="{{hasPeople}}" hint-placeholder-val="{{true}}">
    <div class="dt" style="overflow-x:auto">
      <div class="dr dh" style="grid-template-columns:[[cols]]"><div class="dc">Name</div><div class="dc">Email</div><div class="dc">Role</div><div class="dc">Workspace</div><div class="dc">Status</div><div class="dc">Joined</div><div class="dc">Last sign-in</div><div class="dc r">Documents</div><div class="dc r">Reviews</div><div class="dc">Last active</div></div>
      <sc-for list="{{people}}" as="p" hint-placeholder-count="3">[[row]]</sc-for>
    </div></sc-if>
  </div>
</div>""", s=icon("search", 14), cols=PEOPLE_COLS, row=PERSON)

FEEDS = T("""
<div class="grid g2" style="margin-bottom:16px">
  <div class="card"><div class="card-h"><h3>Recent sign-ins</h3><div class="search" style="width:190px">[[s]]<input class="input sm" placeholder="Search sign-ins…" aria-label="Search sign-ins…" value="{{qSign}}" onChange="{{setQSign}}"></div></div>
    <div class="card-b" style="padding:6px 0;max-height:288px;overflow-y:auto">
      <sc-if value="{{noSign}}" hint-placeholder-val="{{false}}"><p class="sub" style="font-size:13px;padding:8px 16px">No sign-ins recorded yet.</p></sc-if>
      <sc-for list="{{signins}}" as="s" hint-placeholder-count="3"><div class="row between" style="padding:7px 16px;font-size:12.5px;border-bottom:1px solid var(--line)"><span><b>{{s.who}}</b> <span class="sub">· {{s.how}} · {{s.device}} · from {{s.ip}}</span></span><span class="faint num" style="white-space:nowrap">{{s.when}}</span></div></sc-for>
    </div></div>
  <div class="card"><div class="card-h"><h3>Recent activity</h3><div class="search" style="width:190px">[[s]]<input class="input sm" placeholder="Search activity…" aria-label="Search activity…" value="{{qAct}}" onChange="{{setQAct}}"></div></div>
    <div class="card-b" style="padding:6px 0;max-height:288px;overflow-y:auto">
      <sc-if value="{{noAct}}" hint-placeholder-val="{{false}}"><p class="sub" style="font-size:13px;padding:8px 16px">Nothing yet.</p></sc-if>
      <sc-for list="{{activity}}" as="a" hint-placeholder-count="3"><div class="row between" style="padding:7px 16px;font-size:12.5px;border-bottom:1px solid var(--line)"><span><b>{{a.who}}</b> <span class="sub">— {{a.what}}</span></span><span class="faint num" style="white-space:nowrap">{{a.when}}</span></div></sc-for>
    </div></div>
</div>""", s=icon("search", 14))

USAGE = T("""
<div class="card"><div class="card-h"><h3>AI usage</h3></div><div class="card-b">
  <div class="grid g6" style="gap:10px">[[k1]][[k2]][[k3]][[k4]][[k5]][[k6]]</div>
  <p class="faint" style="font-size:12px;margin-top:10px">AI models in use: z-ai/glm-5.2, minimax/minimax-m3, deepseek/deepseek-v4-flash</p>
</div></div>""", k1=kpi("Reviews finished", "15"), k2=kpi("Reviews failed", "1", tone="crit"), k3=kpi("Checks per review", "6"),
           k4=kpi("AI calls (approx.)", "90", "finished reviews × checks"), k5=kpi("Average review time", "42s"), k6=kpi("Last review", "1 day ago"))

KPIS = T("""<div class="grid g5" style="margin-bottom:16px">[[k1]][[k2]][[k3]][[k4]][[k5]]</div>""",
         k1=kpi("Members", "9", "9 active"), k2=kpi("Sign-ins this week", "23", "37 in the last 30 days"), k3=kpi("Documents", "11", "0 added this week"),
         k4=kpi("AI reviews", "15", "0 this week"), k5=kpi("Issues found", "896", "across all reviews"))

MAIN = KPIS + ORGS + PEOPLE + FEEDS + USAGE
LOADING = '<p class="sub" style="font-size:13px">Loading…</p>' + KPIS.replace('"9"', '"—"')
ERROR = alert("err", "Could not load the admin overview.").replace('class="alert err row"', 'class="alert err row" style="margin-bottom:14px"') + MAIN

BODY = T("""
<div class="pagehead">
  <div class="row" style="gap:8px"><span style="color:var(--accent)">[[shield]]</span><h1>Admin</h1></div>
  <div class="actions"><span class="faint" style="font-size:11.5px">Last updated {{updated}}</span><button class="btn sm" onClick="{{refresh}}"><span class="{{spinCls}}" style="display:inline-flex">[[refresh]]</span>Refresh</button></div>
</div>
[[states]]""", shield=icon("shield", 18), refresh=icon("refresh", 14), states=states(MAIN, LOADING, MAIN, ERROR))

VALS = r"""
const tiers = S.tiers || {}, runs = S.runs || {}, drafts = S.drafts || {};
const norm = s => (s || '').toLowerCase();
const orgs = D.orgs.map(o => { const tier = tiers[o.id] || o.tier; const free = tier === 'free'; const granted = runs[o.id] == null ? 0 : runs[o.id];
  return Object.assign({}, o, { tier, free, paid: !free, tierTone: free ? 'grey' : 'blue', tierAria: 'Tier for ' + o.name, members: String(o.members),
    draft: drafts[o.id] != null ? drafts[o.id] : String(granted), runsNote: granted > 0 ? granted + ' granted' : '',
    setDraft: e => self.setIn(['drafts', o.id], e.target.value),
    setRuns: e => { e.stopPropagation(); const v = Math.max(0, Math.min(1000, Number(drafts[o.id] != null ? drafts[o.id] : granted) || 0)); const r = Object.assign({}, runs); r[o.id] = v; const d = Object.assign({}, drafts); d[o.id] = String(v); self.setState({ runs: r, drafts: d }); },
    setTier: e => { const t = Object.assign({}, tiers); t[o.id] = e.target.value; self.setState({ tiers: t }); } }); });
const qp = norm(S.qPeople), qs = norm(S.qSign), qa = norm(S.qAct);
const people = D.people.filter(p => !qp || norm(p.name + ' ' + p.email + ' ' + p.role + ' ' + p.ws).includes(qp)).map(p => Object.assign({}, p, { docs: String(p.docs), reviews: String(p.reviews), tone: p.status === 'Active' ? 'ok' : 'grey' }));
const signins = D.signins.filter(s => !qs || norm(s.who + ' ' + s.how + ' ' + s.device + ' ' + s.ip).includes(qs));
const activity = D.activity.filter(a => !qa || norm(a.who + ' ' + a.what).includes(qa));
return { orgs, showOrgs: P.view !== 'loading' && P.view !== 'empty', people, noPeople: people.length === 0, hasPeople: people.length > 0,
  signins, noSign: signins.length === 0, activity, noAct: activity.length === 0,
  qPeople: S.qPeople || '', setQPeople: e => self.setState({ qPeople: e.target.value }),
  qSign: S.qSign || '', setQSign: e => self.setState({ qSign: e.target.value }), qAct: S.qAct || '', setQAct: e => self.setState({ qAct: e.target.value }),
  updated: self.busy('refresh') ? 'Just now' : 'Just now', spinCls: self.busy('refresh') ? 'spin' : '', refresh: () => self.runBusy('refresh', 1200) };
"""

CLICKS = [
    {"label": "Tier for talk2maq's Workspace", "check": "true", "note": "Change a tier (select) → Runs shows Unlimited"},
    {"css": ".dt .dr .dc[data-th='Runs'] .btn", "check": "document.querySelector('.dt .dr .dc[data-th=\"Runs\"] .faint') !== null", "note": "Set runs"},
    {"label": "Search people…", "check": "true", "note": "Search people"},
    {"text": "Refresh", "check": "document.querySelector('.spin') !== null"},
]


def build(phone=False):
    stem = STEM + ("Phone" if phone else "")
    html = screen(stem, app_shell("admin", BODY), VALS, DATA, {"tiers": {}, "runs": {}, "drafts": {}}, phone=phone)
    return [(stem, html)]
