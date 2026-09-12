"""Generates the ScopeWise app redesign artboards (.dc.html) from one shared shell.
Tokens lifted from apps/web/app/globals.css + tailwind.config.ts + components/ui/*."""
import os, json
OUT = os.path.dirname(os.path.abspath(__file__))

FG="#0F1729"; MUTED="#404F64"; BORDER="#E1E7EF"; SOFT="#F3F5F7"; PRIMARY="#0066CC"
DANGER="#DB3344"; SUCCESS="#28A745"; WARNING="#FFC107"; INFO="#17A2B8"; SUBTLE="#6B7A90"

CSS = f"""
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap">
<style>
  body {{ margin:0; font-family: Inter, system-ui, -apple-system, 'Segoe UI', sans-serif; color:{FG}; background:#fff; font-size:14px; line-height:1.45; -webkit-font-smoothing:antialiased; }}
  a {{ color:{PRIMARY}; text-decoration:none; }} a:hover {{ color:#0052a3; }}
  .num {{ font-variant-numeric: tabular-nums; }}
  .mono {{ font-family: ui-monospace, 'JetBrains Mono', Menlo, monospace; font-size:12px; }}
  table {{ border-collapse:collapse; width:100%; }}
  th {{ text-align:left; font-size:11px; font-weight:600; letter-spacing:.04em; text-transform:uppercase; color:{SUBTLE}; padding:10px 12px; border-bottom:1px solid {BORDER}; background:#FAFBFC; }}
  td {{ padding:11px 12px; border-bottom:1px solid {BORDER}; font-size:13px; vertical-align:middle; }}
  td.num, th {{ white-space:nowrap; }}
  tr.hover td {{ background:{SOFT}; }}
  th.r, td.r {{ text-align:right; }}
</style>
"""

def icon(name, size=16, color="currentColor"):
    p = {
     "file": '<path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/><path d="M14 2v6h6"/><path d="M8 13h8M8 17h8"/>',
     "target": '<circle cx="12" cy="12" r="10"/><circle cx="12" cy="12" r="6"/><circle cx="12" cy="12" r="2"/>',
     "bug": '<path d="M8 2l1.5 2M16 2l-1.5 2"/><rect x="6" y="6" width="12" height="14" rx="6"/><path d="M12 6v14M2 13h4M18 13h4M3 20l3-2M21 20l-3-2M3 6l3 2M21 6l-3 2"/>',
     "shield": '<path d="M12 2l8 3v6c0 5-3.5 9-8 11-4.5-2-8-6-8-11V5z"/><path d="M9 12l2 2 4-4"/>',
     "search": '<circle cx="11" cy="11" r="7"/><path d="M20 20l-3.5-3.5"/>',
     "bell": '<path d="M6 8a6 6 0 0 1 12 0c0 7 3 9 3 9H3s3-2 3-9"/><path d="M10 21h4"/>',
     "chev": '<path d="M6 9l6 6 6-6"/>',
     "plus": '<path d="M12 5v14M5 12h14"/>',
     "down": '<path d="M12 3v12M6 11l6 6 6-6"/><path d="M4 21h16"/>',
     "more": '<circle cx="5" cy="12" r="1.5"/><circle cx="12" cy="12" r="1.5"/><circle cx="19" cy="12" r="1.5"/>',
     "upload": '<path d="M12 21V9M6 15l6-6 6 6"/><path d="M4 3h16"/>',
     "filter": '<path d="M3 5h18l-7 8v6l-4 2v-8z"/>',
     "cmd": '<path d="M9 9V6a3 3 0 1 0-3 3h12a3 3 0 1 0-3-3v12a3 3 0 1 0 3-3H6a3 3 0 1 0 3 3z"/>',
     "up": '<path d="M12 19V5M5 12l7-7 7 7"/>',
     "dn": '<path d="M12 5v14M5 12l7 7 7-7"/>',
     "link": '<path d="M10 14a4 4 0 0 0 5.7 0l3-3a4 4 0 0 0-5.7-5.7l-1 1"/><path d="M14 10a4 4 0 0 0-5.7 0l-3 3a4 4 0 0 0 5.7 5.7l1-1"/>',
     "users": '<circle cx="9" cy="8" r="4"/><path d="M2 21a7 7 0 0 1 14 0"/><path d="M16 4a4 4 0 0 1 0 8M22 21a7 7 0 0 0-5-6.7"/>',
     "grid": '<rect x="3" y="3" width="7" height="7" rx="1"/><rect x="14" y="3" width="7" height="7" rx="1"/><rect x="3" y="14" width="7" height="7" rx="1"/><rect x="14" y="14" width="7" height="7" rx="1"/>',
     "list": '<path d="M8 6h13M8 12h13M8 18h13"/><circle cx="4" cy="6" r="1"/><circle cx="4" cy="12" r="1"/><circle cx="4" cy="18" r="1"/>',
     "check": '<path d="M5 12l5 5L20 7"/>',
     "clock": '<circle cx="12" cy="12" r="9"/><path d="M12 7v5l3 2"/>',
     "logout": '<path d="M10 17l5-5-5-5M15 12H3"/><path d="M13 3h6v18h-6"/>',
    }[name]
    return f'<svg width="{size}" height="{size}" viewBox="0 0 24 24" fill="none" stroke="{color}" stroke-width="1.75" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">{p}</svg>'

def pill(text, tone):
    t = {"red":("#FDECEE",DANGER),"amber":("#FFF6D6","#8A6100"),"green":("#E8F6EC","#1E7A35"),"blue":("#E6F0FA",PRIMARY),"grey":(SOFT,MUTED),"purple":("#EFE9FA","#5B3FA3")}[tone]
    return f'<span style="display:inline-flex; align-items:center; gap:6px; height:22px; padding:0 8px; border-radius:999px; background:{t[0]}; color:{t[1]}; font-size:12px; font-weight:600; white-space:nowrap;">{text}</span>'

def dot_pill(text, tone):
    t = {"red":DANGER,"amber":"#D98E00","green":"#1E7A35","blue":PRIMARY,"grey":SUBTLE}[tone]
    return f'<span style="display:inline-flex; align-items:center; gap:6px; font-size:13px; font-weight:500; color:{FG};"><span style="width:8px; height:8px; border-radius:999px; background:{t}; display:inline-block;"></span>{text}</span>'

def btn(label, kind="primary", ico=None, size=36):
    st = {"primary": f"background:{PRIMARY}; color:#fff; border:1px solid {PRIMARY};",
          "outline": f"background:#fff; color:{FG}; border:1px solid {BORDER};",
          "ghost": f"background:transparent; color:{MUTED}; border:1px solid transparent;"}[kind]
    i = (icon(ico, 15) + " ") if ico else ""
    return f'<button style="display:inline-flex; align-items:center; gap:6px; height:{size}px; padding:0 12px; border-radius:6px; font: 500 13px Inter, sans-serif; cursor:pointer; white-space:nowrap; {st}">{i}{label}</button>'

def sidebar(active):
    def item(label, ico, key):
        on = key == active
        bg = PRIMARY if on else "transparent"; col = "#fff" if on else MUTED
        return f'<a href="#" style="display:flex; align-items:center; gap:10px; padding:8px 12px; border-radius:6px; font-size:14px; font-weight:500; color:{col}; background:{bg};">{icon(ico,16,col)}{label}</a>'
    def group(title, items):
        return f'<div style="display:flex; flex-direction:column; gap:2px;"><div style="font-size:11px; font-weight:600; letter-spacing:.06em; text-transform:uppercase; color:{SUBTLE}; padding:0 12px 6px;">{title}</div>{"".join(items)}</div>'
    return f'''
<aside style="width:224px; flex:none; height:900px; border-right:1px solid {BORDER}; background:#fff; display:flex; flex-direction:column; padding:16px 12px; box-sizing:border-box;">
  <div style="display:flex; align-items:center; gap:10px; padding:4px 8px 18px;">
    <div style="width:28px; height:28px; border-radius:7px; background:{PRIMARY}; display:flex; align-items:center; justify-content:center;">{icon("shield",16,"#fff")}</div>
    <div><div style="font-weight:600; font-size:14px; line-height:1.1;">ScopeWise</div><div style="font-size:11px; color:{SUBTLE};">Wipro Practice</div></div>
  </div>
  <div style="display:flex; flex-direction:column; gap:20px;">
    {group("Products",[item("SOW &amp; RFP Review","file","sow"),item("MITRE ATT&amp;CK Coverage","target","mitre"),item("Code Security Review","bug","code")])}
    {group("Organisation",[item("Admin","shield","admin"),item("People","users","people")])}
  </div>
  <div style="margin-top:auto; display:flex; flex-direction:column; gap:10px;">
    <div style="border:1px solid {BORDER}; border-radius:8px; padding:10px 12px; display:flex; flex-direction:column; gap:4px;">
      <div style="display:flex; justify-content:space-between; align-items:center;"><span style="font-size:12px; font-weight:600;">AI credit</span>{pill("Low","amber")}</div>
      <div style="height:6px; border-radius:999px; background:{SOFT}; overflow:hidden;"><div style="width:31%; height:100%; background:{WARNING};"></div></div>
      <div style="font-size:11px; color:{SUBTLE};">$7.85 of $25.00 remaining</div>
    </div>
    <div style="display:flex; align-items:center; gap:10px; padding:6px 8px;">
      <div style="width:28px; height:28px; border-radius:999px; background:#DCE6F2; color:{PRIMARY}; font-size:12px; font-weight:600; display:flex; align-items:center; justify-content:center;">MK</div>
      <div style="min-width:0;"><div style="font-size:13px; font-weight:500; line-height:1.1;">Manish Kumar</div><div style="font-size:11px; color:{SUBTLE};">Platform admin</div></div>
      <span style="margin-left:auto; color:{SUBTLE};">{icon("logout",15)}</span>
    </div>
  </div>
</aside>'''

def topbar(crumbs):
    c = ' <span style="color:#B7C1CE;">/</span> '.join(f'<span style="color:{"inherit" if i==len(crumbs)-1 else SUBTLE};">{x}</span>' for i,x in enumerate(crumbs))
    return f'''
<div style="height:48px; border-bottom:1px solid {BORDER}; display:flex; align-items:center; gap:16px; padding:0 24px; background:#fff;">
  <div style="font-size:13px; font-weight:500;">{c}</div>
  <div style="margin-left:auto; display:flex; align-items:center; gap:10px;">
    <div style="display:flex; align-items:center; gap:8px; height:32px; width:340px; padding:0 10px; border:1px solid {BORDER}; border-radius:6px; color:{SUBTLE}; font-size:13px; background:#fff; overflow:hidden;">{icon("search",15,SUBTLE)}<span style="white-space:nowrap;">Search documents, assessments, findings…</span><span style="margin-left:auto; font-size:11px; border:1px solid {BORDER}; border-radius:4px; padding:1px 5px;">⌘K</span></div>
    {pill("Production","grey")}
    <span style="color:{MUTED}; display:flex;">{icon("bell",17)}</span>
  </div>
</div>'''

def header(title, sub, actions):
    return f'''
<div style="display:flex; align-items:flex-start; justify-content:space-between; gap:24px; margin-bottom:20px;">
  <div><h1 style="margin:0; font-size:22px; font-weight:600; letter-spacing:-.01em;">{title}</h1><div style="font-size:13px; color:{MUTED}; margin-top:4px;">{sub}</div></div>
  <div style="display:flex; gap:8px; align-items:center;">{actions}</div>
</div>'''

def spark(points, color=PRIMARY, w=72, h=22):
    mx=max(points); mn=min(points); rng=(mx-mn) or 1
    pts=" ".join(f"{i*(w/(len(points)-1)):.1f},{h-(p-mn)/rng*(h-3)-1.5:.1f}" for i,p in enumerate(points))
    return f'<svg width="{w}" height="{h}" viewBox="0 0 {w} {h}" aria-hidden="true"><polyline points="{pts}" fill="none" stroke="{color}" stroke-width="1.5" stroke-linejoin="round"/></svg>'

def kpi(label, value, sub, delta=None, tone="blue", sp=None):
    dl = ""
    if delta:
        up = delta.startswith("+") or delta.startswith("▲")
        col = "#1E7A35" if (up and tone!="inv") or (not up and tone=="inv") else DANGER
        dl = f'<span style="font-size:12px; font-weight:600; color:{col};">{delta}</span>'
    return f'''<div style="border:1px solid {BORDER}; border-radius:8px; background:#fff; padding:14px 16px; display:flex; flex-direction:column; gap:6px; min-width:0;">
  <div style="font-size:11px; font-weight:600; letter-spacing:.04em; text-transform:uppercase; color:{SUBTLE};">{label}</div>
  <div style="display:flex; align-items:baseline; gap:8px;"><span class="num" style="font-size:26px; font-weight:600; letter-spacing:-.02em;">{value}</span>{dl}</div>
  <div style="display:flex; align-items:center; justify-content:space-between; gap:8px;"><span style="font-size:12px; color:{MUTED};">{sub}</span>{sp or ""}</div>
</div>'''

def bar(pct, color=PRIMARY, w=120):
    return f'<div style="display:inline-flex; align-items:center; gap:8px;"><div style="width:{w}px; height:6px; border-radius:999px; background:{SOFT}; overflow:hidden;"><div style="width:{pct}%; height:100%; background:{color};"></div></div><span class="num" style="font-size:12px; color:{MUTED}; min-width:36px;">{pct}%</span></div>'

def shell(active, crumbs, body):
    return f'''<!doctype html>
<html>
<head>
  <meta charset="utf-8">
  <script src="./support.js"></script>
</head>
<body>
<x-dc>
<helmet>{CSS}</helmet>
<div style="width:1440px; height:900px; display:flex; background:#F7F8FA; overflow:hidden;">
  {sidebar(active)}
  <div style="flex:1; min-width:0; display:flex; flex-direction:column;">
    {topbar(crumbs)}
    <div style="padding:24px 28px; flex:1; overflow:hidden;">{body}</div>
  </div>
</div>
</x-dc>
</body>
</html>'''

def tabs(items, active):
    out=[]
    for t in items:
        on = t==active
        out.append(f'<span style="padding:0 2px 10px; font-size:13px; font-weight:{600 if on else 500}; color:{FG if on else MUTED}; border-bottom:2px solid {PRIMARY if on else "transparent"};">{t}</span>')
    return f'<div style="display:flex; gap:22px; border-bottom:1px solid {BORDER}; margin-bottom:16px;">{"".join(out)}</div>'

def seg(items, active):
    out=[]
    for t in items:
        on=t==active
        out.append(f'<span style="padding:0 10px; height:30px; display:inline-flex; align-items:center; border-radius:5px; font-size:13px; font-weight:500; color:{FG if on else MUTED}; background:{"#fff" if on else "transparent"}; box-shadow:{"0 1px 2px rgba(15,23,41,.12)" if on else "none"};">{t}</span>')
    return f'<div style="display:inline-flex; gap:2px; padding:3px; background:{SOFT}; border-radius:7px;">{"".join(out)}</div>'

def card(title, body, extra=""):
    return f'<div style="border:1px solid {BORDER}; border-radius:8px; background:#fff; overflow:hidden;"><div style="display:flex; align-items:center; justify-content:space-between; padding:12px 16px; border-bottom:1px solid {BORDER};"><span style="font-size:13px; font-weight:600;">{title}</span>{extra}</div>{body}</div>'

# ---------- 1. SOW Review dashboard ----------
def sow():
    kpis = f'''<div style="display:grid; grid-template-columns: repeat(5, minmax(0, 1fr)); gap:12px; margin-bottom:20px;">
{kpi("Documents","11","4 projects · 2 RFP", sp=spark([3,4,4,6,8,9,11]))}
{kpi("Open findings","896","across 15 reviews","+41 this week","inv",spark([700,740,790,820,855,896]))}
{kpi("Critical open","17","in 4 documents","+2","inv")}
{kpi("Avg risk score","14","lower is better","−3 vs last month")}
{kpi("Awaiting review","2","uploaded, not yet reviewed")}
</div>'''
    def proj(name, n, avg, crit, rows, open_=True):
        chev = icon("chev",14,SUBTLE)
        head = f'''<tr><td colspan="7" style="background:#FAFBFC; padding:8px 12px;"><div style="display:flex; align-items:center; gap:10px;">{chev}<span style="font-weight:600; font-size:13px;">{name}</span><span style="font-size:12px; color:{SUBTLE};">{n} documents</span><span style="margin-left:auto; display:flex; gap:8px; align-items:center;"><span style="font-size:12px; color:{MUTED};">Avg score <b class="num">{avg}</b></span>{pill(f"{crit} critical","red") if crit else pill("no critical","green")}<a href="#" style="font-size:12px; font-weight:500;">Open project</a></span></div></td></tr>'''
        body=""
        for r in rows:
            fname, ver, typ, comp, acc, trend, date, st, stt = r
            tr = "" if not trend else (f'<span style="color:{"#1E7A35" if trend>0 else DANGER}; font-size:12px; font-weight:600; margin-left:4px;">{"▲" if trend>0 else "▼"}{abs(trend)}</span>')
            body += f'''<tr><td><div style="display:flex; flex-direction:column; gap:2px;"><span style="font-weight:500;">{fname}</span><span style="font-size:11px; color:{SUBTLE};">{ver}</span></div></td><td>{pill(typ,"blue" if typ=="RFP" else "grey")}</td><td class="r num">{comp}</td><td class="r num">{acc}{tr}</td><td class="num" style="color:{MUTED};">{date}</td><td>{dot_pill(st,stt)}</td><td class="r"><div style="display:inline-flex; gap:4px; justify-content:flex-end;">{btn("Review","outline",size=30)}{btn("","ghost","more",30)}</div></td></tr>'''
        return head+body
    table = f'''<table>
<thead><tr><th style="width:34%;">Document</th><th>Type</th><th class="r">Completeness</th><th class="r">Risk score</th><th>Uploaded</th><th>Status</th><th class="r">Actions</th></tr></thead>
<tbody>
{proj("NovaRetail Software Solutions",7,13,7,[("SOC_SOW_Testing.docx","v6 · 6 versions · compare vs v5","SOW",0,10,-2,"24 Jul 2026","Reviewed","green"),("SOC_SOW_Testing.docx","v1","SOW",0,12,None,"23 Jul 2026","Reviewed","green")])}
{proj("ConflictTest",2,8,2,[("Subtle_Conflicts_Test.docx","v2 · 2 versions","SOW",0,12,2,"24 Jul 2026","Reviewed","green")])}
{proj("RFPValidation",1,25,1,[("rfp_sample.pdf","v1","RFP",29,25,None,"23 Jul 2026","Reviewed","green")])}
{proj("Acme",1,0,0,[("sample_rfp.docx","v1","RFP","–","–",None,"18 Jul 2026","Not reviewed","grey")])}
</tbody></table>'''
    toolbar = f'''<div style="display:flex; align-items:center; gap:10px; margin-bottom:12px;">
{seg(["All 11","SOW 9","RFP 2","Other 0"],"All 11")}
<div style="display:flex; align-items:center; gap:8px; height:32px; width:260px; padding:0 10px; border:1px solid {BORDER}; border-radius:6px; color:{SUBTLE}; font-size:13px; background:#fff;">{icon("search",15,SUBTLE)}Filter by name or project</div>
{btn("Status","outline","chev",32)}{btn("Project","outline","chev",32)}
<span style="margin-left:auto; display:inline-flex; gap:4px;">{btn("","ghost","list",32)}{btn("","ghost","grid",32)}</span>
</div>'''
    body = header("SOW &amp; RFP Review","Contract risk reviews for your projects. Upload a document, run the six reviewers, fix before you sign.",btn("Export CSV","outline","down")+btn("Upload document","primary","upload"))+kpis+toolbar+card("Documents",table,f'<span style="font-size:12px; color:{SUBTLE};">Grouped by project · sorted by last upload</span>')
    return shell("sow",["SOW &amp; RFP Review"],body)

# ---------- 2. MITRE list ----------
def mitre_list():
    kpis=f'''<div style="display:grid; grid-template-columns: repeat(4, minmax(0, 1fr)); gap:12px; margin-bottom:20px;">
{kpi("Assessments","4","1 demo · 4 archived")}
{kpi("Latest coverage","14.4%","abc ltd · 8 Sep 2026","▲14.1", "blue", spark([2.2,2.2,10.4,0.3,14.4]))}
{kpi("Best trend","+12.2 pts","abc ltd over 8 runs")}
{kpi("SIEM connections","2","1 scheduled weekly · both healthy")}
</div>'''
    def row(name, cust, cov, ent, ics, mob, n, d, date, status, demo=False, delta=None):
        dl = "" if delta is None else f'<span style="font-size:12px; font-weight:600; color:{"#1E7A35" if delta>0 else DANGER};">{"▲" if delta>0 else "▼"}{abs(delta)}</span>'
        return f'''<tr><td><div style="display:flex; flex-direction:column; gap:2px;"><span style="display:flex; align-items:center; gap:8px; font-weight:500;">{name}{pill("Demo","blue") if demo else ""}</span><span style="font-size:11px; color:{SUBTLE};">{cust}</span></div></td>
<td><div style="display:flex; align-items:center; gap:10px;"><span class="num" style="font-size:16px; font-weight:600; min-width:52px;">{cov}</span>{dl}</div></td>
<td>{bar(ent, PRIMARY, 90)}</td><td>{bar(ics, PRIMARY, 90)}</td><td>{bar(mob, PRIMARY, 90)}</td>
<td class="r num">{n} / {d}</td><td>{dot_pill(status,"green" if status=="Completed" else "amber")}</td><td class="num" style="color:{MUTED};">{date}</td>
<td class="r"><div style="display:inline-flex; gap:4px;">{btn("Open","outline",size=30)}{btn("","ghost","more",30)}</div></td></tr>'''
    table=f'''<table><thead><tr><th style="width:24%;">Assessment</th><th>Coverage</th><th>Enterprise</th><th>ICS / OT</th><th>Mobile</th><th class="r">Covered / applicable</th><th>Status</th><th>Last run</th><th class="r"></th></tr></thead><tbody>
{row("abc ltd","Cisco CDC · Prepared by Wipro Practice","14.4%",17.9,5.2,1.6,132,918,"8 Sep 2026","Completed",delta=14.1)}
{row("Acme MITRE Assessment","Acme Ltd","10.4%",13,4.1,0.8,95,911,"2 Aug 2026","Completed",demo=True,delta=8.2)}
{row("Test Assessment","—","2.2%",2.3,2.1,1.6,20,908,"2 Aug 2026","Completed")}
{row("Mitre Assessment","Cisco CDC","0.3%",0.3,0,0,2,644,"8 Sep 2026","Completed",delta=-78.4)}
</tbody></table>'''
    toolbar=f'''<div style="display:flex; align-items:center; gap:10px; margin-bottom:12px;">
<div style="display:flex; align-items:center; gap:8px; height:32px; width:280px; padding:0 10px; border:1px solid {BORDER}; border-radius:6px; color:{SUBTLE}; font-size:13px; background:#fff;">{icon("search",15,SUBTLE)}Search by name or customer</div>
{seg(["Active","Archived 4"],"Active")}{btn("Status","outline","chev",32)}{btn("Customer","outline","chev",32)}
<span style="margin-left:auto; display:inline-flex; gap:4px;">{btn("","ghost","list",32)}{btn("","ghost","grid",32)}</span></div>'''
    body=header("MITRE ATT&amp;CK Coverage","Detection coverage assessments from your SIEM rule exports and environment inventory. Deterministic numbers; AI only tags.",btn("SIEM connections","outline","link")+btn("New assessment","primary","plus"))+kpis+toolbar+card("Assessments",table,f'<span style="font-size:12px; color:{SUBTLE};">ATT&amp;CK v19.1 · coverage measures presence, not efficacy</span>')
    return shell("mitre",["MITRE ATT&amp;CK Coverage"],body)

# ---------- 3. MITRE detail ----------
def mitre_detail():
    top = f'''<div style="display:flex; align-items:flex-start; justify-content:space-between; gap:24px; margin-bottom:16px;">
<div><div style="display:flex; align-items:center; gap:10px;"><h1 style="margin:0; font-size:22px; font-weight:600; letter-spacing:-.01em;">abc ltd</h1>{pill("Completed","green")}{pill("ATT&amp;CK v19.1","grey")}</div>
<div style="font-size:13px; color:{MUTED}; margin-top:4px;">Cisco CDC · CDC team · Prepared by Wipro Practice · run 8 Sep 2026, 20:23 · <a href="#">8 past runs</a></div></div>
<div style="display:flex; gap:8px;">{btn("Compare runs","outline","clock")}{btn("Re-run","outline")}{btn("Export","primary","down")}</div></div>'''
    kpis=f'''<div style="display:grid; grid-template-columns: repeat(6, minmax(0, 1fr)); gap:12px; margin-bottom:12px;">
{kpi("Coverage","14.4%","132 of 918 applicable · plus 15 partial","▲14.1")}
{kpi("Enterprise","17.9%","125 / 697")}
{kpi("ICS / OT","5.2%","6 / 118")}
{kpi("Mobile","1.6%","3 / 190")}
{kpi("Not covered","771","ranked in Gaps &amp; roadmap")}
{kpi("Not applicable","37","with printed reasons")}
</div>'''
    overlay=f'''<div style="border:1px solid #CFE0F5; background:#EEF5FD; border-radius:8px; padding:12px 16px; display:flex; gap:16px; align-items:flex-start; margin-bottom:16px;">
<div style="flex:1;"><div style="font-size:13px; font-weight:600; color:{FG};">Two numbers, never one</div><div style="font-size:13px; color:{MUTED}; margin-top:2px;">Your SIEM rules cover <b class="num">117 (12.7%)</b>. Adding Microsoft Defender for Endpoint and Palo Alto Cortex XDR's MITRE-evaluated detections credits a further <b class="num">15 (1.6%)</b>. Vendor-evaluated capability is not proof the alerts are tuned, monitored or reaching your SOC.</div></div>
<a href="#" style="font-size:12px; font-weight:500; white-space:nowrap;">Source: evals.mitre.org</a></div>'''
    inputs=f'''<div style="display:grid; grid-template-columns: 1fr 1fr; gap:12px; margin-bottom:16px;">
{card("Detection rules · acme_sentinel_usecases_v2.xlsx", f'<div style="padding:12px 16px; display:flex; flex-wrap:wrap; gap:6px;">{pill("175 rules","grey")}{pill("153 tagged by you","grey")}{pill("1 AI-tagged","purple")}{pill("1 reviewer-edited","grey")}{pill("4 unmapped","amber")}{pill("3 disabled","grey")}</div>', f'<a href="#" style="font-size:12px;">Remap columns</a>')}
{card("Environment · acme_environment_v2.xlsx", f'<div style="padding:12px 16px; font-size:13px; color:{MUTED};">13 platforms · 29 log sources · 16 tools · 7 crown jewels<div style="margin-top:6px; display:flex; gap:6px;">{pill("OT/ICS","grey")}{pill("Managed mobile","grey")}{pill("9 unmapped assets","amber")}</div></div>', f'<a href="#" style="font-size:12px;">How we read it (93 entries)</a>')}
</div>'''
    def cell(t, tone):
        bg={"g":"#1E9E4A","y":WARNING,"r":"#FDE1E4","n":SOFT}[tone]; col={"g":"#fff","y":FG,"r":"#8B1E2A","n":SUBTLE}[tone]
        return f'<div style="background:{bg}; color:{col}; font-size:10.5px; padding:4px 6px; border-radius:3px; white-space:nowrap; overflow:hidden; text-overflow:ellipsis;">{t}</div>'
    cols=[("Initial Access","7/22",[("T1078 Valid Accounts","g"),("T1078.001 Default","r"),("T1078.004 Cloud","g"),("T1091 Replication","r"),("T1133 External Remote","y"),("T1190 Exploit Public","g"),("T1195 Supply Chain","r"),("T1199 Trusted Rel.","r"),("T1200 Hardware Add.","n")]),
          ("Execution","15/64",[("T1047 WMI","g"),("T1053 Scheduled Task","g"),("T1053.003 Cron","g"),("T1053.005 Sched.","g"),("T1059 Command Interp.","g"),("T1059.001 PowerShell","g"),("T1059.004 Bash","r"),("T1204 User Execution","r"),("T1569 System Services","r")]),
          ("Persistence","22/113",[("T1037 Boot Scripts","r"),("T1053 Scheduled Task","g"),("T1098 Account Manip.","g"),("T1136 Create Account","g"),("T1136.001 Local","r"),("T1543 System Process","y"),("T1546 Event Trigger","r"),("T1547 Boot Autostart","g"),("T1556 Modify Auth","r")]),
          ("Privilege Esc.","19/96",[("T1055 Process Inject","g"),("T1068 Exploit Priv.","r"),("T1078 Valid Accounts","g"),("T1134 Token Manip.","r"),("T1484 Domain Policy","g"),("T1548 Abuse Elev.","y"),("T1548.002 UAC","g"),("T1574 Hijack Flow","r"),("T1611 Escape Container","n")]),
          ("Credential Access","16/67",[("T1003 OS Cred Dump","g"),("T1003.001 LSASS","g"),("T1003.003 NTDS","g"),("T1110 Brute Force","g"),("T1552 Unsecured Creds","r"),("T1552.001 Files","r"),("T1555 Password Stores","r"),("T1557 Adversary-in-Mid","r"),("T1558 Kerberos","g")]),
          ("Lateral Movement","9/23",[("T1021 Remote Services","g"),("T1021.001 RDP","g"),("T1021.002 SMB","g"),("T1021.004 SSH","r"),("T1021.006 WinRM","g"),("T1080 Taint Shared","r"),("T1210 Exploit Remote","r"),("T1219 Remote Access SW","r"),("T1570 Lateral Tool","r")])]
    grid = "".join(f'<div style="display:flex; flex-direction:column; gap:3px; min-width:0;"><div style="font-size:12px; font-weight:600; padding-bottom:2px;">{n}<span class="num" style="font-weight:500; color:{SUBTLE}; margin-left:6px;">{c}</span></div>{"".join(cell(t,k) for t,k in cs)}</div>' for n,c,cs in cols)
    heat=f'''<div style="display:flex; align-items:center; gap:10px; margin-bottom:10px;">
{btn("Threat group: full matrix","outline","chev",32)}{btn("Runs: latest","outline","chev",32)}{btn("Detected via: all","outline","chev",32)}
<span style="display:inline-flex; gap:14px; margin-left:8px; font-size:12px; color:{MUTED};"><span>{dot_pill("Covered","green")}</span><span>{dot_pill("Partial","amber")}</span><span>{dot_pill("Not covered","red")}</span><span>{dot_pill("N/A","grey")}</span></span>
<div style="margin-left:auto; display:flex; align-items:center; gap:8px; height:32px; width:260px; padding:0 10px; border:1px solid {BORDER}; border-radius:6px; color:{SUBTLE}; font-size:13px; background:#fff;">{icon("search",15,SUBTLE)}Is it covered? Try T1486, ransomware</div></div>
<div style="display:grid; grid-template-columns: repeat(6, minmax(0, 1fr)); gap:10px;">{grid}</div>'''
    body = top+kpis+overlay+inputs+tabs(["Coverage","Gaps &amp; roadmap","Assumptions &amp; N/A","Compare"],"Coverage")+heat
    return shell("mitre",["MITRE ATT&amp;CK Coverage","abc ltd"],body)

# ---------- 4. Code review detail ----------
def code_detail():
    top=f'''<div style="display:flex; align-items:flex-start; justify-content:space-between; gap:24px; margin-bottom:16px;">
<div><div style="display:flex; align-items:center; gap:10px;"><h1 style="margin:0; font-size:22px; font-weight:600; letter-spacing:-.01em;">NodeGoat golden scan</h1>{pill("Demo","blue")}{pill("VVAH 1.3.0","grey")}</div>
<div style="font-size:13px; color:{MUTED}; margin-top:4px;">target-nodegoat · <span class="mono">c5cb68a</span> · findings.json · 12 Sep 2026, 02:25 · 66 of 69 files analysed · 3.4M tokens</div></div>
<div style="display:flex; gap:8px;">{btn("Rename","ghost")}{btn("XLSX tracker","outline","down")}{btn("PPTX deck","primary","down")}</div></div>'''
    kpis=f'''<div style="display:grid; grid-template-columns: repeat(5, minmax(0, 1fr)); gap:12px; margin-bottom:12px;">
{kpi("Findings","29","88 raw before dedup")}
{kpi("Critical","6","confirm these first")}
{kpi("High","5","")}
{kpi("Exploit chains","6","fewest fixes that break all: 3")}
{kpi("Verifier false positives","4","dropped, listed in Scan details")}
</div>'''
    guide=f'''<div style="border:1px solid {BORDER}; border-radius:8px; background:#fff; padding:12px 16px; margin-bottom:16px; display:flex; gap:24px; align-items:center;">
<div style="font-size:13px;"><b>Where to start.</b> <span style="color:{MUTED};">8 of 29 findings sit in <span class="mono">app/routes/session.js</span>. Fixing #3, #4 and #7 breaks all six exploit chains.</span></div>
<a href="#" style="margin-left:auto; font-size:12px; font-weight:500; white-space:nowrap;">Open remediation plan</a></div>'''
    sev=lambda s,t: pill(s,t)
    conf=lambda p: f'<div style="width:64px; height:6px; border-radius:999px; background:{SOFT}; overflow:hidden;"><div style="width:{p}%; height:100%; background:{PRIMARY};"></div></div>'
    rows=[(1,"Critical","red","Missing authentication on MongoDB","logic-flaw","CWE-306","9.9",95,"docker-compose.yml:8"),
          (2,"Critical","red","EOL Node.js 12 in Docker base image","other","CWE-1104","9.8",92,"Dockerfile:1-7"),
          (3,"Critical","red","NoSQL injection in login via username","injection","CWE-943","9.8",96,"app/data/user-dao.js:92-93"),
          (4,"Critical","red","Hardcoded session secret in config","other","CWE-798","9.8",98,"config/env/all.js:8"),
          (5,"Critical","red","Missing rate limiting on login endpoint","other","CWE-307","9.1",88,"app/routes/session.js:53-58"),
          (6,"Critical","red","Server exposes sensitive data over HTTP","other","CWE-319","9.1",90,"server.js:145-147"),
          (7,"High","amber","Eval injection via contributions update handler","injection","CWE-95","8.8",94,"app/routes/index.js:50-52"),
          (8,"High","amber","EOL MongoDB 4.4 in docker-compose","other","CWE-1104","8.2",85,"docker-compose.yml:14"),
          (9,"High","amber","Authenticated SSRF via stock research URL","injection","CWE-918","7.7",89,"app/routes/research.js:14-16"),
          (10,"High","amber","Unpinned GitHub tarball dependency","injection","CWE-494","7.5",80,"package-lock.json:39")]
    tr="".join(f'<tr{" class=\"hover\"" if i==3 else ""}><td class="num" style="color:{SUBTLE}; width:36px;">{n}</td><td>{sev(s,t)}</td><td><span style="font-weight:500;">{ti}</span>{"<span style=\"margin-left:8px;\">"+pill("in 3 chains","purple")+"</span>" if n in (3,4,7) else ""}</td><td style="color:{MUTED};">{cl}</td><td><a href="#" class="mono">{cwe}</a></td><td class="r num">{cv}</td><td>{conf(cf)}</td><td class="mono" style="color:{MUTED};">{f}</td><td>{pill("Confirmed","green")}</td></tr>' for i,(n,s,t,ti,cl,cwe,cv,cf,f) in enumerate(rows))
    table=f'''<table><thead><tr><th>#</th><th>Severity</th><th style="width:30%;">Title</th><th>Class</th><th>CWE</th><th class="r">CVSS</th><th>Confidence</th><th>File:lines</th><th>Verdict</th></tr></thead><tbody>{tr}</tbody></table>
<div style="padding:10px 16px; font-size:12px; color:{SUBTLE}; display:flex; justify-content:space-between;"><span>Showing 10 of 29 · click a row to open the finding drawer</span><span>Findings produced by Visa Vulnerability Agentic Harness (Apache-2.0). AI-generated triage candidates, confirm before acting.</span></div>'''
    toolbar=f'''<div style="display:flex; align-items:center; gap:10px; margin-bottom:12px;">{seg(["All 29","Critical 6","High 5","Medium 18","Low 0"],"All 29")}
<div style="display:flex; align-items:center; gap:8px; height:32px; width:240px; padding:0 10px; border:1px solid {BORDER}; border-radius:6px; color:{SUBTLE}; font-size:13px; background:#fff;">{icon("search",15,SUBTLE)}Title, file or CWE</div>{btn("Class","outline","chev",32)}{btn("Verdict","outline","chev",32)}</div>'''
    body=top+kpis+guide+tabs(["Findings 29","Exploit chains 6","Remediation plan","Scan details"],"Findings 29")+toolbar+card("Findings register",table)
    return shell("code",["Code Security Review","NodeGoat golden scan"],body)

# ---------- 5. Admin ----------
def admin():
    kpis=f'''<div style="display:grid; grid-template-columns: repeat(5, minmax(0, 1fr)); gap:12px; margin-bottom:20px;">
{kpi("Organisations","9","1 enabled to run · 8 free")}
{kpi("Members","9","9 active")}
{kpi("Sign-ins","23","this week · 37 in 30 days",sp=spark([2,5,3,6,4,8,7]))}
{kpi("AI reviews","15","0 this week")}
{kpi("Access requests","2","awaiting your decision")}
</div>'''
    def org(name, email, tier, members, created, last, req=False):
        t = pill(tier.capitalize(),"blue" if tier!="free" else "grey")
        act = btn("Enable pro","primary",size=30) if tier=="free" else btn("Change tier","outline","chev",30)
        rq = pill("Requested access · 5h ago","amber") if req else ""
        return f'<tr><td><div style="display:flex; flex-direction:column; gap:2px;"><span style="font-weight:500; display:flex; gap:8px; align-items:center;">{name}{rq}</span><span style="font-size:11px; color:{SUBTLE};">{email}</span></div></td><td>{t}</td><td class="r num">{members}</td><td class="num" style="color:{MUTED};">{created}</td><td class="num" style="color:{MUTED};">{last}</td><td class="r"><div style="display:inline-flex; gap:4px;">{act}{btn("","ghost","more",30)}</div></td></tr>'
    table=f'''<table><thead><tr><th style="width:36%;">Organisation</th><th>Tier</th><th class="r">Members</th><th>Created</th><th>Last sign-in</th><th class="r">Run entitlement</th></tr></thead><tbody>
{org("Default Org","manishjnvk@gmail.com · platform admin","enterprise",1,"18 Jul 2026","1 min ago")}
{org("talk2maq's Workspace","talk2maq@gmail.com","free",1,"12 Sep 2026","5 hours ago",True)}
{org("rajendra19sep's Workspace","rajendra19sep@gmail.com","free",1,"12 Sep 2026","5 hours ago",True)}
{org("starshrishail's Workspace","starshrishail@gmail.com","free",1,"21 Jul 2026","1 month ago")}
{org("veena9jan's Workspace","veena9jan@gmail.com","free",1,"24 Jul 2026","1 month ago")}
{org("urdineshnaidu's Workspace","urdineshnaidu@gmail.com","free",1,"4 Aug 2026","29 days ago")}
{org("hemantsawant48's Workspace","hemantsawant48@gmail.com","free",1,"7 Aug 2026","1 month ago")}
</tbody></table>'''
    side=f'''<div style="display:flex; flex-direction:column; gap:12px;">
{card("AI provider", f'<div style="padding:14px 16px; display:flex; flex-direction:column; gap:10px;"><div style="display:flex; justify-content:space-between; align-items:baseline;"><span class="num" style="font-size:22px; font-weight:600;">$7.85</span>{pill("Key limit reached","red")}</div><div style="height:6px; border-radius:999px; background:{SOFT}; overflow:hidden;"><div style="width:31%; height:100%; background:{DANGER};"></div></div><div style="font-size:12px; color:{MUTED};">OpenRouter key · limit $2.00, remaining $0.00. Reviews and MITRE tagging fail until the limit is raised.</div><a href="#" style="font-size:12px; font-weight:500;">Open OpenRouter dashboard</a></div>')}
{card("Recent activity", f'<div style="padding:6px 0;">' + "".join(f'<div style="display:flex; gap:10px; padding:8px 16px; font-size:12px; border-bottom:1px solid {BORDER};"><span style="color:{SUBTLE}; min-width:56px;" class="num">{t}</span><span><b>{w}</b> {a}</span></div>' for t,w,a in [("1 min ago","Manish Kumar","signed in with Google"),("5 h ago","Rajendra Sah","requested run access"),("5 h ago","Mohammed Shaik","requested run access"),("2 h ago","Manish Kumar","uploaded SOC_SOW_Testing.docx v6"),("Yesterday","Scheduled pull","abc ltd · Sentinel · 175 rules")]) + '</div>')}
</div>'''
    body=header("Admin","Platform view across all organisations. Only platform admins see this page.",btn("Refresh","outline")+btn("Invite organisation","primary","plus"))+kpis+f'<div style="display:grid; grid-template-columns: minmax(0, 1fr) 300px; gap:16px;">{card("Organisations",table,f"<span style=\"font-size:12px; color:{SUBTLE};\">Free-tier orgs can upload and configure but not start reviews or assessments</span>")}{side}</div>'
    return shell("admin",["Admin"],body)

# ---------- Low-fi directions ----------
def lofi(title, blurb, dark):
    bg = "#1B2433" if dark else "#fff"; fg = "#fff" if dark else FG
    box = lambda w,h,t="": f'<div style="width:{w}px; height:{h}px; border:1.5px dashed {"#5A6B85" if dark else "#9AA7B8"}; border-radius:6px; display:flex; align-items:center; justify-content:center; font-size:12px; color:{"#9DB0CB" if dark else SUBTLE};">{t}</div>'
    if dark:
        body=f'''<div style="width:1440px; height:900px; display:flex; background:#F4F5F7; overflow:hidden; font-family: Inter, system-ui, sans-serif;">
<div style="width:64px; background:{bg}; display:flex; flex-direction:column; align-items:center; gap:14px; padding:16px 0;">{"".join(f'<div style="width:32px; height:32px; border-radius:8px; background:{"#3B82F6" if i==0 else "#2A3547"};"></div>' for i in range(4))}</div>
<div style="flex:1; display:flex; flex-direction:column;">
<div style="height:52px; background:{bg}; display:flex; align-items:center; gap:12px; padding:0 20px; color:#fff;">{box(320,30,"global search / command palette")}<span style="margin-left:auto;">{box(120,30,"org switcher")}</span>{box(30,30)}</div>
<div style="padding:24px; display:flex; flex-direction:column; gap:16px;">
<div style="display:flex; justify-content:space-between;">{box(360,36,"page title + breadcrumb")}{box(220,36,"primary + secondary action")}</div>
<div style="display:flex; gap:12px;">{"".join(box(210,84,"KPI tile w/ delta") for _ in range(6))}</div>
<div style="display:flex; gap:12px;">{box(880,520,"dense data table · sticky header · row hover · inline actions")}{box(400,520,"context rail: filters, saved views, activity")}</div>
</div></div></div>'''
    else:
        body=f'''<div style="width:1440px; height:900px; display:flex; flex-direction:column; background:#fff; overflow:hidden; font-family: Inter, system-ui, sans-serif;">
<div style="height:60px; border-bottom:1px solid {BORDER}; display:flex; align-items:center; gap:24px; padding:0 48px;">{box(120,30,"wordmark")}{"".join(box(130,30,t) for t in ["SOW Review","MITRE","Code Review","Admin"])}<span style="margin-left:auto;">{box(36,36)}</span></div>
<div style="padding:40px 48px; display:flex; flex-direction:column; gap:28px; max-width:1200px;">
<div style="display:flex; justify-content:space-between; align-items:flex-end;">{box(520,64,"large page title + one-line purpose")}{box(200,40,"single primary action")}</div>
<div style="display:flex; gap:24px;">{"".join(box(270,110,"big number + sentence") for _ in range(4))}</div>
<div style="display:flex; gap:24px;">{box(760,440,"airy list: one row per item, generous spacing, 15px type")}{box(360,440,"insight card: what to do next")}</div>
</div></div>'''
    note=f'<div style="position:absolute; left:24px; bottom:20px; max-width:900px; font-size:13px; color:{SUBTLE};"><b style="color:{FG};">{title}.</b> {blurb}</div>'
    return f'''<!doctype html>
<html><head><meta charset="utf-8"><script src="./support.js"></script></head>
<body><x-dc><helmet><style>body{{margin:0; font-family:Inter, system-ui, sans-serif;}} a{{color:{PRIMARY};}} a:hover{{color:#0052a3;}}</style></helmet>
<div style="position:relative;">{body}{note}</div></x-dc></body></html>'''

files = {
 "Main.dc.html": sow(),
 "MitreList.dc.html": mitre_list(),
 "MitreDetail.dc.html": mitre_detail(),
 "CodeReviewDetail.dc.html": code_detail(),
 "Admin.dc.html": admin(),
 "DirectionB.dc.html": lofi("Direction B, dark operations console","Icon rail + dark top bar, light content, a right-hand context rail for filters and activity. Best when analysts live in the tool all day. Tradeoff: two chrome colours, heavier to theme; PDF/PPTX exports still light.",True),
 "DirectionC.dc.html": lofi("Direction C, airy editorial","Top navigation, no sidebar, one action per page, larger type and whitespace. Reads like a report, fits the consultancy deliverable story. Tradeoff: lower density, more scrolling on the MITRE matrix and findings tables.",False),
}
for n,s in files.items():
    open(os.path.join(OUT,n),"w",encoding="utf-8").write(s)

canvas = {
 "pages":[{"id":"page-1","name":"Redesign (Direction A)"},{"id":"page-2","name":"Alternate directions"}],
 "artboards":[
  {"file":"Main.dc.html","title":"SOW & RFP Review","x":0,"y":0,"w":1440,"h":900,"page":"page-1"},
  {"file":"MitreList.dc.html","title":"MITRE list","x":1560,"y":0,"w":1440,"h":900,"page":"page-1"},
  {"file":"MitreDetail.dc.html","title":"MITRE detail","x":0,"y":1060,"w":1440,"h":900,"page":"page-1"},
  {"file":"CodeReviewDetail.dc.html","title":"Code Security Review detail","x":1560,"y":1060,"w":1440,"h":900,"page":"page-1"},
  {"file":"Admin.dc.html","title":"Admin","x":0,"y":2120,"w":1440,"h":900,"page":"page-1"},
  {"file":"DirectionB.dc.html","title":"Direction B · dark ops console (low-fi)","x":0,"y":0,"w":1440,"h":900,"page":"page-2"},
  {"file":"DirectionC.dc.html","title":"Direction C · airy editorial (low-fi)","x":1560,"y":0,"w":1440,"h":900,"page":"page-2"},
 ],
 "annotations":[
  {"id":"a-system","x":1560,"y":2120,"w":420,"page":"page-1","text":"Direction A: quiet operations console.\nKept: Inter, brand blue #0066CC, slate #0F1729, 8px radius, 224px sidebar, shadcn card/badge/button anatomy.\nAdded: 48px utility bar (breadcrumb, global search ⌘K, environment chip), grouped sidebar with org + AI-credit meter, KPI strip with deltas and sparklines, toolbar row (segmented filter + search + filter chips + density toggle), tables with uppercase 11px headers, tabular numerals, status dots and soft pills, one consolidated Export action per page."},
  {"id":"a-sow","x":0,"y":-150,"w":460,"page":"page-1","text":"SOW dashboard, what changed and why:\n1. Red 0/12/29 numbers read as errors; risk score now has a neutral value + trend arrow, completeness shows '–' when not reviewed.\n2. Five text links per row (Review · View · New version · Compare · Delete) became one Review button + overflow menu; destructive action moves into the menu.\n3. Project groups get summary chips (avg score, critical count) in a real header row instead of right-aligned loose text.\n4. Counts row (Total 11 · SOW 9 …) became a segmented filter that actually filters.\n5. KPI strip gives the page a purpose above the table."},
  {"id":"a-mitre","x":1560,"y":-150,"w":460,"page":"page-1","text":"MITRE list: cards hid comparison. A table with inline coverage bars per domain, covered/applicable, trend delta and last run lets a consultant scan four customers at once. Card view stays as a toggle.\nMITRE detail: eight equal tiles flattened the story. Now 6 tiles with hierarchy, the tool-overlay banner reads as 'two numbers, never one', inputs sit in two cards with a chip vocabulary (tagged / AI-tagged / unmapped / disabled), Exec PDF · Full PDF · XLSX · PPT · Navigator collapse into one Export menu. Heatmap unchanged in logic, legend moved into the toolbar."},
  {"id":"a-code","x":1560,"y":2120+0,"w":0,"page":"page-1","text":""},
  {"id":"a-code2","x":2020,"y":2120,"w":420,"page":"page-1","text":"Code Security Review detail: added a 'where to start' strip (the set-cover result the PPTX already computes), 'in N chains' pill on findings that matter most, a Remediation plan tab, and the VVAH attribution moved to the table footer. Severity became a pill, confidence a bar, file:lines mono.\nAdmin: organisations table now leads with the decision (Enable pro), shows access requests inline with age, and the AI provider card surfaces the OpenRouter key state that caused today's outage."},
  {"id":"a-alt","x":0,"y":-150,"w":520,"page":"page-2","text":"Two genuinely different directions, sketched low-fi so the choice is about structure, not polish. Direction A (page 1) is the recommendation: it keeps every existing token and component, so it can be built incrementally page by page."}
 ],
 "launch":{"view":"canvas","page":"page-1"}
}
# drop the empty placeholder annotation
canvas["annotations"]=[a for a in canvas["annotations"] if a["text"]]
json.dump(canvas, open(os.path.join(OUT,"canvas.json"),"w"), indent=1)
print("wrote", list(files), "canvas.json")
