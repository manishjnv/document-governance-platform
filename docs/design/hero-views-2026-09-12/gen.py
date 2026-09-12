"""ScopeWise hero views, calm-light direction. Three interactive artboards, each
fluid-width with media queries so the same file renders at 1440 and 390."""
import os, json
OUT = os.path.dirname(os.path.abspath(__file__))

HEAD = """<!doctype html>
<html>
<head>
  <meta charset="utf-8">
  <script src="./support.js"></script>
</head>
<body>
<x-dc>
<helmet>
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Instrument+Serif:ital@0;1&family=Instrument+Sans:wght@400;500;600&family=JetBrains+Mono:wght@400;500&display=swap">
<style>
  :root{
    --paper:#FBFAF7; --card:#FFFFFF; --ink:#1B1F27; --ink-2:#4A5361; --ink-3:#7B8494;
    --line:#E8E5DF; --line-2:#D9D5CD; --accent:#2B62C9; --accent-soft:#E9F0FC;
    --crit:#C0392B; --crit-soft:#FBE9E6; --high:#C9701A; --high-soft:#FCEFE2;
    --med:#A88A17; --med-soft:#FAF3D8; --low:#3E7A52; --low-soft:#E5F2E9;
    --ok:#2F7D4F; --ok-soft:#E3F1E7; --na:#EEEBE5;
    --r:10px; --shadow:0 1px 2px rgba(27,31,39,.05), 0 8px 24px -12px rgba(27,31,39,.18);
    --ease:cubic-bezier(.22,.61,.36,1);
  }
  *{box-sizing:border-box}
  body{margin:0;background:var(--paper);color:var(--ink);font-family:"Instrument Sans",system-ui,-apple-system,"Segoe UI",sans-serif;font-size:14px;line-height:1.5;-webkit-font-smoothing:antialiased}
  a{color:var(--accent);text-decoration:none} a:hover{color:#1F4FA8}
  h1,h2{font-family:"Instrument Serif",Georgia,"Times New Roman",serif;font-weight:400;letter-spacing:-.01em;margin:0}
  .mono{font-family:"JetBrains Mono",ui-monospace,Menlo,monospace;font-size:12px}
  .num{font-variant-numeric:tabular-nums}
  .card{background:var(--card);border:1px solid var(--line);border-radius:var(--r);box-shadow:var(--shadow)}
  .btn{display:inline-flex;align-items:center;gap:6px;height:36px;padding:0 14px;border-radius:8px;border:1px solid var(--line-2);background:#fff;color:var(--ink);font:500 13px "Instrument Sans",sans-serif;cursor:pointer;transition:background .18s var(--ease),transform .18s var(--ease),border-color .18s}
  .btn:hover{background:#F4F2EE;transform:translateY(-1px)} .btn:active{transform:translateY(0)}
  .btn.primary{background:var(--accent);border-color:var(--accent);color:#fff} .btn.primary:hover{background:#2456B3}
  .chip{display:inline-flex;align-items:center;gap:6px;height:22px;padding:0 9px;border-radius:999px;font-size:12px;font-weight:600;white-space:nowrap;transition:background .25s var(--ease),color .25s}
  .tip{position:relative}
  .tip::after{content:attr(data-tip);position:absolute;left:50%;bottom:calc(100% + 8px);transform:translate(-50%,4px);background:var(--ink);color:#fff;font:400 12px/1.4 "Instrument Sans",sans-serif;padding:7px 10px;border-radius:7px;white-space:pre-line;width:max-content;max-width:260px;opacity:0;pointer-events:none;transition:opacity .16s var(--ease),transform .16s var(--ease);z-index:20;text-align:left}
  .tip::before{content:"";position:absolute;left:50%;bottom:calc(100% + 3px);transform:translateX(-50%);border:5px solid transparent;border-top-color:var(--ink);opacity:0;transition:opacity .16s}
  .tip:hover::after,.tip:hover::before,.tip:focus-visible::after{opacity:1;transform:translate(-50%,0)}
  .reveal{animation:rise .5s var(--ease) both}
  @keyframes rise{from{opacity:0;transform:translateY(8px)}to{opacity:1;transform:none}}
  .kbd{font:500 11px "JetBrains Mono",monospace;border:1px solid var(--line-2);border-radius:5px;padding:1px 5px;color:var(--ink-3)}
  input[type=range]{-webkit-appearance:none;width:100%;height:4px;border-radius:999px;background:var(--line-2);outline:none}
  input[type=range]::-webkit-slider-thumb{-webkit-appearance:none;width:18px;height:18px;border-radius:999px;background:#fff;border:2px solid var(--accent);box-shadow:var(--shadow);cursor:pointer;transition:transform .15s}
  input[type=range]::-webkit-slider-thumb:hover{transform:scale(1.12)}
</style>
</helmet>
"""
TAIL = "</x-dc>\n{script}\n</body>\n</html>\n"

def topbar(product, title_html, actions_html):
    return f"""
<header style="display:flex;align-items:center;gap:16px;padding:14px clamp(16px,3vw,40px);border-bottom:1px solid var(--line);background:rgba(251,250,247,.85);backdrop-filter:blur(8px);position:sticky;top:0;z-index:10">
  <div style="display:flex;align-items:center;gap:10px;min-width:0">
    <span style="width:26px;height:26px;border-radius:7px;background:var(--ink);display:inline-flex;align-items:center;justify-content:center;flex:none"><svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="#fff" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M12 2l8 3v6c0 5-3.5 9-8 11-4.5-2-8-6-8-11V5z"/></svg></span>
    <span style="font-size:13px;color:var(--ink-3);white-space:nowrap">ScopeWise <span style="color:var(--line-2)">/</span> {product}</span>
  </div>
  <div style="margin-left:auto;display:flex;gap:8px;align-items:center">{actions_html}</div>
</header>
<div style="padding:clamp(16px,2.5vw,32px) clamp(16px,3vw,40px) 8px">{title_html}</div>
"""

# ---------------------------------------------------------------- 1. SOW review
SOW_BODY = topbar("SOW &amp; RFP Review",
 """<div style="display:flex;flex-wrap:wrap;align-items:flex-end;gap:12px 24px">
   <div style="min-width:0"><h1 style="font-size:clamp(24px,2.6vw,34px);line-height:1.15">SOC_SOW_Testing.docx <span style="color:var(--ink-3);font-style:italic">v6</span></h1>
   <div style="font-size:13px;color:var(--ink-2);margin-top:4px">NovaRetail Software Solutions · reviewed 24 Jul 2026 · six reviewers + 40 rules · every finding is pinned to the sentence it came from</div></div>
 </div>""",
 """<button class="btn tip" data-tip="Compare this version with v5: resolved, new and persisting findings">Compare vs v5</button><button class="btn primary">Export report</button>""") + """
<div class="sow-grid" style="display:grid;grid-template-columns:minmax(0,1.5fr) minmax(300px,420px);gap:20px;padding:8px clamp(16px,3vw,40px) 40px">
  <!-- score band -->
  <div class="card reveal" style="grid-column:1/-1;display:grid;grid-template-columns:auto 1fr auto;gap:20px;align-items:center;padding:16px 20px">
    <div class="tip" data-tip="0-100 saturating curve of remaining severity. Lower is better. Recomputes as you mark findings fixed.">
      <div style="font-size:11px;font-weight:600;letter-spacing:.06em;text-transform:uppercase;color:var(--ink-3)">Risk score</div>
      <div class="num" style="font-family:'Instrument Serif',serif;font-size:44px;line-height:1;color:{{scoreColor}};transition:color .4s var(--ease)">{{score}}</div>
    </div>
    <div>
      <div style="display:flex;justify-content:space-between;font-size:12px;color:var(--ink-2);margin-bottom:6px"><span>{{openCount}} open · {{fixedCount}} marked fixed</span><span>{{scoreLabel}}</span></div>
      <div style="height:8px;border-radius:999px;background:var(--na);overflow:hidden"><div style="height:100%;width:{{score}}%;background:{{scoreColor}};transition:width .6s var(--ease),background .4s"></div></div>
      <div style="display:flex;gap:6px;margin-top:10px;flex-wrap:wrap">
        <sc-for list="{{areas}}" as="a" hint-placeholder-count="5">
          <span class="chip tip" data-tip="{{a.tip}}" style="background:{{a.bg}};color:{{a.fg}}">{{a.name}} {{a.n}}</span>
        </sc-for>
      </div>
    </div>
    <button class="btn" onClick="{{resetAll}}">Reset</button>
  </div>

  <!-- document -->
  <div class="card reveal" style="padding:clamp(18px,2.5vw,36px);min-width:0;animation-delay:.05s">
    <div style="font-size:12px;color:var(--ink-3);margin-bottom:14px">Statement of Work · §4 Deliverables and Acceptance</div>
    <sc-for list="{{clauses}}" as="c" hint-placeholder-count="6">
      <div onClick="{{c.pick}}" style="position:relative;padding:10px 14px 10px 18px;margin:0 -14px 4px;border-radius:8px;cursor:pointer;background:{{c.bg}};box-shadow:{{c.ring}};transition:background .3s var(--ease),box-shadow .3s var(--ease)">
        <span style="position:absolute;left:6px;top:12px;bottom:12px;width:3px;border-radius:2px;background:{{c.bar}};transition:background .3s"></span>
        <span class="mono" style="color:var(--ink-3);margin-right:8px">{{c.ref}}</span><span style="font-size:15px;line-height:1.6;color:var(--ink)">{{c.text}}</span>
        <sc-if value="{{c.hasNote}}" hint-placeholder-val="{{true}}">
          <div style="margin-top:8px;display:flex;gap:8px;align-items:center;font-size:12px;color:var(--ink-2)"><span class="chip" style="background:{{c.sevBg}};color:{{c.sevFg}}">{{c.sev}}</span><span>{{c.note}}</span></div>
        </sc-if>
      </div>
    </sc-for>
  </div>

  <!-- findings rail -->
  <div style="display:flex;flex-direction:column;gap:10px;min-width:0">
    <div style="display:flex;align-items:baseline;justify-content:space-between"><span style="font-size:13px;font-weight:600">Findings</span><span style="font-size:12px;color:var(--ink-3)">click one to jump to its sentence</span></div>
    <sc-for list="{{findings}}" as="f" hint-placeholder-count="6">
      <div class="card" onClick="{{f.pick}}" style="padding:12px 14px;cursor:pointer;border-color:{{f.border}};opacity:{{f.opacity}};transform:{{f.shift}};transition:border-color .25s,opacity .3s,transform .3s var(--ease)">
        <div style="display:flex;gap:8px;align-items:center">
          <span class="chip tip" data-tip="{{f.sevTip}}" style="background:{{f.sevBg}};color:{{f.sevFg}}">{{f.sev}}</span>
          <span style="font-weight:600;font-size:13px;flex:1;min-width:0;text-decoration:{{f.strike}}">{{f.title}}</span>
          <span class="mono" style="color:var(--ink-3)">{{f.ref}}</span>
        </div>
        <div style="font-size:12.5px;color:var(--ink-2);margin-top:6px">{{f.why}}</div>
        <div style="display:flex;gap:6px;margin-top:10px;align-items:center">
          <span style="font-size:11px;color:var(--ink-3)">{{f.agent}}</span>
          <button class="btn" onClick="{{f.toggle}}" style="margin-left:auto;height:28px;padding:0 10px;font-size:12px">{{f.action}}</button>
        </div>
      </div>
    </sc-for>
  </div>
</div>
<style>
  @media (max-width:760px){ .sow-grid{grid-template-columns:1fr !important} .sow-grid > .card:first-child{grid-template-columns:auto 1fr !important} .sow-grid > .card:first-child > button{display:none} }
</style>
"""

SOW_SCRIPT = """<script data-dc-script data-props='{"$preview":{"width":1440,"height":900}}'>
class Component extends DCLogic {
  constructor(p){ super(p); this.state = { sel: 2, fixed: {} }; }
  renderVals(){
    const sev = { Critical:{w:25,bg:'var(--crit-soft)',fg:'var(--crit)',tip:'Critical: exposes the buyer to open-ended cost or liability. Severity is LLM-assigned; treat as a first pass.'},
                  Major:{w:12,bg:'var(--high-soft)',fg:'var(--high)',tip:'Major: likely to cause a dispute or scope creep if left as written.'},
                  Medium:{w:6,bg:'var(--med-soft)',fg:'var(--med)',tip:'Medium: ambiguity a reviewer should tighten before signature.'},
                  Low:{w:2,bg:'var(--low-soft)',fg:'var(--low)',tip:'Low: style or completeness note.'} };
    const F = [
      {id:1, ref:'§4.1', sev:'Major',    title:'Deliverables lack acceptance criteria', why:'"to the reasonable satisfaction of the Client" is undefined; no test, sign-off window or default acceptance.', agent:'Scope reviewer', area:'Scope'},
      {id:2, ref:'§4.2', sev:'Critical', title:'Unlimited change requests at no cost', why:'"including but not limited to" plus no change-control clause means any addition is in scope for the fixed price.', agent:'Commercial reviewer', area:'Commercial'},
      {id:3, ref:'§4.3', sev:'Medium',   title:'Timeline uses "approximately"', why:'Milestone dates are non-binding; no dependency on Client inputs is stated.', agent:'Delivery reviewer', area:'Delivery'},
      {id:4, ref:'§4.4', sev:'Major',    title:'No liability cap referenced', why:'Clause relies on an MSA that is not attached or named.', agent:'Legal reviewer', area:'Legal'},
      {id:5, ref:'§4.5', sev:'Low',      title:'Reporting cadence unspecified', why:'"regular status updates" has no frequency or format.', agent:'PMO reviewer', area:'Governance'},
      {id:6, ref:'§4.6', sev:'Medium',   title:'Data handling clause is silent on residency', why:'Customer PII is processed; no region, retention or deletion terms.', agent:'Security reviewer', area:'Security'},
    ];
    const C = [
      {ref:'4.1', fid:1, text:'The Supplier shall deliver the Platform to the reasonable satisfaction of the Client.'},
      {ref:'4.2', fid:2, text:'The Services include, but are not limited to, the items listed in Schedule A, and the Supplier shall accommodate Client requests as they arise.'},
      {ref:'4.3', fid:3, text:'Milestones will be completed approximately in line with the dates in Schedule B.'},
      {ref:'4.4', fid:4, text:'Liability shall be governed by the parties\\u2019 master agreement.'},
      {ref:'4.5', fid:5, text:'The Supplier will provide regular status updates to the Client.'},
      {ref:'4.6', fid:6, text:'The Supplier may process customer data as required to perform the Services.'},
    ];
    const fixed = this.state.fixed, sel = this.state.sel;
    const open = F.filter(f=>!fixed[f.id]);
    const sum = open.reduce((s,f)=>s+sev[f.sev].w,0);
    const score = Math.round(100*(1-Math.exp(-0.0086*sum*4)));
    const scoreColor = score>=60?'var(--crit)':score>=35?'var(--high)':score>=15?'var(--med)':'var(--ok)';
    const scoreLabel = score>=60?'Do not sign as written':score>=35?'Negotiate before signature':score>=15?'Minor edits':'Ready to sign';
    const areaNames = ['Scope','Commercial','Delivery','Legal','Governance','Security'];
    const areas = areaNames.map(n=>{ const k=open.filter(f=>f.area===n).length; return {name:n,n:k,bg:k?'var(--accent-soft)':'var(--na)',fg:k?'var(--accent)':'var(--ink-3)',tip:k?k+' open finding'+(k>1?'s':'')+' in '+n:'No open findings in '+n}; });
    const findings = F.map(f=>{ const isSel=sel===f.id, isFixed=!!fixed[f.id]; const s=sev[f.sev];
      return {...f, sevBg:s.bg, sevFg:s.fg, sevTip:s.tip, border:isSel?'var(--accent)':'var(--line)', opacity:isFixed?.55:1, shift:isSel?'translateX(-2px)':'none',
        strike:isFixed?'line-through':'none', action:isFixed?'Reopen':'Mark fixed',
        pick:()=>this.setState({sel:f.id}), toggle:(e)=>{ e&&e.stopPropagation&&e.stopPropagation(); const nx={...fixed}; if(nx[f.id]) delete nx[f.id]; else nx[f.id]=true; this.setState({fixed:nx, sel:f.id}); } }; });
    const clauses = C.map(c=>{ const f=F.find(x=>x.id===c.fid); const isSel=sel===f.id, isFixed=!!fixed[f.id]; const s=sev[f.sev];
      return {ref:'\\u00a7'+c.ref, text:c.text, hasNote:isSel, note:f.why, sev:f.sev, sevBg:s.bg, sevFg:s.fg,
        bg:isSel?(isFixed?'var(--ok-soft)':s.bg):'transparent', ring:isSel?'0 0 0 1px '+(isFixed?'var(--ok)':s.fg)+' inset':'none', bar:isFixed?'var(--ok)':(isSel?s.fg:'var(--line-2)'),
        pick:()=>this.setState({sel:f.id}) }; });
    return { score, scoreColor, scoreLabel, openCount:open.length, fixedCount:F.length-open.length, areas, findings, clauses, resetAll:()=>this.setState({fixed:{},sel:2}) };
  }
}
</script>"""

# ---------------------------------------------------------------- 2. MITRE heatmap
MITRE_BODY = topbar("MITRE ATT&amp;CK Coverage",
 """<div style="display:flex;flex-wrap:wrap;align-items:flex-end;gap:12px 24px">
   <div><h1 style="font-size:clamp(24px,2.6vw,34px);line-height:1.15">abc ltd <span style="color:var(--ink-3);font-style:italic">coverage over eight runs</span></h1>
   <div style="font-size:13px;color:var(--ink-2);margin-top:4px">Drag the timeline or press play. Cells that turn green were covered by a rule added in that run. Coverage measures presence, not efficacy.</div></div>
 </div>""",
 """<button class="btn tip" data-tip="Navigator layer, XLSX tracker, PPTX deck, PDF">Export</button><button class="btn primary">New run</button>""") + """
<div style="padding:8px clamp(16px,3vw,40px) 40px;display:flex;flex-direction:column;gap:16px">
  <div class="card reveal" style="padding:16px 20px;display:grid;grid-template-columns:auto 1fr auto;gap:20px;align-items:center" id="band">
    <div class="tip" data-tip="Covered techniques divided by applicable techniques. N/A techniques leave the denominator with a printed reason.">
      <div style="font-size:11px;font-weight:600;letter-spacing:.06em;text-transform:uppercase;color:var(--ink-3)">Coverage · {{runLabel}}</div>
      <div class="num" style="font-family:'Instrument Serif',serif;font-size:44px;line-height:1;transition:color .4s">{{pct}}%</div>
      <div style="font-size:12px;color:var(--ink-2)">{{covered}} of {{applicable}} applicable · <span style="color:{{deltaColor}}">{{delta}}</span></div>
    </div>
    <div style="min-width:0">
      <div style="display:flex;justify-content:space-between;font-size:12px;color:var(--ink-3);margin-bottom:8px"><span>Aug 2</span><span>Sep 8</span></div>
      <input type="range" min="0" max="7" value="{{run}}" onInput="{{onSlide}}" onChange="{{onSlide}}" aria-label="Run timeline">
      <div style="display:flex;justify-content:space-between;margin-top:6px">
        <sc-for list="{{ticks}}" as="t" hint-placeholder-count="8"><span class="tip" data-tip="{{t.tip}}" onClick="{{t.pick}}" style="width:8px;height:8px;border-radius:999px;background:{{t.bg}};cursor:pointer;transition:background .3s,transform .2s;transform:{{t.scale}}"></span></sc-for>
      </div>
    </div>
    <button class="btn" onClick="{{togglePlay}}">{{playLabel}}</button>
  </div>

  <div class="card reveal" style="padding:clamp(12px,2vw,20px);animation-delay:.05s;min-width:0">
    <div style="display:flex;gap:14px;flex-wrap:wrap;align-items:center;font-size:12px;color:var(--ink-2);margin-bottom:12px">
      <span style="display:inline-flex;align-items:center;gap:6px"><i style="width:10px;height:10px;border-radius:3px;background:var(--ok)"></i>Covered</span>
      <span style="display:inline-flex;align-items:center;gap:6px"><i style="width:10px;height:10px;border-radius:3px;background:#E3B53A"></i>Partial</span>
      <span style="display:inline-flex;align-items:center;gap:6px"><i style="width:10px;height:10px;border-radius:3px;background:var(--crit-soft);border:1px solid #F1C2BB"></i>Not covered</span>
      <span style="display:inline-flex;align-items:center;gap:6px"><i style="width:10px;height:10px;border-radius:3px;background:var(--na)"></i>N/A</span>
      <span style="margin-left:auto;color:var(--ink-3)">hover a cell for the rule that covers it</span>
    </div>
    <div style="display:grid;grid-template-columns:repeat(auto-fit,minmax(150px,1fr));gap:10px">
      <sc-for list="{{tactics}}" as="t" hint-placeholder-count="8">
        <div style="min-width:0">
          <div style="display:flex;justify-content:space-between;align-items:baseline;font-size:12px;font-weight:600;margin-bottom:6px"><span style="white-space:nowrap;overflow:hidden;text-overflow:ellipsis">{{t.name}}</span><span class="num" style="color:var(--ink-3);font-weight:500">{{t.count}}</span></div>
          <div style="display:flex;flex-direction:column;gap:4px">
            <sc-for list="{{t.cells}}" as="c" hint-placeholder-count="7">
              <div class="tip" data-tip="{{c.tip}}" style="height:26px;border-radius:5px;background:{{c.bg}};color:{{c.fg}};border:1px solid {{c.border}};font:500 11px 'JetBrains Mono',monospace;display:flex;align-items:center;padding:0 8px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis;transition:background .45s var(--ease),color .45s,transform .25s var(--ease)">{{c.id}}</div>
            </sc-for>
          </div>
        </div>
      </sc-for>
    </div>
  </div>
</div>
<style>@media (max-width:760px){ #band{grid-template-columns:1fr !important} }</style>
"""

MITRE_SCRIPT = """<script data-dc-script data-props='{"$preview":{"width":1440,"height":900}}'>
class Component extends DCLogic {
  constructor(p){ super(p); this.state={ run:7, playing:false }; this.timer=null; }
  componentWillUnmount(){ if(this.timer) clearInterval(this.timer); }
  renderVals(){
    const T = [
      ['Initial Access',['T1078','T1133','T1190','T1195','T1566','T1091','T1200']],
      ['Execution',['T1059','T1053','T1047','T1204','T1569','T1106','T1129']],
      ['Persistence',['T1098','T1136','T1543','T1547','T1546','T1037','T1556']],
      ['Privilege Esc.',['T1055','T1068','T1548','T1484','T1134','T1574','T1611']],
      ['Defense Evasion',['T1027','T1070','T1562','T1036','T1218','T1553','T1112']],
      ['Credential Access',['T1003','T1110','T1552','T1555','T1557','T1558','T1621']],
      ['Lateral Movement',['T1021','T1080','T1210','T1219','T1570','T1550','T1563']],
      ['Exfiltration',['T1041','T1048','T1567','T1020','T1030','T1052','T1537']],
    ];
    // when each cell became covered (run index 0-7), 9 = never, 'p'+n partial from run n, 'na' not applicable
    const S = {T1078:0,T1133:5,T1190:2,T1195:9,T1566:1,T1091:9,T1200:'na',
      T1059:0,T1053:1,T1047:3,T1204:9,T1569:6,T1106:9,T1129:'na',
      T1098:2,T1136:2,T1543:'p4',T1547:3,T1546:9,T1037:9,T1556:7,
      T1055:1,T1068:9,T1548:'p2',T1484:4,T1134:9,T1574:9,T1611:'na',
      T1027:2,T1070:0,T1562:5,T1036:9,T1218:6,T1553:9,T1112:3,
      T1003:0,T1110:1,T1552:9,T1555:9,T1557:9,T1558:4,T1621:7,
      T1021:0,T1080:9,T1210:9,T1219:9,T1570:9,T1550:5,T1563:9,
      T1041:6,T1048:9,T1567:9,T1020:9,T1030:9,T1052:'na',T1537:7};
    const RULES = {T1078:'Rule 12 · Impossible travel sign-in',T1133:'Rule 141 · VPN from new geo',T1190:'Rule 33 · WAF exploit signature',T1566:'Rule 4 · Phishing URL click',T1059:'Rule 8 · PowerShell encoded command',T1053:'Rule 21 · Scheduled task created',T1047:'Rule 77 · WMI remote exec',T1569:'Rule 150 · Service installed',T1098:'Rule 40 · Account manipulation',T1136:'Rule 41 · Local account created',T1547:'Rule 62 · Run key added',T1556:'Rule 171 · Auth package change',T1055:'Rule 15 · Process injection (EDR)',T1484:'Rule 90 · GPO modified',T1027:'Rule 44 · Obfuscated script',T1070:'Rule 2 · Event log cleared',T1562:'Rule 132 · Defender disabled',T1218:'Rule 152 · Signed binary proxy',T1112:'Rule 66 · Registry persistence',T1003:'Rule 1 · LSASS access',T1110:'Rule 9 · Brute force',T1558:'Rule 88 · Kerberoasting',T1621:'Rule 170 · MFA fatigue',T1021:'Rule 5 · RDP lateral',T1550:'Rule 139 · Pass-the-hash',T1041:'Rule 155 · C2 exfil volume',T1537:'Rule 173 · Cloud storage transfer'};
    const dates=['Aug 2','Aug 9','Aug 16','Aug 21','Aug 27','Sep 1','Sep 5','Sep 8'];
    const run=this.state.run;
    let covered=0, applicable=0;
    const tactics=T.map(([name,ids])=>{ let n=0; const cells=ids.map(id=>{ const s=S[id]; let state='no';
        if(s==='na') state='na'; else if(typeof s==='string'){ if(run>=+s.slice(1)) state='partial'; } else if(s<=run) state='cov';
        if(state!=='na') applicable++; if(state==='cov'){covered++;n++;}
        const bg=state==='cov'?'var(--ok)':state==='partial'?'#E3B53A':state==='na'?'var(--na)':'var(--crit-soft)';
        const fg=state==='cov'?'#fff':state==='na'?'var(--ink-3)':state==='partial'?'#3A2E05':'#8B2E24';
        const border=state==='no'?'#F1C2BB':'transparent';
        const tip=state==='cov'?id+' covered since '+dates[S[id]]+'\\n'+RULES[id]:state==='partial'?id+' partial: rule exists but a required log source is missing':state==='na'?id+' not applicable: platform absent from your inventory':id+' not covered. Ranked in Gaps & roadmap.';
        return {id,bg,fg,border,tip}; });
      return {name,cells,count:n+'/'+ids.filter(i=>S[i]!=='na').length}; });
    const pct=Math.round(1000*covered/applicable)/10;
    const prev=run>0?(()=>{ let c=0,a=0; T.forEach(([_,ids])=>ids.forEach(id=>{const s=S[id]; if(s==='na')return; a++; if(typeof s==='number'&&s<=run-1)c++;})); return Math.round(1000*c/a)/10; })():pct;
    const d=Math.round((pct-prev)*10)/10;
    const ticks=dates.map((dt,i)=>({tip:'Run '+(i+1)+' · '+dt+(i===run?' (shown)':''),bg:i<=run?'var(--accent)':'var(--line-2)',scale:i===run?'scale(1.5)':'scale(1)',pick:()=>this.setState({run:i})}));
    return { run, runLabel:'run '+(run+1)+' · '+dates[run], pct, covered, applicable, delta:(d>=0?'+':'')+d+' pts vs previous run', deltaColor:d>0?'var(--ok)':d<0?'var(--crit)':'var(--ink-3)',
      tactics, ticks, playLabel:this.state.playing?'Pause':'Play timeline',
      onSlide:(e)=>this.setState({run:+e.target.value}),
      togglePlay:()=>{ if(this.state.playing){ clearInterval(this.timer); this.timer=null; this.setState({playing:false}); return; }
        this.setState({playing:true, run:0}); this.timer=setInterval(()=>{ const r=this.state.run; if(r>=7){ clearInterval(this.timer); this.timer=null; this.setState({playing:false}); } else this.setState({run:r+1}); },700); } };
  }
}
</script>"""

# ---------------------------------------------------------------- 3. Exploit chains
CODE_BODY = topbar("Code Security Review",
 """<div style="display:flex;flex-wrap:wrap;align-items:flex-end;gap:12px 24px">
   <div><h1 style="font-size:clamp(24px,2.6vw,34px);line-height:1.15">NodeGoat <span style="color:var(--ink-3);font-style:italic">six exploit chains, three fixes</span></h1>
   <div style="font-size:13px;color:var(--ink-2);margin-top:4px">Each path is an attacker's route from entry to remote code execution. Click a finding to fix it and watch which chains break. Findings are AI-generated triage candidates; confirm before acting.</div></div>
 </div>""",
 """<button class="btn" onClick="{{suggest}}">Fewest fixes</button><button class="btn" onClick="{{reset}}">Reset</button><button class="btn primary">Export deck</button>""") + """
<div class="code-grid" style="display:grid;grid-template-columns:minmax(0,1.6fr) minmax(280px,380px);gap:20px;padding:8px clamp(16px,3vw,40px) 40px">
  <div class="card reveal" style="padding:16px;min-width:0;overflow:hidden">
    <div style="display:flex;justify-content:space-between;align-items:baseline;margin-bottom:8px;flex-wrap:wrap;gap:8px">
      <span style="font-size:13px;font-weight:600">Attack graph</span>
      <span style="font-size:12px;color:var(--ink-2)"><span class="num" style="font-weight:600;color:{{brokenColor}}">{{broken}}</span> of 6 chains broken · {{fixedN}} fixes applied</span>
    </div>
    <svg viewBox="0 0 900 420" style="width:100%;height:auto;display:block" aria-label="Exploit chain graph">
      <defs><marker id="arr" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7" orient="auto-start-reverse"><path d="M0 0L10 5L0 10z" fill="context-stroke"/></marker></defs>
      <text x="20" y="28" font-size="11" fill="#7B8494" font-family="Instrument Sans" letter-spacing=".06em">ENTRY</text>
      <text x="380" y="28" font-size="11" fill="#7B8494" font-family="Instrument Sans" letter-spacing=".06em">PIVOT</text>
      <text x="740" y="28" font-size="11" fill="#7B8494" font-family="Instrument Sans" letter-spacing=".06em">IMPACT</text>
      <sc-for list="{{edges}}" as="e" hint-placeholder-count="8">
        <path d="{{e.d}}" fill="none" stroke="{{e.stroke}}" stroke-width="{{e.w}}" stroke-dasharray="{{e.dash}}" marker-end="url(#arr)" style="transition:stroke .4s,stroke-width .3s"></path>
      </sc-for>
      <sc-for list="{{nodes}}" as="n" hint-placeholder-count="10">
        <g onClick="{{n.toggle}}" style="cursor:pointer">
          <rect x="{{n.x}}" y="{{n.y}}" width="150" height="46" rx="9" fill="{{n.fill}}" stroke="{{n.stroke}}" stroke-width="1.5" style="transition:fill .35s,stroke .35s"></rect>
          <text x="{{n.tx}}" y="{{n.ty1}}" font-size="11" font-family="JetBrains Mono" fill="{{n.idFill}}">#{{n.id}} · {{n.sev}}</text>
          <text x="{{n.tx}}" y="{{n.ty2}}" font-size="12" font-family="Instrument Sans" font-weight="600" fill="{{n.tFill}}" style="text-decoration:{{n.deco}}">{{n.title}}</text>
          <title>{{n.tip}}</title>
        </g>
      </sc-for>
    </svg>
  </div>
  <div style="display:flex;flex-direction:column;gap:10px;min-width:0">
    <div style="display:flex;align-items:baseline;justify-content:space-between"><span style="font-size:13px;font-weight:600">Chains</span><span style="font-size:12px;color:var(--ink-3)">a chain breaks when any step is fixed</span></div>
    <sc-for list="{{chains}}" as="c" hint-placeholder-count="6">
      <div class="card reveal" style="padding:12px 14px;border-left:3px solid {{c.edge}};opacity:{{c.op}};transition:border-color .35s,opacity .35s">
        <div style="display:flex;gap:8px;align-items:center;flex-wrap:wrap"><span class="chip" style="background:{{c.bg}};color:{{c.fg}}">{{c.state}}</span><span style="font-weight:600;font-size:13px;text-decoration:{{c.deco}}">{{c.title}}</span></div>
        <div style="display:flex;gap:6px;margin-top:8px;flex-wrap:wrap;align-items:center;font-size:12px;color:var(--ink-3)">
          <sc-for list="{{c.steps}}" as="s" hint-placeholder-count="3"><span class="mono tip" data-tip="{{s.tip}}" onClick="{{s.toggle}}" style="padding:2px 7px;border-radius:5px;background:{{s.bg}};color:{{s.fg}};cursor:pointer;transition:background .3s">#{{s.id}}</span></sc-for>
        </div>
      </div>
    </sc-for>
    <div style="font-size:11px;color:var(--ink-3);margin-top:4px">Findings produced by Visa Vulnerability Agentic Harness (Apache-2.0). ScopeWise is not affiliated with Visa, Inc.</div>
  </div>
</div>
<style>@media (max-width:760px){ .code-grid{grid-template-columns:1fr !important} }</style>
"""

CODE_SCRIPT = """<script data-dc-script data-props='{"$preview":{"width":1440,"height":900}}'>
class Component extends DCLogic {
  constructor(p){ super(p); this.state={ fixed:{} }; }
  renderVals(){
    const N = {
      3:{title:'NoSQL injection in login',sev:'Critical',col:0,row:0,file:'app/data/user-dao.js:92'},
      4:{title:'Hardcoded session secret',sev:'Critical',col:0,row:1,file:'config/env/all.js:8'},
      24:{title:'Username enumeration',sev:'Medium',col:0,row:2,file:'app/routes/session.js:53'},
      9:{title:'Authenticated SSRF',sev:'High',col:0,row:3,file:'app/routes/research.js:14'},
      21:{title:'Outdated marked (XSS)',sev:'Medium',col:0,row:4,file:'package.json'},
      5:{title:'No rate limit on login',sev:'Critical',col:1,row:1,file:'app/routes/session.js:53'},
      22:{title:'Cookie lacks httpOnly',sev:'Medium',col:1,row:3,file:'server.js:60'},
      7:{title:'Eval injection (RCE)',sev:'High',col:2,row:1,file:'app/routes/index.js:50'},
      1:{title:'Unauthenticated MongoDB',sev:'Critical',col:2,row:3,file:'docker-compose.yml:8'},
    };
    const CH = [
      {t:'NoSQLi login bypass → RCE',steps:[3,7]},
      {t:'Hardcoded secret → forged session → RCE',steps:[4,7]},
      {t:'Enumeration + brute force → RCE',steps:[24,5,7]},
      {t:'SSRF → open MongoDB',steps:[9,1]},
      {t:'Stored XSS → cookie theft → RCE',steps:[21,22,7]},
      {t:'Weak password policy → brute force → RCE',steps:[5,7]},
    ];
    const fixed=this.state.fixed;
    const sevFill={Critical:'var(--crit-soft)',High:'var(--high-soft)',Medium:'var(--med-soft)'}, sevStroke={Critical:'#E7A79F',High:'#EBC59A',Medium:'#E4D38F'}, sevText={Critical:'var(--crit)',High:'var(--high)',Medium:'var(--med)'};
    const X=[30,390,750], Y=[48,120,192,264,336];
    const pos=id=>({x:X[N[id].col],y:Y[N[id].row]});
    const isBroken=c=>c.steps.some(s=>fixed[s]);
    const toggle=id=>()=>{ const nx={...fixed}; if(nx[id]) delete nx[id]; else nx[id]=true; this.setState({fixed:nx}); };
    const nodes=Object.keys(N).map(k=>{ const id=+k, n=N[id], p=pos(id), f=!!fixed[id];
      return {id, sev:n.sev, title:n.title, x:p.x, y:p.y, tx:p.x+12, ty1:p.y+18, ty2:p.y+35,
        fill:f?'var(--ok-soft)':sevFill[n.sev], stroke:f?'var(--ok)':sevStroke[n.sev], idFill:f?'var(--ok)':sevText[n.sev], tFill:f?'var(--ink-3)':'var(--ink)', deco:f?'line-through':'none',
        tip:(f?'FIXED · ':'')+'#'+id+' '+n.title+'\\n'+n.file+'\\nClick to '+(f?'reopen':'mark fixed'), toggle:toggle(id)}; });
    const edges=[]; CH.forEach(c=>{ for(let i=0;i<c.steps.length-1;i++){ const a=pos(c.steps[i]), b=pos(c.steps[i+1]); const broken=fixed[c.steps[i]]||fixed[c.steps[i+1]]||isBroken(c);
        const x1=a.x+150,y1=a.y+23,x2=b.x,y2=b.y+23, mx=(x1+x2)/2;
        edges.push({d:'M'+x1+' '+y1+' C '+mx+' '+y1+', '+mx+' '+y2+', '+x2+' '+y2, stroke:broken?'#C9CDD4':'#1B1F27', w:broken?1.2:2, dash:broken?'4 5':'0'}); } });
    const broken=CH.filter(isBroken).length;
    const chains=CH.map(c=>{ const b=isBroken(c); return {title:c.t, state:b?'Broken':'Open', bg:b?'var(--ok-soft)':'var(--crit-soft)', fg:b?'var(--ok)':'var(--crit)', edge:b?'var(--ok)':'var(--crit)', op:b?.75:1, deco:b?'line-through':'none',
      steps:c.steps.map(s=>({id:s, bg:fixed[s]?'var(--ok-soft)':'var(--na)', fg:fixed[s]?'var(--ok)':'var(--ink-2)', tip:'#'+s+' '+N[s].title+'\\n'+N[s].file, toggle:toggle(s)}))}; });
    return { nodes, edges, chains, broken, fixedN:Object.keys(fixed).length, brokenColor:broken===6?'var(--ok)':broken?'var(--high)':'var(--crit)',
      suggest:()=>this.setState({fixed:{7:true,1:true}}), reset:()=>this.setState({fixed:{}}) };
  }
}
</script>"""

def build(body, script): return HEAD + body + TAIL.format(script=script)

files = {
 "Main.dc.html": build(SOW_BODY, SOW_SCRIPT),
 "MitreTimeline.dc.html": build(MITRE_BODY, MITRE_SCRIPT),
 "ExploitChains.dc.html": build(CODE_BODY, CODE_SCRIPT),
 "SowPhone.dc.html": build(SOW_BODY, SOW_SCRIPT.replace('"width":1440,"height":900','"width":390,"height":844')),
 "MitrePhone.dc.html": build(MITRE_BODY, MITRE_SCRIPT.replace('"width":1440,"height":900','"width":390,"height":844')),
 "ChainsPhone.dc.html": build(CODE_BODY, CODE_SCRIPT.replace('"width":1440,"height":900','"width":390,"height":844')),
}
for n,s in files.items(): open(os.path.join(OUT,n),"w",encoding="utf-8").write(s)

canvas = {
 "artboards":[
  {"file":"Main.dc.html","title":"SOW review · annotated document","x":0,"y":0,"w":1440,"h":900,"expand":"fill","is_interactive":True},
  {"file":"SowPhone.dc.html","title":"SOW review · phone","x":1540,"y":0,"w":390,"h":844,"expand":"fill","is_interactive":True},
  {"file":"MitreTimeline.dc.html","title":"MITRE · living heatmap over runs","x":0,"y":1060,"w":1440,"h":900,"expand":"fill","is_interactive":True},
  {"file":"MitrePhone.dc.html","title":"MITRE · phone","x":1540,"y":1060,"w":390,"h":844,"expand":"fill","is_interactive":True},
  {"file":"ExploitChains.dc.html","title":"Code review · exploit chain graph","x":0,"y":2120,"w":1440,"h":900,"expand":"fill","is_interactive":True},
  {"file":"ChainsPhone.dc.html","title":"Code review · phone","x":1540,"y":2120,"w":390,"h":844,"expand":"fill","is_interactive":True},
 ],
 "annotations":[
  {"id":"refs","x":2020,"y":0,"w":420,"text":"References held against: Linear (restraint, motion that explains), Attio (light, data-dense), Vercel (type and whitespace), Wiz (security graph), Notion (annotated document).\n\nSystem: Instrument Serif for headlines, Instrument Sans for UI, JetBrains Mono for IDs. Warm paper #FBFAF7, ink #1B1F27, one accent #2B62C9, severity ramp critical/high/medium/low each with a soft tint. 10px radius, one shadow, one easing curve (.22,.61,.36,1)."},
  {"id":"interact","x":2020,"y":300,"w":420,"text":"Everything is live. SOW: click a finding or a sentence to pin them together; Mark fixed and the risk score, bar and area chips recompute with transitions. MITRE: drag the timeline, click a dot, or press Play; cells turn green in the run that covered them, hover any cell for the rule. Code: click a node or a step chip to fix it; edges through it go dashed and chains flip to Broken; Fewest fixes applies the set-cover result (#7 and #1 break all six).\n\nHover any chip, cell or button for a tooltip. Phone frames are the same files at 390px: the grid stacks, the score band collapses, the heatmap auto-fits columns."},
  {"id":"next","x":2020,"y":700,"w":420,"text":"Not designed yet on purpose: shells, navigation, tables, settings. Once a hero direction is approved the rest inherits this system. Open questions: keep serif headlines in the product (bolder identity) or reserve serif for marketing; dark mode as a system toggle later."}
 ],
 "launch":{"view":"focused","file":"Main.dc.html"}
}
json.dump(canvas, open(os.path.join(OUT,"canvas.json"),"w"), indent=1)
print("ok", list(files))
