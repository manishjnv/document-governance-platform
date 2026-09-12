"""Shared framework for the ScopeWise app design canvas (Design Components format).

Everything an artboard needs comes from here: tokens CSS, inline SVG icons, the AppShell
markup, primitive helpers (buttons, chips, tabs, sheets, dialogs, kebabs, tables,
dropzones, states) and the `screen()` assembler that writes one self-contained .dc.html.

Template rule: `[[name]]` placeholders are filled by `T()`; `{{hole}}` is left for the
DC runtime. Never use f-strings on markup that contains DC holes.
"""
import json
import os
import re

HERE = os.path.dirname(os.path.abspath(__file__))
LOGIC_JS = open(os.path.join(HERE, "logic.js"), encoding="utf-8").read()


def T(_tpl, **kw):
    for k, v in kw.items():
        _tpl = _tpl.replace("[[" + k + "]]", str(v))
    return _tpl


def esc(s):
    """Escape text for HTML markup (not for JS data)."""
    return (
        str(s)
        .replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
    )


def dc_props(d):
    """JSON for the single-quoted data-props attribute."""
    return json.dumps(d, ensure_ascii=False).replace("&", "&amp;").replace("'", "&#39;")


def js_data(obj):
    """JSON literal safe inside a <script>."""
    return json.dumps(obj, ensure_ascii=False).replace("</", "<\\/")


# ----------------------------------------------------------------------------- tokens
TOKENS = {
    "paper": "#FAF9F6", "card": "#FFFFFF", "ink": "#14181F", "ink2": "#3B4453", "ink3": "#5E6877",
    "line": "#E6E3DD", "line2": "#D5D1C9", "accent": "#2457B8", "accent_soft": "#E8EFFB",
    "crit": "#A32D25", "crit_soft": "#FBE7E4", "high": "#9C4A0C", "high_soft": "#FCEEDF",
    "med": "#705708", "med_soft": "#FAF1D2", "low": "#2E6A42", "low_soft": "#E3F1E7",
    "info": "#1F5C85", "info_soft": "#E3EEF7", "ok": "#2A6F46", "ok_soft": "#E3F1E7",
    "na": "#ECE9E3", "violet": "#4F3691", "violet_soft": "#EFE9FA", "amber_bg": "#FFF8E6",
}

CSS = """
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=IBM+Plex+Sans:wght@400;500;600&family=IBM+Plex+Mono:wght@400;500&display=swap">
<style>
:root{--paper:#FAF9F6;--card:#FFFFFF;--ink:#14181F;--ink2:#3B4453;--ink3:#5E6877;--line:#E6E3DD;--line2:#D5D1C9;
--accent:#2457B8;--accent-soft:#E8EFFB;--crit:#A32D25;--crit-soft:#FBE7E4;--high:#9C4A0C;--high-soft:#FCEEDF;
--med:#705708;--med-soft:#FAF1D2;--low:#2E6A42;--low-soft:#E3F1E7;--info:#1F5C85;--info-soft:#E3EEF7;--ok:#2A6F46;--ok-soft:#E3F1E7;
--na:#ECE9E3;--violet:#4F3691;--violet-soft:#EFE9FA;--r:8px;--rc:10px;
--crit-fill:#C0392B;--high-fill:#D97A1F;--med-fill:#D4A72C;--low-fill:#3E8A57;--info-fill:#2E86C1;
--shadow:0 1px 2px rgba(20,24,31,.05),0 8px 24px -12px rgba(20,24,31,.16);--ease:cubic-bezier(.22,.61,.36,1);--side:224px}
*{box-sizing:border-box}
body{margin:0;background:var(--paper);color:var(--ink);font:400 14px/1.5 "IBM Plex Sans","Segoe UI",system-ui,-apple-system,sans-serif;-webkit-font-smoothing:antialiased}
a{color:var(--accent);text-decoration:none}a:hover{color:#1B4494;text-decoration:underline}
h1,h2,h3,h4{margin:0;font-weight:600;letter-spacing:-.01em;color:var(--ink)}
h1{font-size:24px;line-height:1.2}h2{font-size:18px}h3{font-size:14px}
p{margin:0}button{font:inherit;color:inherit}
.mono{font-family:"IBM Plex Mono",Consolas,Menlo,monospace;font-size:12px}
.num{font-variant-numeric:tabular-nums}
.sub{color:var(--ink2)}.faint{color:var(--ink3)}
.lbl{font-size:11px;font-weight:600;letter-spacing:.05em;text-transform:uppercase;color:var(--ink3)}
.card{background:var(--card);border:1px solid var(--line);border-radius:var(--rc);box-shadow:var(--shadow)}
.card-h{display:flex;align-items:center;justify-content:space-between;gap:12px;padding:12px 16px;border-bottom:1px solid var(--line)}
.card-b{padding:16px}
.row{display:flex;align-items:center;gap:8px}.row>*{min-width:0}.wrap{flex-wrap:wrap}.between{justify-content:space-between}.grow{flex:1;min-width:0}
.stack{display:flex;flex-direction:column;gap:8px}
.grid{display:grid;gap:12px}.g2{grid-template-columns:repeat(2,minmax(0,1fr))}.g3{grid-template-columns:repeat(3,minmax(0,1fr))}.g4{grid-template-columns:repeat(4,minmax(0,1fr))}.g5{grid-template-columns:repeat(5,minmax(0,1fr))}.g6{grid-template-columns:repeat(6,minmax(0,1fr))}.g8{grid-template-columns:repeat(8,minmax(0,1fr))}
/* buttons */
.btn{display:inline-flex;align-items:center;justify-content:center;gap:6px;height:36px;padding:0 14px;border-radius:var(--r);border:1px solid var(--line2);background:#fff;color:var(--ink);font-size:13px;font-weight:500;cursor:pointer;white-space:nowrap;transition:background .16s var(--ease),border-color .16s,transform .16s var(--ease),opacity .16s}
.btn:hover{background:#F3F1EC}.btn:active{transform:translateY(1px)}
.btn.primary{background:var(--accent);border-color:var(--accent);color:#fff}.btn.primary:hover{background:#1E4CA2}
.btn.danger{background:var(--crit);border-color:var(--crit);color:#fff}.btn.danger:hover{background:#9C2A23}
.btn.ghost{background:transparent;border-color:transparent;color:var(--ink2)}.btn.ghost:hover{background:#F0EDE7;color:var(--ink)}
.btn.link{background:transparent;border-color:transparent;color:var(--accent);padding:0;height:auto}.btn.link:hover{text-decoration:underline}
.btn.sm{height:30px;padding:0 10px;font-size:12px}.btn.lg{height:40px;padding:0 18px}.btn.icon{width:36px;padding:0}.btn.icon.sm{width:30px}
.btn[disabled],.btn.disabled{opacity:.5;pointer-events:none}
/* chips */
.chip{display:inline-flex;align-items:center;gap:5px;height:22px;padding:0 8px;border-radius:999px;font-size:12px;font-weight:600;white-space:nowrap;border:1px solid transparent;transition:background .2s,color .2s}
.chip.crit{background:var(--crit-soft);color:var(--crit)}.chip.high{background:var(--high-soft);color:var(--high)}.chip.med{background:var(--med-soft);color:var(--med)}.chip.low{background:var(--low-soft);color:var(--low)}.chip.info{background:var(--info-soft);color:var(--info)}
.chip.ok{background:var(--ok-soft);color:var(--ok)}.chip.grey{background:var(--na);color:var(--ink2)}.chip.blue{background:var(--accent-soft);color:var(--accent)}.chip.violet{background:var(--violet-soft);color:var(--violet)}
.chip.outline{background:#fff;border-color:var(--line2);color:var(--ink2);font-weight:500}
.chip.xs{height:18px;font-size:10.5px;padding:0 6px}
.dot{width:8px;height:8px;border-radius:999px;display:inline-block;flex:none}
/* inputs */
.input,.select,textarea.input{height:36px;padding:0 10px;border:1px solid var(--line2);border-radius:var(--r);background:#fff;color:var(--ink);font:inherit;font-size:13px;outline:none;transition:border-color .16s,box-shadow .16s}
.input:focus,.select:focus,textarea.input:focus{border-color:var(--accent);box-shadow:0 0 0 3px var(--accent-soft)}
.input.sm,.select.sm{height:30px;font-size:12px}textarea.input{height:auto;padding:8px 10px}
.select{padding-right:28px;appearance:none;background:#fff url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='16' height='16' viewBox='0 0 24 24' fill='none' stroke='%233B4453' stroke-width='2' stroke-linecap='round'%3E%3Cpath d='M6 9l6 6 6-6'/%3E%3C/svg%3E") no-repeat right 8px center}
.search{position:relative}.search .input{padding-left:30px;width:100%}.search svg{position:absolute;left:9px;top:50%;transform:translateY(-50%);color:var(--ink3);pointer-events:none}
.label{display:block;font-size:12px;font-weight:500;color:var(--ink2);margin-bottom:4px}
.req{color:var(--crit)}
input[type=checkbox]{width:15px;height:15px;accent-color:var(--accent)}
/* tooltip */
.tip{position:relative}
.tip::after{content:attr(data-tip);position:absolute;left:50%;bottom:calc(100% + 8px);transform:translate(-50%,4px);background:var(--ink);color:#fff;font:400 12px/1.4 "IBM Plex Sans",sans-serif;padding:7px 10px;border-radius:7px;white-space:pre-line;width:max-content;max-width:280px;opacity:0;pointer-events:none;transition:opacity .16s var(--ease),transform .16s var(--ease);z-index:60;text-align:left;font-weight:400;text-transform:none;letter-spacing:0}
.tip::before{content:"";position:absolute;left:50%;bottom:calc(100% + 3px);transform:translateX(-50%);border:5px solid transparent;border-top-color:var(--ink);opacity:0;transition:opacity .16s;z-index:60}
.tip:hover::after,.tip:hover::before,.tip:focus-visible::after,.tip:focus-visible::before{opacity:1;transform:translate(-50%,0)}
.tip.left::after{left:0;transform:translate(0,4px)}.tip.left:hover::after{transform:translate(0,0)}.tip.left::before{left:14px}
/* kpi */
.kpi{background:var(--card);border:1px solid var(--line);border-radius:var(--rc);padding:12px 14px;display:flex;flex-direction:column;gap:4px;min-width:0;text-align:left;cursor:default}
.kpi.click{cursor:pointer;transition:border-color .16s,background .16s}.kpi.click:hover{border-color:var(--accent);background:#FBFBFF}
.kpi .v{font-size:24px;font-weight:600;letter-spacing:-.02em;line-height:1.1}
/* tables */
.tbl{width:100%;border-collapse:collapse}
.tbl th{text-align:left;font-size:11px;font-weight:600;letter-spacing:.05em;text-transform:uppercase;color:var(--ink3);padding:9px 12px;border-bottom:1px solid var(--line);background:#FBFAF8;white-space:nowrap}
.tbl th button{background:none;border:0;padding:0;font:inherit;color:inherit;cursor:pointer;display:inline-flex;align-items:center;gap:4px;text-transform:inherit;letter-spacing:inherit}
.tbl td{padding:10px 12px;border-bottom:1px solid var(--line);font-size:13px;vertical-align:middle}
.tbl tbody tr{transition:background .12s}.tbl tbody tr:hover{background:#F6F4EF}.tbl tbody tr.sel{background:var(--accent-soft)}
.tbl .r{text-align:right}.tbl tr.band td{background:#F5F3EE;padding:7px 12px}
.tbl .clickable{cursor:pointer}
/* tabs */
.tabs{display:flex;gap:20px;border-bottom:1px solid var(--line);align-items:flex-end}
.tab{background:none;border:0;padding:0 2px 10px;font-size:13px;font-weight:500;color:var(--ink2);cursor:pointer;border-bottom:2px solid transparent;margin-bottom:-1px;transition:color .16s,border-color .16s}
.tab:hover{color:var(--ink)}.tab.on{color:var(--ink);font-weight:600;border-color:var(--accent)}
.seg{display:inline-flex;gap:2px;padding:3px;background:var(--na);border-radius:7px}
.seg button{border:0;background:transparent;padding:0 10px;height:28px;border-radius:5px;font-size:12.5px;font-weight:500;color:var(--ink2);cursor:pointer;transition:background .16s,color .16s}
.seg button.on{background:#fff;color:var(--ink);box-shadow:0 1px 2px rgba(20,24,31,.14)}
.pillbar{display:flex;flex-wrap:wrap;gap:6px}
.pillbar .chip{cursor:pointer;opacity:.75}.pillbar .chip:hover{opacity:1}.pillbar .chip.on{opacity:1;box-shadow:0 0 0 2px var(--accent-soft);border-color:var(--accent)}
/* sheets / dialogs / menus */
.ov{position:fixed;inset:0;background:rgba(20,24,31,.35);z-index:40;transition:opacity .25s var(--ease)}
.sheet{position:fixed;top:0;right:0;height:100%;background:#fff;box-shadow:-12px 0 40px -20px rgba(20,24,31,.35);z-index:41;display:flex;flex-direction:column;transition:transform .32s var(--ease);max-width:100vw}
.sheet-h{padding:16px 20px 12px 24px;border-bottom:1px solid var(--line);display:flex;align-items:flex-start;gap:10px}
.sheet-b{padding:16px 20px 16px 24px;overflow-y:auto;flex:1}
.sheet-f{position:sticky;bottom:0;padding:10px 20px;border-top:1px solid var(--line);background:#fff;display:flex;align-items:center;justify-content:space-between;gap:8px}
.grip{position:absolute;left:0;top:0;height:100%;width:12px;cursor:ew-resize;touch-action:none;display:flex;align-items:center;justify-content:center}
.grip i{width:4px;height:40px;border-radius:999px;background:var(--line2);transition:background .16s}.grip:hover i,.grip:focus-visible i{background:var(--accent)}
.grip:focus-visible{outline:none}
.xbtn{background:none;border:0;padding:4px;border-radius:6px;color:var(--ink3);cursor:pointer;display:inline-flex}.xbtn:hover{background:#F0EDE7;color:var(--ink)}
.dlg-ov{position:fixed;inset:0;background:rgba(20,24,31,.45);z-index:50;display:flex;align-items:center;justify-content:center;padding:16px;transition:opacity .2s var(--ease)}
.dlg{background:#fff;border-radius:12px;box-shadow:0 24px 60px -20px rgba(20,24,31,.4);width:100%;max-width:480px;transition:transform .22s var(--ease),opacity .22s;position:relative}
.dlg-h{padding:18px 20px 6px}.dlg-b{padding:8px 20px 16px;color:var(--ink2);font-size:13.5px}.dlg-f{padding:12px 20px 18px;display:flex;justify-content:flex-end;gap:8px}
.menu{position:absolute;right:0;top:calc(100% + 4px);background:#fff;border:1px solid var(--line);border-radius:8px;box-shadow:var(--shadow);min-width:160px;padding:4px;z-index:30;display:none}
.menu.open{display:block}.menu button{display:flex;width:100%;text-align:left;background:none;border:0;padding:8px 10px;border-radius:6px;font-size:13px;cursor:pointer;color:var(--ink);align-items:center;gap:8px}
.menu button:hover{background:#F3F1EC}.menu button.danger{color:var(--crit)}
.rel{position:relative}
/* alerts, states */
.alert{border-radius:var(--r);padding:12px 14px;font-size:13px;border:1px solid}
.alert.err{background:var(--crit-soft);border-color:#F1C5BF;color:#8A2A23}
.alert.warn{background:#FFF8E6;border-color:#F0DFA8;color:#6B5407}
.alert.ok{background:var(--ok-soft);border-color:#BFE1CB;color:#256A40}
.alert.info{background:var(--info-soft);border-color:#C6DBEA;color:#1F4E6E}
.alert.blue{background:var(--accent-soft);border-color:#C9D9F5;color:#1F3F80}
.err-line{font-size:12px;color:var(--crit)}
.empty{border:1px dashed var(--line2);border-radius:var(--rc);padding:36px 20px;text-align:center;color:var(--ink2);background:#FCFBF9}
.empty h3{margin-bottom:6px}
.skel{background:linear-gradient(90deg,#EFECE6 25%,#F7F5F1 50%,#EFECE6 75%);background-size:400% 100%;animation:sh 1.3s ease infinite;border-radius:6px}
@keyframes sh{0%{background-position:100% 0}100%{background-position:0 0}}
.spin{animation:sp 1s linear infinite}@keyframes sp{to{transform:rotate(360deg)}}
.rise{animation:rise .45s var(--ease) both}@keyframes rise{from{opacity:0;transform:translateY(6px)}to{opacity:1;transform:none}}
.drop{border:2px dashed var(--line2);border-radius:var(--rc);padding:26px 16px;text-align:center;cursor:pointer;transition:border-color .16s,background .16s;color:var(--ink2)}
.drop:hover{background:#F6F4EF}.drop.on{border-color:var(--accent);background:var(--accent-soft)}
.filerow{display:flex;align-items:center;gap:8px;border:1px solid #BFE1CB;background:var(--ok-soft);color:#256A40;border-radius:var(--r);padding:8px 10px;font-size:13px}
.bar{height:6px;border-radius:999px;background:var(--na);overflow:hidden}.bar i{display:block;height:100%;border-radius:999px;transition:width .5s var(--ease)}
.code{font-family:"IBM Plex Mono",Consolas,monospace;font-size:12px;background:#F5F3EE;border:1px solid var(--line);border-radius:6px;padding:1px 5px;color:var(--ink)}
pre.block{font-family:"IBM Plex Mono",Consolas,monospace;font-size:12px;background:#F5F3EE;border:1px solid var(--line);border-radius:8px;padding:10px 12px;overflow:auto;margin:0;color:var(--ink);line-height:1.55}
.kbd{font:500 11px "IBM Plex Mono",monospace;border:1px solid var(--line2);border-radius:5px;padding:1px 5px;color:var(--ink3);background:#fff}
.hr{border:0;border-top:1px solid var(--line);margin:0}
/* shell */
.app{min-height:100vh;display:flex;background:var(--paper)}
.side{position:fixed;inset:0 auto 0 0;width:var(--side);border-right:1px solid var(--line);background:#fff;display:flex;flex-direction:column;padding:14px 10px;z-index:20;transition:width .18s var(--ease)}
.side .brand{display:flex;align-items:center;gap:10px;padding:4px 8px;min-width:0}
.side .tag{padding:2px 8px 14px;font-size:11.5px;color:var(--ink3);white-space:nowrap;overflow:hidden}
.nav{display:flex;flex-direction:column;gap:2px}
.nav a{display:flex;align-items:center;gap:10px;padding:8px 10px;border-radius:7px;font-size:13.5px;font-weight:500;color:var(--ink2);white-space:nowrap;overflow:hidden;transition:background .16s,color .16s}
.nav a:hover{background:#F3F1EC;color:var(--ink);text-decoration:none}.nav a.on{background:var(--accent);color:#fff}
.nav a svg{flex:none}
.side .foot{margin-top:auto}
.side .tog{position:absolute;right:-14px;top:30px;width:28px;height:28px;border-radius:999px;border:2px solid var(--paper);background:var(--accent);color:#fff;display:flex;align-items:center;justify-content:center;cursor:pointer;box-shadow:var(--shadow)}
.side .sgrip{position:absolute;right:0;top:0;height:100%;width:6px;cursor:col-resize;touch-action:none}.side .sgrip:hover{background:var(--accent-soft)}
.side.c .tag,.side.c .nav a span,.side.c .brand span,.side.c .foot span{display:none}.side.c .nav a{justify-content:center;padding:8px 0}.side.c .foot .btn{justify-content:center;padding:0}
.topbar{display:none;align-items:center;justify-content:space-between;padding:10px 14px;border-bottom:1px solid var(--line);background:#fff;position:sticky;top:0;z-index:20}
.msheet{position:fixed;inset:0 auto 0 0;width:256px;background:#fff;z-index:45;padding:16px 12px;display:flex;flex-direction:column;transition:transform .28s var(--ease);box-shadow:12px 0 40px -20px rgba(20,24,31,.35)}
.main{flex:1;min-width:0;padding-left:var(--side);transition:padding-left .18s var(--ease)}
.page{max-width:1240px;margin:0 auto;padding:24px 28px 48px}.page.wide{max-width:none}
.pagehead{display:flex;align-items:flex-start;justify-content:space-between;gap:16px;flex-wrap:wrap;margin-bottom:18px}
.pagehead .actions{display:flex;gap:8px;flex-wrap:wrap;align-items:center}
.appbar{position:fixed;left:0;right:0;top:0;z-index:70;background:var(--accent);color:#fff;padding:8px 16px;display:flex;align-items:center;justify-content:center;gap:12px;font-size:13px}
.install{position:fixed;bottom:16px;left:50%;transform:translateX(-50%);width:calc(100% - 32px);max-width:400px;background:#fff;border:1px solid var(--line);border-radius:var(--r);box-shadow:var(--shadow);padding:8px 8px 8px 12px;display:flex;align-items:center;justify-content:space-between;gap:10px;font-size:13px;z-index:70}
@media (max-width:760px){
 .app{flex-direction:column}.side{display:none}.topbar{display:flex;width:100%}.main{padding-left:0;width:100%}.page{padding:16px 16px 40px}
 .g2,.g3{grid-template-columns:minmax(0,1fr)}.g4,.g5,.g6,.g8{grid-template-columns:repeat(2,minmax(0,1fr))}
 .chip{white-space:normal;height:auto;min-height:22px;padding:2px 8px}
 .tbl.cards thead{display:none}.tbl.cards tr{display:block;border:1px solid var(--line);border-radius:var(--r);margin-bottom:8px;background:#fff;padding:4px 0}
 .tbl.cards td{display:flex;justify-content:space-between;align-items:center;gap:12px;border:0;padding:6px 12px;text-align:left}
 .tbl.cards td::before{content:attr(data-th);font-size:11px;font-weight:600;letter-spacing:.05em;text-transform:uppercase;color:var(--ink3);flex:none}
 .tbl.cards td.r{text-align:right}.tbl.cards tr.band td::before{content:none}
 .kpi .v{font-size:20px}.sheet{width:100vw !important}.pagehead .actions{width:100%}
 .tip::after{display:none}
}
</style>
"""

# ----------------------------------------------------------------------------- icons
_ICONS = {
    "archive": '<rect x="3" y="4" width="18" height="4" rx="1"/><path d="M5 8v11a1 1 0 0 0 1 1h12a1 1 0 0 0 1-1V8M10 12h4"/>',
    "archive-restore": '<rect x="3" y="4" width="18" height="4" rx="1"/><path d="M5 8v11a1 1 0 0 0 1 1h12a1 1 0 0 0 1-1V8M12 17v-6M9 14l3-3 3 3"/>',
    "arrow-down": '<path d="M12 5v14M5 12l7 7 7-7"/>',
    "arrow-up": '<path d="M12 19V5M5 12l7-7 7 7"/>',
    "arrow-up-down": '<path d="M7 3v18M3 7l4-4 4 4M17 21V3M13 17l4 4 4-4"/>',
    "arrow-left": '<path d="M19 12H5M12 19l-7-7 7-7"/>',
    "bug": '<path d="M8 2l1.5 2M16 2l-1.5 2"/><rect x="6" y="6" width="12" height="14" rx="6"/><path d="M12 6v14M2 13h4M18 13h4M3 20l3-2M21 20l-3-2M3 6l3 2M21 6l-3 2"/>',
    "check": '<path d="M5 12l5 5L20 7"/>',
    "check-circle": '<circle cx="12" cy="12" r="9"/><path d="M8.5 12l2.5 2.5 4.5-5"/>',
    "chevron-down": '<path d="M6 9l6 6 6-6"/>',
    "chevron-left": '<path d="M15 6l-6 6 6 6"/>',
    "chevron-right": '<path d="M9 6l6 6-6 6"/>',
    "chevron-up": '<path d="M6 15l6-6 6 6"/>',
    "columns": '<rect x="3" y="4" width="18" height="16" rx="2"/><path d="M9 4v16M15 4v16"/>',
    "copy": '<rect x="9" y="9" width="11" height="11" rx="2"/><path d="M5 15V5a2 2 0 0 1 2-2h10"/>',
    "download": '<path d="M12 3v12M6 11l6 6 6-6"/><path d="M4 21h16"/>',
    "external": '<path d="M14 4h6v6M20 4l-9 9"/><path d="M19 14v5a1 1 0 0 1-1 1H5a1 1 0 0 1-1-1V6a1 1 0 0 1 1-1h5"/>',
    "eye": '<path d="M2 12s3.5-6 10-6 10 6 10 6-3.5 6-10 6S2 12 2 12z"/><circle cx="12" cy="12" r="3"/>',
    "eye-off": '<path d="M3 3l18 18M10.6 10.6a3 3 0 0 0 4.2 4.2M9 5.3A10 10 0 0 1 12 5c6.5 0 10 7 10 7a17 17 0 0 1-3.4 4.2M6.4 6.4A17 17 0 0 0 2 12s3.5 7 10 7a10 10 0 0 0 4.5-1"/>',
    "file-down": '<path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/><path d="M14 2v6h6M12 11v7M9 15l3 3 3-3"/>',
    "file-json": '<path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/><path d="M14 2v6h6M9 13c-1 0-1 1-1 1.5S8 16 9 16M15 13c1 0 1 1 1 1.5s0 1.5-1 1.5"/>',
    "file-spreadsheet": '<path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/><path d="M14 2v6h6M8 13h8M8 17h8M12 13v4"/>',
    "file-text": '<path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/><path d="M14 2v6h6M8 13h8M8 17h8"/>',
    "folder": '<path d="M3 7a2 2 0 0 1 2-2h4l2 2h8a2 2 0 0 1 2 2v9a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2z"/>',
    "help": '<circle cx="12" cy="12" r="9"/><path d="M9.5 9.5a2.5 2.5 0 1 1 3.5 2.3c-.7.3-1 .8-1 1.5M12 17h.01"/>',
    "history": '<path d="M3 12a9 9 0 1 0 3-6.7L3 8"/><path d="M3 3v5h5M12 7v5l3 2"/>',
    "info": '<circle cx="12" cy="12" r="9"/><path d="M12 11v5M12 8h.01"/>',
    "layout": '<rect x="3" y="3" width="7" height="9" rx="1"/><rect x="14" y="3" width="7" height="5" rx="1"/><rect x="14" y="12" width="7" height="9" rx="1"/><rect x="3" y="16" width="7" height="5" rx="1"/>',
    "loader": '<path d="M12 2v4M12 18v4M4.9 4.9l2.8 2.8M16.3 16.3l2.8 2.8M2 12h4M18 12h4M4.9 19.1l2.8-2.8M16.3 7.7l2.8-2.8"/>',
    "logout": '<path d="M10 17l5-5-5-5M15 12H3"/><path d="M13 3h6v18h-6"/>',
    "map-pin": '<path d="M12 21s7-6.5 7-11a7 7 0 1 0-14 0c0 4.5 7 11 7 11z"/><circle cx="12" cy="10" r="2.5"/>',
    "menu": '<path d="M4 6h16M4 12h16M4 18h16"/>',
    "more": '<circle cx="5" cy="12" r="1.5"/><circle cx="12" cy="12" r="1.5"/><circle cx="19" cy="12" r="1.5"/>',
    "pencil": '<path d="M12 20h9M16.5 3.5a2.1 2.1 0 0 1 3 3L7 19l-4 1 1-4z"/>',
    "play": '<path d="M6 4l14 8-14 8z"/>',
    "plug": '<path d="M9 2v6M15 2v6M6 8h12v4a6 6 0 0 1-12 0zM12 18v4"/>',
    "plus": '<path d="M12 5v14M5 12h14"/>',
    "presentation": '<path d="M3 4h18M5 4v11a1 1 0 0 0 1 1h12a1 1 0 0 0 1-1V4M12 16v4M8 22l4-3 4 3"/>',
    "refresh": '<path d="M21 12a9 9 0 1 1-3-6.7L21 8"/><path d="M21 3v5h-5"/>',
    "rotate": '<path d="M3 12a9 9 0 1 0 3-6.7L3 8"/><path d="M3 3v5h5"/>',
    "search": '<circle cx="11" cy="11" r="7"/><path d="M20 20l-3.5-3.5"/>',
    "shield": '<path d="M12 2l8 3v6c0 5-3.5 9-8 11-4.5-2-8-6-8-11V5z"/><path d="M9 12l2 2 4-4"/>',
    "sparkles": '<path d="M12 3l1.8 5.2L19 10l-5.2 1.8L12 17l-1.8-5.2L5 10l5.2-1.8zM5 18l.7 2 2 .7-2 .7-.7 2-.7-2-2-.7 2-.7z"/>',
    "target": '<circle cx="12" cy="12" r="10"/><circle cx="12" cy="12" r="6"/><circle cx="12" cy="12" r="2"/>',
    "trash": '<path d="M3 6h18M8 6V4h8v2M6 6l1 14h10l1-14M10 10v7M14 10v7"/>',
    "upload-cloud": '<path d="M12 21V11M8 15l4-4 4 4"/><path d="M20 17a4 4 0 0 0-1-7.9A6 6 0 0 0 7.5 7.5 4.5 4.5 0 0 0 5 16"/>',
    "x": '<path d="M18 6L6 18M6 6l12 12"/>',
    "clock": '<circle cx="12" cy="12" r="9"/><path d="M12 7v5l3 2"/>',
    "link": '<path d="M10 14a4 4 0 0 0 5.7 0l3-3a4 4 0 0 0-5.7-5.7l-1 1"/><path d="M14 10a4 4 0 0 0-5.7 0l-3 3a4 4 0 0 0 5.7 5.7l1-1"/>',
    "user": '<circle cx="12" cy="8" r="4"/><path d="M4 21a8 8 0 0 1 16 0"/>',
    "users": '<circle cx="9" cy="8" r="4"/><path d="M2 21a7 7 0 0 1 14 0M16 4a4 4 0 0 1 0 8M22 21a7 7 0 0 0-5-6.7"/>',
    "settings": '<circle cx="12" cy="12" r="3"/><path d="M19.4 15a1.7 1.7 0 0 0 .3 1.8l.1.1a2 2 0 1 1-2.8 2.8l-.1-.1a1.7 1.7 0 0 0-1.8-.3 1.7 1.7 0 0 0-1 1.5V21a2 2 0 1 1-4 0v-.1a1.7 1.7 0 0 0-1.1-1.5 1.7 1.7 0 0 0-1.8.3l-.1.1a2 2 0 1 1-2.8-2.8l.1-.1a1.7 1.7 0 0 0 .3-1.8 1.7 1.7 0 0 0-1.5-1H3a2 2 0 1 1 0-4h.1a1.7 1.7 0 0 0 1.5-1.1 1.7 1.7 0 0 0-.3-1.8l-.1-.1a2 2 0 1 1 2.8-2.8l.1.1a1.7 1.7 0 0 0 1.8.3H9a1.7 1.7 0 0 0 1-1.5V3a2 2 0 1 1 4 0v.1a1.7 1.7 0 0 0 1 1.5 1.7 1.7 0 0 0 1.8-.3l.1-.1a2 2 0 1 1 2.8 2.8l-.1.1a1.7 1.7 0 0 0-.3 1.8V9a1.7 1.7 0 0 0 1.5 1H21a2 2 0 1 1 0 4h-.1a1.7 1.7 0 0 0-1.5 1z"/>',
}


def icon(name, size=16, color="currentColor", cls=""):
    p = _ICONS[name]
    c = ' class="%s"' % cls if cls else ""
    return ('<svg%s width="%d" height="%d" viewBox="0 0 24 24" fill="none" stroke="%s" stroke-width="1.8" '
            'stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">%s</svg>') % (c, size, size, color, p)


# ----------------------------------------------------------------------------- primitives
def btn(label, kind="", ico=None, size="", attrs="", tip=None, disabled=False):
    cls = " ".join(x for x in ["btn", kind, size, "tip" if tip else ""] if x)
    i = (icon(ico, 14 if size == "sm" else 15) + " ") if ico else ""
    t = ' data-tip="%s"' % esc(tip) if tip else ""
    d = " disabled" if disabled else ""
    return '<button class="%s"%s%s %s>%s%s</button>' % (cls, t, d, attrs, i, label)


def chip(label, tone="grey", tip=None, attrs="", xs=False):
    cls = "chip %s%s%s" % (tone, " xs" if xs else "", " tip" if tip else "")
    t = ' data-tip="%s"' % esc(tip) if tip else ""
    return '<span class="%s"%s %s>%s</span>' % (cls, t, attrs, label)


def dot_chip(label, tone):
    col = {"crit": "var(--crit)", "high": "var(--high)", "med": "var(--med)", "low": "var(--low)", "ok": "var(--ok)",
           "info": "var(--info)", "grey": "var(--ink3)", "blue": "var(--accent)", "violet": "var(--violet)"}[tone]
    return '<span class="row" style="gap:6px;font-size:13px;font-weight:500"><i class="dot" style="background:%s"></i>%s</span>' % (col, label)


def kpi(label, value, sub="", tone="", tip=None, attrs="", click=False):
    col = {"": "var(--ink)", "accent": "var(--accent)", "ok": "var(--ok)", "crit": "var(--crit)", "high": "var(--high)",
           "med": "var(--med)", "grey": "var(--ink3)"}[tone]
    t = ' data-tip="%s"' % esc(tip) if tip else ""
    cls = "kpi" + (" click" if click else "") + (" tip" if tip else "")
    tag = "button" if click else "div"
    return T("""<[[tag]] class="[[cls]]"[[t]] [[attrs]]><span class="lbl">[[label]]</span><span class="v num" style="color:[[col]]">[[value]]</span><span class="faint" style="font-size:12px">[[sub]]</span></[[tag]]>""",
             tag=tag, cls=cls, t=t, attrs=attrs, label=label, col=col, value=value, sub=sub)


def tabs(name, items):
    """items: [(key, label_html)]. Bound to {{name.key.cls}} / {{name.key.pick}} / {{name.key.aria}}."""
    out = []
    for k, label in items:
        out.append(T('<button role="tab" class="tab {{[[n]].[[k]].cls}}" aria-selected="{{[[n]].[[k]].aria}}" onClick="{{[[n]].[[k]].pick}}">[[label]]</button>',
                     n=name, k=k, label=label))
    return '<div class="tabs" role="tablist">%s</div>' % "".join(out)


def panel(name, key, inner):
    return T('<sc-if value="{{[[n]].[[k]].on}}" hint-placeholder-val="{{true}}">[[inner]]</sc-if>', n=name, k=key, inner=inner)


def sheet(name, head_html, body_html, foot_html="", aria="Panel"):
    """Right sheet bound to {{sheets.name.*}} (see logic.js sheetVals)."""
    return T("""
<div class="ov" style="opacity:{{sheets.[[n]].ovOp}};pointer-events:{{sheets.[[n]].pe}};z-index:{{sheets.[[n]].oz}}" onClick="{{sheets.[[n]].close}}"></div>
<aside class="sheet" role="dialog" aria-label="[[aria]]" style="width:{{sheets.[[n]].w}};transform:{{sheets.[[n]].tx}};z-index:{{sheets.[[n]].z}}">
  <div class="grip" role="separator" aria-orientation="vertical" aria-label="Resize panel (drag, or use arrow keys)" tabindex="0" title="Drag to resize"
       onPointerDown="{{sheets.[[n]].gDown}}" onPointerMove="{{sheets.[[n]].gMove}}" onPointerUp="{{sheets.[[n]].gUp}}" onKeyDown="{{sheets.[[n]].gKey}}"><i></i></div>
  <div class="sheet-h"><div class="grow">[[head]]</div><button class="xbtn" aria-label="Close" onClick="{{sheets.[[n]].close}}">[[x]]</button></div>
  <div class="sheet-b">[[body]]</div>
  [[foot]]
</aside>""", n=name, aria=esc(aria), head=head_html, body=body_html, x=icon("x", 16), foot=('<div class="sheet-f">%s</div>' % foot_html) if foot_html else "")


def dialog(name, title, body_html, actions_html, width=480):
    return T("""
<div class="dlg-ov" style="opacity:{{dlg.[[n]].op}};pointer-events:{{dlg.[[n]].pe}}" onClick="{{dlg.[[n]].close}}">
  <div class="dlg" role="dialog" aria-modal="true" aria-label="[[t]]" style="max-width:[[w]]px;transform:{{dlg.[[n]].tx}}" onClick="{{stop}}" onKeyDown="{{dlg.[[n]].key}}" tabindex="-1">
    <button class="xbtn" style="position:absolute;right:10px;top:10px" aria-label="Close" onClick="{{dlg.[[n]].close}}">[[x]]</button>
    <div class="dlg-h"><h2 style="font-size:16px">[[title]]</h2></div>
    <div class="dlg-b">[[body]]</div>
    <div class="dlg-f">[[actions]]</div>
  </div>
</div>""", n=name, t=esc(re.sub("<[^>]+>", "", title)), w=width, title=title, body=body_html, actions=actions_html, x=icon("x", 16))


def kebab(hole, items, aria="Actions"):
    """Per-row kebab. `hole` is the item path prefix, e.g. 'r.menu' -> {{r.menu.toggle}}, {{r.menu.cls}}."""
    its = "".join('<button class="%s" onClick="%s">%s%s</button>' % (cls, h, (icon(ic, 14) + " ") if ic else "", label)
                  for label, h, cls, ic in items)
    return T("""<span class="rel" onClick="{{stop}}"><button class="btn ghost icon sm" aria-label="[[aria]]" aria-haspopup="menu" onClick="{{[[h]].toggle}}">[[more]]</button><div class="menu {{[[h]].cls}}" role="menu">[[items]]</div></span>""",
             aria=esc(aria), h=hole, more=icon("more", 15), items=its)


def th(name, key, label, align="", tip=None, sortable=True):
    """Sortable header bound to {{name.h.key.*}} from sortVals."""
    cls = ' class="r"' if align == "r" else ""
    if not sortable:
        return '<th%s>%s</th>' % (cls, label)
    t = (' class="tip" data-tip="%s"' % esc(tip)) if tip else ""
    return T('<th[[cls]] aria-sort="{{[[n]].h.[[k]].aria}}"><button[[t]] onClick="{{[[n]].h.[[k]].pick}}">[[label]] <span style="opacity:{{[[n]].h.[[k]].op}}">{{[[n]].h.[[k]].arrow}}</span></button></th>',
             cls=cls, n=name, k=key, t=t, label=label)


def dropzone(name, label, hint, aria, ico="upload-cloud"):
    return T("""<div class="drop {{drop.[[n]].cls}}" role="button" tabindex="0" aria-label="[[aria]]" onClick="{{drop.[[n]].pick}}" onDragOver="{{drop.[[n]].over}}" onDragLeave="{{drop.[[n]].leave}}" onDrop="{{drop.[[n]].pick}}">
  <div style="display:flex;justify-content:center;margin-bottom:8px;color:var(--ink3)">[[ico]]</div>
  <div style="font-weight:600;color:var(--ink)">[[label]]</div><div class="sub" style="font-size:12.5px;margin-top:2px">[[hint]]</div></div>""",
             n=name, aria=esc(aria), ico=icon(ico, 26), label=label, hint=hint)


def filerow(name, remove_aria_hole):
    return T("""<div class="filerow">[[ico]]<span class="grow" style="overflow:hidden;text-overflow:ellipsis;white-space:nowrap">{{drop.[[n]].file}}</span><span class="num faint" style="color:#256A40">{{drop.[[n]].size}}</span><button class="xbtn" aria-label="{{[[a]]}}" onClick="{{drop.[[n]].clear}}">[[x]]</button></div>""",
             ico=icon("file-spreadsheet", 15), n=name, a=remove_aria_hole, x=icon("x", 14))


def states(default_html, loading_html, empty_html, error_html, gated_html=None):
    parts = [
        T('<sc-if value="{{is.default}}" hint-placeholder-val="{{true}}">[[h]]</sc-if>', h=default_html),
        T('<sc-if value="{{is.loading}}" hint-placeholder-val="{{false}}">[[h]]</sc-if>', h=loading_html),
        T('<sc-if value="{{is.empty}}" hint-placeholder-val="{{false}}">[[h]]</sc-if>', h=empty_html),
        T('<sc-if value="{{is.error}}" hint-placeholder-val="{{false}}">[[h]]</sc-if>', h=error_html),
    ]
    if gated_html is not None:
        parts.append(T('<sc-if value="{{is.gated}}" hint-placeholder-val="{{false}}">[[h]]</sc-if>', h=gated_html))
    return "".join(parts)


def skel(w="100%", h="14px", extra=""):
    return '<div class="skel" style="width:%s;height:%s;%s"></div>' % (w, h, extra)


def alert(kind, html, dismiss_hole=None):
    d = ('<button class="xbtn" style="margin-left:auto" aria-label="Dismiss" onClick="{{%s}}">%s</button>' % (dismiss_hole, icon("x", 14))) if dismiss_hole else ""
    return '<div class="alert %s row" role="alert" style="align-items:flex-start;gap:10px"><div class="grow">%s</div>%s</div>' % (kind, html, d)


def request_access_form(heading=True):
    h = '<h2 style="font-size:15px;margin-bottom:4px">Request access to run assessments</h2>' if heading else ""
    return T("""<div class="card card-b rise" style="max-width:520px">[[h]]
<p class="sub" style="font-size:13px;margin-bottom:12px">Running a review or assessment is switched on per organisation. Send us your details and we will enable it.</p>
<sc-if value="{{req.sent}}" hint-placeholder-val="{{false}}"><p role="status" class="sub">Thanks. We will enable assessments for your organisation and email you.</p></sc-if>
<sc-if value="{{req.form}}" hint-placeholder-val="{{true}}">
<div class="stack" style="gap:10px">
 <div><label class="label">Name</label><input class="input" style="width:100%" value="{{req.name}}" onChange="{{req.setName}}" maxlength="200"></div>
 <div><label class="label">Work email</label><input class="input" type="email" style="width:100%" value="{{req.email}}" onChange="{{req.setEmail}}"></div>
 <div aria-hidden="true" style="display:none"><label>Website</label><input name="website" tabindex="-1" autocomplete="off"></div>
 <button class="btn primary" style="width:100%;height:40px" onClick="{{req.submit}}">{{req.btn}}</button>
</div></sc-if></div>""", h=h)


# ----------------------------------------------------------------------------- shell
NAV = [("dashboard", "SOW Review", "layout"), ("mitre", "MITRE Assessment", "target"), ("codereview", "Code Security Review", "bug")]


def _nav(active, mobile=False):
    out = []
    for key, label, ic in NAV:
        on = " on" if key == active else ""
        out.append('<a href="#" class="%s"%s>%s<span>%s</span></a>' % (on.strip(), (' title="%s"' % label) if not mobile else "", icon(ic, 16), label))
    on = " on" if active == "admin" else ""
    out.append(T('<sc-if value="{{shell.admin}}" hint-placeholder-val="{{true}}"><a href="#" class="[[on]]">[[ic]]<span>Admin</span></a></sc-if>', on=on.strip(), ic=icon("shield", 16)))
    return '<nav class="nav" aria-label="Main">%s</nav>' % "".join(out)


def app_shell(active, body_html, wide=False):
    brand = '<div class="brand">%s<span style="font-weight:600;font-size:14px">ScopeWise</span></div>' % icon("file-text", 18, "var(--accent)")
    return T("""
<div class="app" style="--side:{{shell.sideW}}" data-screen="[[stem]]" data-ready="{{ready}}" onClick="{{root}}">
  <aside class="side {{shell.cls}}" aria-label="Sidebar">
    [[brand]]
    <div class="tag">Catch contract risk before you sign.</div>
    [[nav]]
    <div class="foot"><button class="btn ghost sm" style="width:100%;justify-content:flex-start">[[lo]]<span>Log out</span></button></div>
    <button class="tog" aria-label="{{shell.togLabel}}" onClick="{{shell.toggle}}"><sc-if value="{{shell.collapsed}}" hint-placeholder-val="{{false}}">[[cr]]</sc-if><sc-if value="{{shell.expanded}}" hint-placeholder-val="{{true}}">[[cl]]</sc-if></button>
    <sc-if value="{{shell.expanded}}" hint-placeholder-val="{{true}}"><div class="sgrip" role="separator" aria-orientation="vertical" aria-label="Resize sidebar" onPointerDown="{{shell.gDown}}" onPointerMove="{{shell.gMove}}" onPointerUp="{{shell.gUp}}"></div></sc-if>
  </aside>
  <div class="topbar">[[brand]]<button class="btn ghost icon sm" aria-label="Open navigation menu" onClick="{{shell.openMobile}}">[[menu]]</button></div>
  <div class="ov" style="opacity:{{shell.mOvOp}};pointer-events:{{shell.mPe}};z-index:44" onClick="{{shell.closeMobile}}"></div>
  <div class="msheet" style="transform:{{shell.mTx}}" aria-label="Navigation">
    <div class="row between" style="margin-bottom:14px">[[brand]]<button class="xbtn" aria-label="Close" onClick="{{shell.closeMobile}}">[[x]]</button></div>
    [[mnav]]
    <div class="foot" style="margin-top:auto"><button class="btn ghost sm" style="width:100%;justify-content:flex-start">[[lo]]<span>Log out</span></button></div>
  </div>
  <main class="main"><div class="page[[wide]]">[[body]]</div></main>
</div>""", stem="[[stem]]", brand=brand, nav=_nav(active), mnav=_nav(active, True), lo=icon("logout", 15), menu=icon("menu", 18),
             x=icon("x", 16), wide=" wide" if wide else "", body=body_html, cr=icon("chevron-right", 15, "#fff"), cl=icon("chevron-left", 15, "#fff"))


# ----------------------------------------------------------------------------- assembler
HEAD = """<!doctype html>
<html>
<head>
  <meta charset="utf-8">
  <script src="./support.js"></script>
</head>
<body>
<x-dc>
<helmet>[[css]][[extra_css]]</helmet>
"""

TAIL = """
</x-dc>
<script data-dc-script data-props='[[props]]'>
class Component extends DCLogic {
  constructor(p){ super(p); this.state = [[init]]; this._drag = null; }
  data(){ return [[data]]; }
[[logic]]
  renderVals(){
    const S = this.state, D = this.data(), P = this.props || {};
    const base = { ready:'1', stop:(e)=>{ e && e.stopPropagation && e.stopPropagation(); }, root:()=>this.closeAll(),
      shell:this.shellVals(), is:this.viewFlags(), req:this.reqVals() };
    const vals = (function(self){ [[vals]] }).call(this, this);
    return Object.assign(base, vals);
  }
}
</script>
</body>
</html>
"""

DEFAULT_PROPS = {
    "$preview": {"width": 1440, "height": 900},
    "view": {"editor": "enum", "options": ["default", "loading", "empty", "error", "gated"], "default": "default", "section": "State"},
    "admin": {"editor": "boolean", "default": True, "section": "State"},
}

BASE_STATE = {
    "shell": {"collapsed": False, "width": 224, "mobileOpen": False},
    "sheets": {}, "sheetOrder": [], "dlg": None, "dlgArg": None, "menu": None, "listbox": None,
    "sort": {}, "filters": {}, "search": "", "rename": {"id": None, "value": ""}, "expanded": {},
    "drop": {}, "tab": {}, "req": {"sent": False, "name": "", "email": "", "busy": False}, "busy": {},
}


def deep_merge(a, b):
    out = dict(a)
    for k, v in b.items():
        out[k] = deep_merge(out[k], v) if isinstance(v, dict) and isinstance(out.get(k), dict) else v
    return out


def screen(stem, body_html, vals_js, data=None, state=None, props=None, extra_css="", phone=False):
    """Assemble one artboard. `body_html` must already include the shell (use app_shell) or be a bare page."""
    p = dict(DEFAULT_PROPS)
    if props:
        p.update(props)
    if phone:
        p["$preview"] = {"width": 390, "height": 844}
    init = deep_merge(BASE_STATE, state or {})
    html = T(HEAD, css=CSS, extra_css=extra_css) + body_html.replace("[[stem]]", stem) + T(
        TAIL, props=dc_props(p), init=js_data(init), data=js_data(data or {}), logic=LOGIC_JS, vals=vals_js)
    return html


def write(outdir, stem, html):
    with open(os.path.join(outdir, stem + ".dc.html"), "w", encoding="utf-8") as f:
        f.write(html)
