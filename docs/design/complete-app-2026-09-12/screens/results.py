"""/results/[reviewId] -- Review results. Source: inventory/sow.md §3.

Sample findings/clause texts lifted from docs/design/hero-views-2026-09-12/gen.py
(SOW_BODY/SOW_SCRIPT); risk recompute reuses that file's saturating-curve formula.
"""
from dc import T, app_shell, screen, btn, icon, esc

STEM = "Results"
PAGE, TITLE, ORDER = "sow", "Review results", 30

ARROWLEFT = icon("arrow-left", 14)
FILETEXT = icon("file-text", 14)
CHEVRON = icon("chevron-right", 13)
CHECK12 = icon("check", 12)
CHECK14 = icon("check", 14)
ROTATE14 = icon("rotate", 14)
MAPPIN13 = icon("map-pin", 13)
HELP14 = icon("help", 14)

DATA = {
    "meta": {"filename": "SOC_SOW_Testing.docx", "project": "NovaRetail Software Solutions", "doc_type": "SOW", "pages": 14, "uploaded": "24 Jul 2026"},
    "overall_score": 34.5,
    "sections": [
        {"id": "1", "heading": "1. Scope of Work", "page": 1,
         "text": "This Statement of Work is issued under the Master Services Agreement between the parties and describes the Platform implementation services to be provided by the Supplier."},
        {"id": "2", "heading": "2. Term and Termination", "page": 2,
         "text": "This SOW commences on the Effective Date and continues until all Deliverables have been accepted, unless terminated earlier in accordance with the Agreement."},
        {"id": "3", "heading": "3. Fees and Payment", "page": 3,
         "text": "Client shall pay the fixed price set out in Schedule A within thirty (30) days of receipt of a correct invoice."},
        {"id": "4.1", "heading": "4.1 Deliverables and Acceptance", "page": 4, "text": "The Supplier shall deliver the Platform to the reasonable satisfaction of the Client."},
        {"id": "4.2", "heading": "4.2 Change Requests", "page": 4, "text": "The Services include, but are not limited to, the items listed in Schedule A, and the Supplier shall accommodate Client requests as they arise."},
        {"id": "4.3", "heading": "4.3 Delivery Timeline", "page": 4, "text": "Milestones will be completed approximately in line with the dates in Schedule B."},
        {"id": "4.4", "heading": "4.4 Liability", "page": 5, "text": "Liability shall be governed by the parties’ master agreement."},
        {"id": "4.5", "heading": "4.5 Reporting", "page": 5, "text": "The Supplier will provide regular status updates to the Client."},
        {"id": "4.6", "heading": "4.6 Data Handling", "page": 5, "text": "The Supplier may process customer data as required to perform the Services."},
    ],
    "gaps": [
        "No Data Processing Agreement or data residency clause found",
        "Limitation of Liability section is missing a cap amount",
        "Change Control / Variation procedure is not defined",
    ],
    "findings": [
        {"id": 1, "ref": "4.1", "section_ref": "§4.1", "severity": "Major", "area": "Scope", "evidence_type": "ambiguous_term",
         "title": "Deliverables lack acceptance criteria",
         "description": "\"to the reasonable satisfaction of the Client\" is undefined; no test, sign-off window or default acceptance is stated. See §4.4 for the related liability gap.",
         "recommendation": "Add a defined acceptance test, sign-off window, and a default-acceptance clause if the Client does not respond within a stated period.",
         "confidence": 92},
        {"id": 2, "ref": "4.2", "section_ref": "§4.2", "severity": "Critical", "area": "Commercial", "evidence_type": "unbounded_commitment",
         "title": "Unlimited change requests at no cost",
         "description": "\"including but not limited to\" plus no change-control clause means any addition is in scope for the fixed price.",
         "recommendation": "Cap change requests under a named change-control procedure with pricing for additional units of work.",
         "confidence": 88},
        {"id": 3, "ref": "4.3", "section_ref": "§4.3", "severity": "Medium", "area": "Delivery", "evidence_type": "non_binding_language",
         "title": "Timeline uses \"approximately\"",
         "description": "Milestone dates are non-binding; no dependency on Client inputs is stated.",
         "recommendation": "Replace \"approximately\" with fixed milestone dates and name any Client-side dependencies that could shift them.",
         "confidence": 81},
        {"id": 4, "ref": "4.4", "section_ref": "§4.4", "severity": "Major", "area": "Legal", "evidence_type": "missing_reference",
         "title": "No liability cap referenced",
         "description": "Clause relies on an MSA that is not attached or named.",
         "recommendation": "Attach the referenced master agreement or restate the liability cap directly in this document.",
         "confidence": 90},
        {"id": 5, "ref": "4.5", "section_ref": "§4.5", "severity": "Low", "area": "Governance", "evidence_type": "unspecified_frequency",
         "title": "Reporting cadence unspecified",
         "description": "\"regular status updates\" has no frequency or format.",
         "recommendation": "Specify a reporting frequency and format, e.g. weekly written status reports.",
         "confidence": 76},
        {"id": 6, "ref": "4.6", "section_ref": "§4.6", "severity": "Medium", "area": "Security", "evidence_type": "missing_clause",
         "title": "Data handling clause is silent on residency",
         "description": "Customer PII is processed; no region, retention or deletion terms.",
         "recommendation": "Add a data residency, retention and deletion clause covering where customer data is stored and processed.",
         "confidence": 84},
    ],
    "audit": {"models": "Scope, Delivery, Commercial, Security, PMO, Legal", "rules_version": "12.3", "doc_sha256": "9f3a7c2e1b08", "build": "e42f9a1c"},
}


def help_btn(tip):
    return T('<button class="btn ghost icon sm tip" aria-label="What does this mean?" data-tip="[[t]]">[[ic]]</button>', t=esc(tip), ic=HELP14)


# ----------------------------------------------------------------------------- scorecards
OVERALL_CARD = T("""
<div class="card" style="padding:16px">
  <div class="row between"><span class="lbl">Overall Score</span>[[help]]</div>
  <div class="num" style="font-size:28px;font-weight:600;color:{{overallColor}};margin-top:2px">{{overallVal}}</div>
  <div class="bar" role="progressbar" aria-label="Overall score" aria-valuenow="{{overallRound}}" aria-valuemin="0" aria-valuemax="100" style="margin-top:10px">
    <i style="width:{{overallVal}}%;background:{{overallFill}}"></i>
  </div>
</div>""", help=help_btn("How complete and well-written this document is (0-100), across scope, clarity, commercial terms, delivery, and more. Higher is better."))

RISK_CARD = T("""
<div class="card" style="padding:16px">
  <div class="row between"><span class="lbl">Risk Level</span>[[help]]</div>
  <div class="row" style="gap:10px;align-items:baseline;margin-top:2px">
    <span id="risk-value" class="num" style="font-size:28px;font-weight:600;color:{{riskColor}}">{{riskPct}}%</span>
    <span class="chip {{riskTone}}">{{riskBand}}</span>
  </div>
  <div style="font-size:11px;color:var(--ink3);margin-top:8px">{{openCount}} open &middot; {{fixedCount}} marked fixed</div>
</div>""", help=help_btn("How much this document could hurt you if signed as-is -- combines how severe the issues are and how many there are. Higher is worse."))

# ----------------------------------------------------------------------------- risk by area
AREA_ROW = T("""
<button class="arearow" data-area-row="{{a.name}}" aria-pressed="{{a.pressed}}" style="box-shadow:{{a.ring}}" onClick="{{a.pick}}">
  <span style="width:88px;flex:none;text-align:left;font-size:12.5px;font-weight:500">{{a.name}}</span>
  <span class="bar" style="flex:1"><i style="width:{{a.val}};background:{{a.fill}}"></i></span>
  <span class="num" style="width:36px;text-align:right;font-size:12.5px;font-weight:600">{{a.val}}</span>
</button>""")

AREA_CARD = T("""
<div class="card">
  <div class="card-h"><h3 class="tip" data-tip="[[tip]]">Risk by Area</h3>
    <sc-if value="{{areaFilterActive}}" hint-placeholder-val="{{false}}"><button id="clear-area-filter" class="btn link sm" onClick="{{clearAreaFilter}}">clear filter</button></sc-if>
  </div>
  <div class="card-b stack" style="gap:6px">
    <sc-for list="{{areas}}" as="a" hint-placeholder-count="7">[[row]]</sc-for>
  </div>
</div>""", tip=esc("The same risk score, split by area (Legal, Commercial, Delivery, etc.) so you can see what's actually driving it. Click an area to filter the findings below to just that area."), row=AREA_ROW)

# ----------------------------------------------------------------------------- x-ray
XRAY_CARD = T("""
<div class="card">
  <div class="card-h"><h3 class="tip" data-tip="[[tip]]">Document X-Ray</h3></div>
  <div class="card-b grid g2" style="gap:18px">
    <div>
      <div class="lbl" style="margin-bottom:8px">Sections Found ({{sectionsCount}})</div>
      <div class="stack" style="gap:5px"><sc-for list="{{sections}}" as="s" hint-placeholder-count="6"><div style="font-size:12.5px">{{s.heading}} (p.{{s.page}})</div></sc-for></div>
    </div>
    <div>
      <div class="lbl" style="margin-bottom:8px">Gaps Detected ({{gapsCount}})</div>
      <sc-if value="{{hasGaps}}" hint-placeholder-val="{{true}}"><div class="stack" style="gap:5px"><sc-for list="{{gaps}}" as="g" hint-placeholder-count="3"><div style="font-size:12.5px;color:var(--crit)">{{g.text}}</div></sc-for></div></sc-if>
      <sc-if value="{{noGaps}}" hint-placeholder-val="{{false}}"><div class="sub" style="font-size:12.5px">None -- passes all rule checks.</div></sc-if>
    </div>
  </div>
</div>""", tip=esc("A quick scan of the document itself: which sections it has, and which required sections/checks are missing."))

# ----------------------------------------------------------------------------- findings summary
SEV_TILE = T("""
<button class="kpi click" data-sev-tile="{{t.sev}}" aria-pressed="{{t.pressed}}" style="box-shadow:{{t.ring}}" onClick="{{t.pick}}">
  <span class="lbl">{{t.sev}}</span><span class="v num" style="color:{{t.color}}">{{t.n}}</span>
</button>""")

SUMMARY_CARD = T("""
<div class="card">
  <div class="card-h"><h3 class="tip" data-tip="[[tip]]">Findings Summary</h3>
    <sc-if value="{{sevFilterActive}}" hint-placeholder-val="{{false}}"><button id="clear-sev-filter" class="btn link sm" onClick="{{clearSevFilter}}">clear filter</button></sc-if>
  </div>
  <div class="card-b grid g5" style="gap:10px">
    <sc-for list="{{sevTiles}}" as="t" hint-placeholder-count="5">[[tile]]</sc-for>
  </div>
</div>""", tip=esc("Every issue found, grouped by how serious it is. Click a number to filter the list below to just that severity."), tile=SEV_TILE)

# ----------------------------------------------------------------------------- findings list
DESC_PART = T("""
<sc-if value="{{p.link}}" hint-placeholder-val="{{false}}"><button class="btn link tip" data-tip="{{p.headingTip}}" onClick="{{p.jump}}" style="display:inline;vertical-align:baseline">[[mp]] {{p.t}}</button></sc-if>
<sc-if value="{{p.notLink}}" hint-placeholder-val="{{true}}">{{p.t}}</sc-if>""", mp=icon("map-pin", 12))

FINDING_ROW = T("""
<div class="card findingrow rise" data-finding-id="{{f.id}}" style="padding:0;overflow:hidden;opacity:{{f.rowOpacity}};background:{{f.tintBg}}">
  <div class="frow-toggle" role="button" tabindex="0" aria-expanded="{{f.aria}}" onClick="{{f.toggleOpen}}">
    <span class="row wrap" style="gap:8px;flex:1;min-width:0;text-align:left">
      <span style="display:inline-flex;align-items:center;height:16px;padding:0 6px;border-radius:4px;font-size:9px;font-weight:700;text-transform:uppercase;letter-spacing:.04em;background:{{f.sevSolid}};color:#fff">{{f.severity}}</span>
      <span class="chip outline xs">{{f.area}}</span>
      <sc-if value="{{f.isFixed}}" hint-placeholder-val="{{false}}"><span class="chip ok xs">[[check12]] Fixed</span></sc-if>
      <span class="chip grey xs">{{f.evidenceLabel}}</span>
      <span style="font-weight:600;font-size:13px;text-decoration:{{f.strike}}">{{f.title}}</span>
    </span>
    <span class="row" style="gap:8px;flex:none">
      <button class="jumpbtn btn ghost sm tip" data-tip="{{f.jumpTip}}" onClick="{{f.jump}}">[[mp]] {{f.section_ref}}</button>
      <span style="display:inline-flex;transition:transform .15s;transform:{{f.rot}}">[[chev]]</span>
    </span>
  </div>
  <sc-if value="{{f.open}}" hint-placeholder-val="{{false}}">
  <div style="padding:0 14px 14px" onClick="{{stop}}">
    <div class="lbl" style="margin-top:6px">Description</div>
    <p style="font-size:13px;line-height:1.6;margin-top:3px"><sc-for list="{{f.descParts}}" as="p" hint-placeholder-count="1">[[descpart]]</sc-for></p>
    <sc-if value="{{f.hasMatchedText}}" hint-placeholder-val="{{true}}">
      <div class="lbl" style="margin-top:10px">Document Text</div>
      <blockquote class="sub" style="margin:3px 0 0;padding:8px 12px;border-left:3px solid var(--line2);font-size:13px;font-style:italic">{{f.matchedText}}</blockquote>
    </sc-if>
    <div class="lbl" style="margin-top:10px">Recommendation</div>
    <p style="font-size:13px;line-height:1.6;margin-top:3px">{{f.recommendation}}</p>
    <div class="row between" style="margin-top:12px">
      <span class="lbl">Confidence <span class="num" style="color:var(--ink);font-weight:600;letter-spacing:0;text-transform:none">{{f.confidence}}%</span></span>
      <sc-if value="{{f.isFixed}}" hint-placeholder-val="{{false}}"><button class="fixbtn btn sm" onClick="{{f.toggleFixed}}">[[rot]] Reopen</button></sc-if>
      <sc-if value="{{f.notFixed}}" hint-placeholder-val="{{true}}"><button class="fixbtn btn sm primary" onClick="{{f.toggleFixed}}">[[chk]] Mark Fixed</button></sc-if>
    </div>
  </div>
  </sc-if>
</div>""", check12=CHECK12, mp=MAPPIN13, chev=CHEVRON, descpart=DESC_PART, rot=ROTATE14, chk=CHECK14)

FINDINGS_CARD = T("""
<div class="card findpane">
  <div class="card-h"><h3>Findings <sc-if value="{{isFiltered}}" hint-placeholder-val="{{false}}">{{countSuffix}}</sc-if></h3></div>
  <div class="card-b stack" style="gap:10px">
    <sc-if value="{{hasFindings}}" hint-placeholder-val="{{true}}"><sc-for list="{{findingsView}}" as="f" hint-placeholder-count="3">[[row]]</sc-for></sc-if>
    <sc-if value="{{noFindings}}" hint-placeholder-val="{{false}}"><p class="empty">No findings in this filter.</p></sc-if>
  </div>
</div>""", row=FINDING_ROW)

# ----------------------------------------------------------------------------- document pane
DOC_SECTION = T("""
<div class="secitem {{s.hl}}" id="sec-{{s.id}}">
  <div class="row between" style="gap:8px"><span style="font-weight:600;font-size:13px">{{s.heading}}</span><span class="faint num" style="font-size:11px">p.{{s.page}}</span></div>
  <p class="sub" style="font-size:12.5px;white-space:pre-wrap;margin-top:4px">{{s.text}}</p>
</div>""")

DOC_PANE = T("""
<aside class="card docpane docwrap" style="padding:16px">
  <h3 style="margin-bottom:10px">Document</h3>
  <div class="stack" style="gap:2px"><sc-for list="{{sections}}" as="s" hint-placeholder-count="6">[[row]]</sc-for></div>
</aside>""", row=DOC_SECTION)

SPLIT = T("""
<div class="rsplit">
  <div class="findpane-wrap" style="flex:{{findBasis}} 1 0%;min-width:0">[[findings]]</div>
  <sc-if value="{{docShown}}" hint-placeholder-val="{{true}}">
    <div class="split-grip" role="separator" aria-orientation="vertical" tabindex="0" aria-label="Resize document pane (drag, or use arrow keys)"
         onPointerDown="{{gDown}}" onPointerMove="{{gMove}}" onPointerUp="{{gUp}}"><i></i></div>
    <div style="flex:{{docBasis}} 1 0%;min-width:0">[[doc]]</div>
  </sc-if>
</div>""", findings=FINDINGS_CARD, doc=DOC_PANE)

# ----------------------------------------------------------------------------- page body
HEADER = T("""
<div class="pagehead">
  <div><h1>Review Results</h1><p class="sub" style="font-size:13px;margin-top:4px"><b>{{meta.filename}}</b> &middot; Project: {{meta.project}} &middot; {{meta.docType}} &middot; {{pagesLabel}} &middot; Uploaded {{meta.uploaded}}</p></div>
  <a href="#" class="btn ghost sm">[[al]] Back to Dashboard</a>
</div>
<div class="row wrap" style="gap:8px;margin-bottom:18px">
  <button id="doc-toggle-btn" class="btn sm" onClick="{{toggleDoc}}">[[ft]] {{docBtnLabel}}</button>
  [[dl]][[vr]]
</div>""", al=ARROWLEFT, ft=FILETEXT, dl=btn("Download PDF", "", "download", size="sm"), vr=btn("View Full Report", "primary", size="sm"))

FOOTER = '<p style="font-size:11px;color:var(--ink3);margin-top:16px">Models: {{audit.models}} &middot; Rules {{audit.rulesVersion}} &middot; Doc SHA-256 {{audit.sha}}&hellip; &middot; Build {{audit.build}}</p>'

DEFAULT_BODY = T("""
[[header]]
<div class="grid g2" style="gap:14px;margin-bottom:14px">[[overall]][[risk]]</div>
<div class="grid g2" style="gap:14px;margin-bottom:14px;align-items:start">[[area]][[xray]]</div>
<div style="margin-bottom:14px">[[summary]]</div>
[[split]]
[[footer]]""", header=HEADER, overall=OVERALL_CARD, risk=RISK_CARD, area=AREA_CARD, xray=XRAY_CARD, summary=SUMMARY_CARD, split=SPLIT, footer=FOOTER)

LOADING = '<p class="sub" style="text-align:center;padding:64px 0">Loading review...</p>'
ERROR = T("""<div class="empty" style="padding:56px 24px"><h3>Review not found</h3><a href="#" class="btn sm" style="margin-top:10px;display:inline-flex">[[al]] Back to Dashboard</a></div>""", al=ARROWLEFT)

BODY = T("""
<sc-if value="{{is.default}}" hint-placeholder-val="{{true}}">[[def]]</sc-if>
<sc-if value="{{is.loading}}" hint-placeholder-val="{{false}}">[[loading]]</sc-if>
<sc-if value="{{is.empty}}" hint-placeholder-val="{{false}}">[[def]]</sc-if>
<sc-if value="{{is.error}}" hint-placeholder-val="{{false}}">[[error]]</sc-if>""", **{"def": DEFAULT_BODY, "loading": LOADING, "error": ERROR})

EXTRA_CSS = """
<style>
.frow-toggle{all:unset;box-sizing:border-box;display:flex;align-items:center;justify-content:space-between;gap:10px;width:100%;padding:12px 14px;cursor:pointer}
.frow-toggle:hover{background:rgba(20,24,31,.04)}
.arearow{all:unset;box-sizing:border-box;display:flex;align-items:center;gap:10px;width:100%;padding:6px;border-radius:8px;cursor:pointer}
.arearow:hover{background:#F6F4EF}
.rsplit{display:flex;gap:16px;align-items:flex-start}
.split-grip{align-self:stretch;width:14px;cursor:col-resize;touch-action:none;display:flex;align-items:center;justify-content:center;flex:none}
.split-grip i{width:4px;height:40px;border-radius:999px;background:var(--line2);display:block}
.split-grip:hover i,.split-grip:focus-visible i{background:var(--accent)}
.docpane{position:sticky;top:16px;max-height:calc(100vh - 32px);overflow:auto}
.secitem{transition:background .5s ease;border-radius:6px;padding:8px;margin:0 -8px}
.secitem.hl{background:#FFF8E6}
@media (max-width:760px){
  .rsplit{flex-direction:column}
  .split-grip{display:none}
  .docpane{position:static;max-height:none}
}
</style>"""

VALS = r"""
const sevTone = { Critical:'crit', Major:'high', Medium:'med', Low:'low', Info:'info' };
const sevFillTok = { Critical:'var(--crit-fill)', Major:'var(--high-fill)', Medium:'var(--med-fill)', Low:'var(--low-fill)', Info:'var(--info-fill)' };
const sevSoft = { Critical:'var(--crit-soft)', Major:'var(--high-soft)', Medium:'var(--med-soft)', Low:'var(--low-soft)', Info:'var(--info-soft)' };
const sevWeight = { Critical:25, Major:12, Medium:6, Low:2, Info:0 };

const fixed = S.fixed || {};
const sevFilter = S.sevFilter || null;
const areaFilter = S.areaFilter || null;
const docShown = S.docShown !== false;
const jumpRef = S.jumpRef || null;
const split = S.split == null ? 33 : S.split;

const secByRef = {};
D.sections.forEach(function(s){ secByRef[s.id] = s; });

const curve = (sum) => Math.round(100 * (1 - Math.exp(-0.0344 * sum)));

const jumpTo = (ref) => (e) => {
  if (e && e.stopPropagation) e.stopPropagation();
  self.setIn(['jumpRef'], ref);
  setTimeout(() => { if (self.state.jumpRef === ref) self.setIn(['jumpRef'], null); }, 2000);
  const el = document.getElementById('sec-' + ref);
  if (el && el.scrollIntoView) el.scrollIntoView({ behavior: 'smooth', block: 'center' });
};

const linkify = (text) => {
  const re = /(§\d+\.\d+|Section \d+\.\d+|Appendix [A-Z])/g;
  const out = []; let last = 0, m;
  while ((m = re.exec(text))) {
    if (m.index > last) out.push({ t: text.slice(last, m.index), link: false, notLink: true });
    const raw = m[0], ref = raw.replace(/^§|^Section /, '').trim();
    const sec = secByRef[ref];
    out.push({ t: raw, link: true, notLink: false, headingTip: 'Jump to "' + (sec ? sec.heading : raw) + '" in the document', jump: jumpTo(ref) });
    last = m.index + raw.length;
  }
  if (last < text.length) out.push({ t: text.slice(last), link: false, notLink: true });
  return out;
};

const findingsAll = D.findings.map(f => Object.assign({}, f, { isFixed: !!fixed[f.id] }));
const openWeight = findingsAll.filter(f => !f.isFixed).reduce((s, f) => s + sevWeight[f.severity], 0);
const riskPct = curve(openWeight);
const riskColor = riskPct > 70 ? 'var(--crit)' : riskPct > 40 ? 'var(--med)' : 'var(--ok)';
const riskBand = riskPct > 70 ? 'High' : riskPct > 40 ? 'Medium' : 'Low';
const riskTone = riskPct > 70 ? 'crit' : riskPct > 40 ? 'med' : 'ok';
const openCount = findingsAll.filter(f => !f.isFixed).length;
const fixedCount = findingsAll.length - openCount;

const overall = D.overall_score;
const overallColor = overall >= 80 ? 'var(--ok)' : overall >= 60 ? 'var(--med)' : 'var(--crit)';
const overallFill = overall >= 80 ? 'var(--ok)' : overall >= 60 ? 'var(--med-fill)' : 'var(--crit-fill)';

const AREA_NAMES = ['Compliance', 'Security', 'Governance', 'Scope', 'Legal', 'Commercial', 'Delivery'];
let areas = AREA_NAMES.map(name => {
  const w = findingsAll.filter(f => !f.isFixed && f.area === name).reduce((s, f) => s + sevWeight[f.severity], 0);
  const pct = curve(w);
  const on = areaFilter === name;
  return { name, val: pct + '%', fill: pct > 70 ? 'var(--crit-fill)' : pct > 40 ? 'var(--med-fill)' : 'var(--ok)',
    pressed: on ? 'true' : 'false', ring: on ? '0 0 0 2px var(--accent-soft)' : 'none', _pct: pct,
    pick: () => self.setIn(['areaFilter'], on ? null : name) };
});
areas = areas.sort((a, b) => b._pct - a._pct);

const SEVS = ['Critical', 'Major', 'Medium', 'Low', 'Info'];
const sevTiles = SEVS.map(s => {
  const n = findingsAll.filter(f => f.severity === s).length;
  const on = sevFilter === s;
  return { sev: s, n, pressed: on ? 'true' : 'false', ring: on ? '0 0 0 2px var(--accent-soft)' : 'none', color: sevFillTok[s],
    pick: () => self.setIn(['sevFilter'], on ? null : s) };
});

const filtered = findingsAll.filter(f => (!sevFilter || f.severity === sevFilter) && (!areaFilter || f.area === areaFilter));
const isFiltered = !!(sevFilter || areaFilter);

const findingsView = filtered.map(f => {
  const open = self.isOpen('finding:' + f.id);
  const sec = secByRef[f.ref];
  const matchedText = sec ? sec.text : '';
  return Object.assign({}, f, {
    sevSolid: sevFillTok[f.severity], tintBg: sevSoft[f.severity],
    evidenceLabel: f.evidence_type.replace(/_/g, ' '),
    open, aria: open ? 'true' : 'false', rot: open ? 'rotate(90deg)' : 'none',
    strike: f.isFixed ? 'line-through' : 'none', rowOpacity: f.isFixed ? '.6' : '1',
    notFixed: !f.isFixed,
    toggleOpen: () => self.toggleOpen('finding:' + f.id),
    jump: jumpTo(f.ref), jumpTip: 'Jump to "' + (sec ? sec.heading : f.section_ref) + '" in the document',
    hasMatchedText: !!matchedText, matchedText,
    descParts: linkify(f.description),
    toggleFixed: (e) => { if (e && e.stopPropagation) e.stopPropagation(); const nx = Object.assign({}, fixed); if (nx[f.id]) delete nx[f.id]; else nx[f.id] = true; self.setState({ fixed: nx }); },
  });
});

const sections = D.sections.map(s => ({ id: s.id, heading: s.heading, page: s.page, text: s.text, hl: jumpRef === s.id ? 'hl' : '' }));
const findBasis = docShown ? split : 100;

return {
  meta: { filename: D.meta.filename, project: D.meta.project, docType: D.meta.doc_type, uploaded: D.meta.uploaded },
  pagesLabel: D.meta.pages + (D.meta.pages === 1 ? ' page' : ' pages'),
  overallVal: overall.toFixed(1), overallRound: Math.round(overall), overallColor, overallFill,
  riskPct, riskColor, riskBand, riskTone, openCount, fixedCount,
  areas, areaFilterActive: !!areaFilter, clearAreaFilter: () => self.setIn(['areaFilter'], null),
  sevTiles, sevFilterActive: !!sevFilter, clearSevFilter: () => self.setIn(['sevFilter'], null),
  sections, sectionsCount: sections.length,
  gaps: D.gaps.map(g => ({ text: g })), gapsCount: D.gaps.length, hasGaps: D.gaps.length > 0, noGaps: D.gaps.length === 0,
  findingsView, isFiltered, countSuffix: '(' + filtered.length + ' of ' + findingsAll.length + ')',
  hasFindings: filtered.length > 0, noFindings: filtered.length === 0,
  docShown, toggleDoc: () => self.setIn(['docShown'], !docShown), docBtnLabel: docShown ? 'Hide Document' : 'Show Document',
  findBasis, docBasis: 100 - split,
  gDown: (e) => { e.currentTarget.setPointerCapture(e.pointerId); self._drag = { kind: 'split', x0: e.clientX, w0: split, cw: e.currentTarget.parentElement.getBoundingClientRect().width || 900 }; },
  gMove: (e) => { if (!self._drag || self._drag.kind !== 'split') return; const d = e.clientX - self._drag.x0; const pct = 100 * d / self._drag.cw; self.setIn(['split'], Math.max(20, Math.min(80, Math.round(self._drag.w0 + pct)))); },
  gUp: () => { self._drag = null; },
  audit: { models: D.audit.models, rulesVersion: D.audit.rules_version, sha: D.audit.doc_sha256, build: D.audit.build },
};
"""

CLICKS = [
    {"css": '[data-finding-id="2"] .frow-toggle', "check": 'document.querySelector(\'[data-finding-id="2"] blockquote\') !== null'},
    {"css": '[data-finding-id="2"] .fixbtn', "check": "document.getElementById('risk-value').textContent.trim() === '73%'"},
    {"css": '[data-sev-tile="Critical"]', "check": "document.querySelectorAll('.findingrow').length === 1"},
    {"css": "#clear-sev-filter", "check": "document.querySelectorAll('.findingrow').length === 6"},
    {"css": '[data-area-row="Scope"]', "check": "document.querySelectorAll('.findingrow').length === 1"},
    {"css": "#clear-area-filter", "check": "document.querySelectorAll('.findingrow').length === 6"},
    {"css": '[data-finding-id="2"] .jumpbtn', "check": "document.getElementById('sec-4.2').classList.contains('hl')"},
    {"css": "#doc-toggle-btn", "check": "document.querySelector('.docpane') === null"},
    {"css": "#doc-toggle-btn", "check": "document.querySelector('.findpane-wrap').style.flexGrow === '33'"},
]


def build(phone=False):
    stem = STEM + ("Phone" if phone else "")
    state = {"fixed": {}, "sevFilter": None, "areaFilter": None, "docShown": True, "jumpRef": None, "split": 33}
    html = screen(stem, app_shell("dashboard", BODY, wide=True), VALS, DATA, state, extra_css=EXTRA_CSS, phone=phone)
    return [(stem, html)]
