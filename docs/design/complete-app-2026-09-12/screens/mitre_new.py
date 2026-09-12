"""/mitre/new — MITRE assessment intake wizard. Source: inventory/mitre.md §2."""
from dc import T, app_shell, screen, btn, chip, kpi, icon, tabs, panel, sheet, dropzone, filerow, alert, dth, dcell, request_access_form, esc

STEM = "MitreNew"
PAGE, TITLE, ORDER = "mitre", "New MITRE assessment", 20

INDUSTRIES = ["Financial Services", "Banking", "Insurance", "Healthcare", "Manufacturing", "Energy & Utilities",
              "Technology", "Telecommunications", "Retail & E-commerce", "Government & Public Sector", "Education",
              "Transportation & Logistics", "Media & Entertainment", "Professional Services", "Hospitality & Food Service",
              "Pharmaceuticals & Life Sciences", "Agriculture & Food Production", "Mining & Metals", "Aerospace & Defense",
              "Construction & Engineering", "Maritime & Shipping", "Other"]
REGIONS = ["North America", "Europe", "Asia-Pacific", "Middle East & Africa", "Latin America", "United Kingdom", "India", "Global"]
ACTORS = [("G0016", "APT29"), ("G1015", "Scattered Spider"), ("G0176", "LockBit"), ("G0032", "Lazarus Group"),
          ("G0046", "FIN7"), ("G0096", "APT41"), ("G0094", "Kimsuky"), ("G0129", "Mustang Panda")]
# field key, label, detected column #, sample header
COLUMNS = [("name", "Use-case name", 1, "Use Case Name"), ("techniques", "MITRE techniques", 3, "MITRE Technique(s)"),
           ("logic", "Detection logic", 2, "Rule Logic"), ("description", "Description", 4, "Description"),
           ("logsource", "Log source", 5, "Log Source"), ("status", "Status", 6, "Status")]
SAMPLE_ROWS = [
    ["Impossible travel sign-in", "distance(loc1,loc2)/time > threshold", "T1078.004",
     "Detects sign-ins from geographically impossible locations for the same account", "Entra sign-in logs", "Enabled"],
    ["Suspicious PowerShell EncodedCommand", "cmdline contains '-enc'", "T1059.001",
     "Flags obfuscated PowerShell execution", "Windows process creation (Sysmon 1)", "Enabled"],
    ["Legacy VPN brute force", "auth_failures > 10 in 5m", "T1110", "Repeated failed VPN logins", "VPN gateway logs", "Disabled"],
]
TILES = {"total": 175, "tagged": 153, "untagged": 18, "invalid": 4}
RULES = [
    {"id": "u1", "name": "Impossible travel sign-in", "tech": "T1078.004", "status": "Enabled", "tag": "customer", "logsrc": "Entra sign-in logs"},
    {"id": "u2", "name": "Suspicious PowerShell EncodedCommand", "tech": "T1059.001", "status": "Enabled", "tag": "customer", "logsrc": "Sysmon process creation"},
    {"id": "u3", "name": "Impossible travel (secondary correlation)", "tech": "T1078.004", "status": "Enabled", "tag": "ai", "logsrc": "Okta system log"},
    {"id": "u4", "name": "Privileged group membership change", "tech": "T1098", "status": "Enabled", "tag": "manual", "logsrc": "AD audit logs"},
    {"id": "u5", "name": "New scheduled task created", "tech": "", "status": "Enabled", "tag": "unmapped", "logsrc": "Windows Security 4698"},
    {"id": "u6", "name": "Outbound traffic to rare domain", "tech": "", "status": "Enabled", "tag": "unmapped", "logsrc": "DNS query logs"},
    {"id": "u7", "name": "Rule with malformed technique tag", "tech": "TA0099X", "status": "Enabled", "tag": "invalid", "logsrc": "Proxy logs"},
    {"id": "u8", "name": "Legacy VPN brute force", "tech": "T1110", "status": "Disabled", "tag": "customer", "logsrc": "VPN gateway logs"},
]
DATA = {"actors": [{"id": i, "name": n} for i, n in ACTORS], "rules": RULES, "tiles": TILES}

# ------------------------------------------------------------------------ static building blocks
PRIVACY = alert("info", icon("shield", 16, "var(--info)") +
                " We never ask for credentials, raw log data, or personal data — upload rule metadata and environment "
                "inventory only. Files are stored encrypted; only minimal rule excerpts are sent for AI tagging.")

SRC_TABS = tabs("src", [("file", "Upload a file"), ("sentinel", "Pull from Microsoft Sentinel"), ("splunk", "Pull from Splunk")]
                ).replace('role="tablist">', 'role="tablist" aria-label="Rule source">')

DZ_RULES = dropzone("rules", "Drag &amp; drop or click to select", "xlsx, xls, csv, pdf or docx · up to 50MB",
                     "Detection rules export: choose a file or drag it here")
FR_RULES = filerow("rules", "drop.rules.removeAria")
DZ_ENV = dropzone("env", "Drag &amp; drop or click to select", "xlsx with Assets, Log Sources, Tooling, Crown Jewels sheets",
                   "Environment workbook (recommended): choose a file or drag it here")
FR_ENV = filerow("env", "drop.env.removeAria")

FILES_CARD = T("""
<div class="card rise" style="margin-top:12px"><div class="card-h"><h2 style="font-size:15px">Your files</h2></div>
<div class="card-b">
<div class="grid g2" style="gap:14px">
 <div><label class="label">Detection rules export <span class="req">*</span></label>[[dzr]]
   <sc-if value="{{drop.rules.has}}" hint-placeholder-val="{{false}}"><div style="margin-top:8px">[[frr]]</div></sc-if></div>
 <div><label class="label">Environment workbook (recommended)</label>[[dze]]
   <sc-if value="{{drop.env.has}}" hint-placeholder-val="{{true}}"><div style="margin-top:8px">[[fre]]</div></sc-if></div>
</div>
<p class="faint" style="font-size:12px;margin-top:12px">If one device sends more than one kind of log, list each log type as its own row in Log Sources — "Infoblox - DNS logs" and "Infoblox - SSH logs" — so each stream gets credited separately.</p>
<div class="row wrap" style="gap:18px;margin-top:10px">[[t1]][[t2]]</div>
<p class="faint" style="font-size:12px;margin-top:8px">Without the environment workbook we assess the full ATT&CK matrices, so your score reads lower than reality.</p>
</div></div>""", dzr=DZ_RULES, frr=FR_RULES, dze=DZ_ENV, fre=FR_ENV,
              t1=btn("Use-case template", "link", "download", "sm"), t2=btn("Environment template", "link", "download", "sm"))

SENTINEL_CARD = T("""
<div class="card rise" style="margin-top:12px"><div class="card-h"><h2 style="font-size:15px">Microsoft Sentinel connection</h2></div>
<div class="card-b">
<p class="sub" style="font-size:12.5px;margin-bottom:12px">Read-only pull of your analytics rules via a service principal with the Microsoft Sentinel Reader role. The client secret is used once for this pull and is never stored.</p>
<div class="grid g2" style="gap:10px">
 <div><label class="label">Tenant ID (GUID)</label><input class="input" style="width:100%" value="{{form.tenantId}}" onChange="{{setTenantId}}"></div>
 <div><label class="label">Client ID (GUID)</label><input class="input" style="width:100%" value="{{form.clientId}}" onChange="{{setClientId}}"></div>
 <div><label class="label">Subscription ID (GUID)</label><input class="input" style="width:100%" value="{{form.subId}}" onChange="{{setSubId}}"></div>
 <div><label class="label">Resource group</label><input class="input" style="width:100%" value="{{form.resourceGroup}}" onChange="{{setResourceGroup}}"></div>
 <div><label class="label">Log Analytics workspace</label><input class="input" style="width:100%" value="{{form.workspace}}" onChange="{{setWorkspace}}"></div>
 <div><label class="label">Client secret (never stored)</label><input class="input" type="password" style="width:100%" value="{{form.secret}}" onChange="{{setSecret}}"></div>
</div>
<p class="faint" style="font-size:12px;margin-top:10px">This path doesn't take an environment workbook yet, so the whole ATT&CK matrix set is assessed — the score reads lower than reality.</p>
</div></div>""")

SPLUNK_CARD = T("""
<div class="card rise" style="margin-top:12px"><div class="card-h"><h2 style="font-size:15px">Splunk connection</h2></div>
<div class="card-b">
<p class="sub" style="font-size:12.5px;margin-bottom:12px">Read-only pull of your saved searches via the Splunk REST API. The management port (usually 8089) must be reachable from ScopeWise — for Splunk Cloud that means allowlisting our IP on the stack. The auth token is used once for this pull and is never stored.</p>
<div class="grid g2" style="gap:10px">
 <div><label class="label">Host</label><input class="input" style="width:100%" placeholder="e.g. acme.splunkcloud.com" value="{{form.host}}" onChange="{{setHost}}"></div>
 <div><label class="label">Management port</label><input class="input" style="width:100%" placeholder="8089" value="{{form.port}}" onChange="{{setPort}}"></div>
 <div><label class="label">App</label><input class="input" style="width:100%" placeholder="optional — all apps if empty" value="{{form.app}}" onChange="{{setApp}}"></div>
 <div><label class="label">Auth token (never stored)</label><input class="input" type="password" style="width:100%" value="{{form.token}}" onChange="{{setToken}}"></div>
</div>
</div></div>""")

INDUSTRY_OPTS = '<option value="" disabled>Select…</option>' + "".join('<option>%s</option>' % esc(x) for x in INDUSTRIES)
REGION_OPTS = "".join('<option value="%s"></option>' % esc(x) for x in REGIONS)

ABOUT_CARD = T("""
<div class="card rise" style="margin-top:12px"><div class="card-h"><h2 style="font-size:15px">About this assessment</h2></div>
<div class="card-b">
<div class="grid g2" style="gap:12px">
 <div><label class="label">Assessment name</label><input class="input" style="width:100%" placeholder="e.g. Q3 SOC coverage" value="{{form.name}}" onChange="{{setName}}"></div>
 <div><label class="label">Industry</label><select class="select" style="width:100%" value="{{form.industry}}" onChange="{{setIndustry}}">[[iopts]]</select></div>
 <div><label class="label">Region</label><input class="input" list="mitre-new-region" style="width:100%" placeholder="e.g. North America" value="{{form.region}}" onChange="{{setRegion}}"><datalist id="mitre-new-region">[[ropts]]</datalist></div>
 <div><label class="label">Customer / engagement <span class="faint" style="font-weight:400;text-transform:none;letter-spacing:0">(optional)</span></label>
   <sc-if value="{{isSiem}}" hint-placeholder-val="{{false}}"><div class="input" style="width:100%;height:auto;min-height:36px;border-style:dashed;display:flex;align-items:center;color:var(--ink3);background:#FCFBF9">Auto-set from your SIEM connection so scheduled re-runs group correctly.</div></sc-if>
   <sc-if value="{{isFile}}" hint-placeholder-val="{{true}}"><input class="input" style="width:100%" placeholder="e.g. Acme Corp" value="{{form.customer}}" onChange="{{setCustomer}}"></sc-if>
   <p class="faint" style="font-size:11.5px;margin-top:4px">Compares this run's trend only against the same customer's previous runs.</p>
 </div>
 <div><label class="label">Organization / project</label><input class="input" style="width:100%" placeholder="e.g. Contoso Bank SOC" value="{{form.org}}" onChange="{{setOrg}}"></div>
 <div><label class="label">Department or scope</label><input class="input" style="width:100%" placeholder="e.g. EMEA production estate" value="{{form.dept}}" onChange="{{setDept}}"></div>
 <div><label class="label">Prepared by</label><input class="input" style="width:100%" placeholder="e.g. Jane Doe, Security Engineering" value="{{form.preparedBy}}" onChange="{{setPreparedBy}}"></div>
 <div style="grid-column:1/-1"><label class="label">Purpose</label><textarea class="input" rows="2" style="width:100%" placeholder="e.g. Annual detection-coverage review for the audit committee" value="{{form.purpose}}" onChange="{{setPurpose}}"></textarea></div>
</div>
</div></div>""", iopts=INDUSTRY_OPTS, ropts=REGION_OPTS)

ACTORS_CARD = T("""
<div class="card rise" style="margin-top:12px"><div class="card-h"><h2 style="font-size:15px">Threat actors of concern (optional)</h2></div>
<div class="card-b">
<p class="sub" style="font-size:12.5px;margin-bottom:10px">Pick any groups you track or worry about — gaps in techniques they use will be prioritized in your roadmap. This never changes your coverage score, only the ordering.</p>
<div class="pillbar"><sc-for list="{{actorList}}" as="a" hint-placeholder-count="8">[[chipone]]</sc-for></div>
<hr class="hr" style="margin:16px 0">
<label class="row" style="gap:8px;font-size:13px"><input type="checkbox" checked="{{countDisabled}}" onChange="{{toggleCountDisabled}}"> Count disabled rules as coverage</label>
<p class="faint" style="font-size:12px;margin-top:4px;margin-left:23px">Off (recommended): a disabled rule scores as "partial" at best, since it isn't actually alerting today.</p>
</div></div>""", chipone='<span class="{{a.cls}}" role="button" tabindex="0" aria-pressed="{{a.aria}}" onClick="{{a.toggle}}">{{a.label}}</span>')

EXCL_ROW = T("""<div class="grid g2" style="gap:8px;margin-bottom:8px">
  <input class="input" style="width:100%" placeholder="T1200, mobile, or a platform (e.g. macOS)" aria-label="{{x.targetAria}}" value="{{x.target}}" onChange="{{x.setTarget}}">
  <div class="row" style="gap:8px">
    <input class="input grow" placeholder="Why it's out of scope (required)" value="{{x.reason}}" onChange="{{x.setReason}}">
    <button class="xbtn" aria-label="{{x.removeAria}}" onClick="{{x.remove}}">[[trash]]</button>
  </div>
</div>""", trash=icon("trash", 15))

EXCLUSIONS_CARD = T("""
<div class="card rise" style="margin-top:12px"><div class="card-h"><h2 style="font-size:15px">Scope exclusions</h2></div>
<div class="card-b">
<p class="sub" style="font-size:12.5px;margin-bottom:10px">Tell us what NOT to assess and why — e.g. "mobile: BYOD fleet is unmanaged", "T1200: accepted risk, physical controls". Excluded items leave the score entirely, and the report lists them with your reason.</p>
<sc-for list="{{exclusions}}" as="x" hint-placeholder-count="1">[[row]]</sc-for>
[[add]]
</div></div>""", row=EXCL_ROW, add=btn("Add exclusion", "", "plus", "sm", attrs='aria-label="Add exclusion" onClick="{{addExclusion}}"'))

ERR_BANNER = alert("err", "{{bannerMsg}}")
SUBMIT_BTN = btn("{{submitLabel}}", "primary {{submitCls}}",
                  attrs='style="width:100%;height:40px" aria-disabled="{{submitAria}}" onClick="{{submitForm}}"')
FORM_TAIL = T("""
<sc-if value="{{is.error}}" hint-placeholder-val="{{false}}"><div style="margin-top:12px">[[err]]</div></sc-if>
<div style="margin-top:14px">[[submit]]</div>""", err=ERR_BANNER, submit=SUBMIT_BTN)

# ------------------------------------------------------------------------ parse preview
TILES_ROW = '<div class="grid g4">%s%s%s%s</div>' % (
    kpi("rule(s) found", "{{tiles.nTotal}}", "parsed from your file", "", tip="Click to see these rows", click=True,
        attrs='aria-label="Rule(s) found — click to see these rows" onClick="{{tiles.openAll}}"'),
    kpi("already tagged", "{{tiles.nTagged}}", "ready to use", "ok", tip="Click to see these rows", click=True,
        attrs='aria-label="Already tagged — click to see these rows" onClick="{{tiles.openTagged}}"'),
    kpi("for AI tagging", "{{tiles.nUntagged}}", "no technique yet", "med", tip="Click to see these rows", click=True,
        attrs='aria-label="For AI tagging — click to see these rows" onClick="{{tiles.openUntagged}}"'),
    kpi("invalid tag(s)", "{{tiles.nInvalid}}", "couldn't be parsed", "crit", tip="Click to see these rows", click=True,
        attrs='aria-label="Invalid tag(s) — click to see these rows" onClick="{{tiles.openInvalid}}"'),
)

EXTRACTION_NOTICE = alert("warn", "Your document isn't a spreadsheet, so rules will be AI-extracted from its text when the assessment runs — lower fidelity than the XLSX template.")

COL_CHIPS = "".join(chip("%s: column %d" % (label, col), "outline") for (key, label, col, header) in COLUMNS)
DETECTED_COLS = T("""
<div style="margin-top:14px"><span class="lbl">Detected columns (sheet "Use Cases")</span>
<div class="row wrap" style="gap:6px;margin-top:6px">[[chips]][[adjust]]</div></div>
""", chips=COL_CHIPS, adjust=btn("Adjust columns", "ghost", "columns", "sm",
                                  tip="Columns can only be adjusted before the assessment runs.",
                                  attrs='aria-label="Adjust columns" onClick="{{toggleWizard}}"'))

COL_OPTIONS = "".join('<option value="%d">%d: %s</option>' % (col, col, esc(header)) for (key, label, col, header) in sorted(COLUMNS, key=lambda c: c[2]))
NOT_MAPPED = '<option value="">— not mapped —</option>'


def _field_select(key, label, required, onchange):
    req = ' <span class="req">*</span>' if required else ""
    return T("""<div><label class="label">[[label]][[req]]</label><select class="select" style="width:100%" value="{{colmap.[[key]]}}" onChange="{{[[onchange]]}}">[[na]][[opts]]</select></div>""",
             label=label, req=req, key=key, onchange=onchange, na=NOT_MAPPED, opts=COL_OPTIONS)


FIELD_SELECTS = "".join([
    _field_select("name", "Use-case name", True, "setColName"),
    _field_select("techniques", "MITRE techniques", False, "setColTech"),
    _field_select("logic", "Detection logic", False, "setColLogic"),
    _field_select("description", "Description", False, "setColDesc"),
    _field_select("logsource", "Log source", False, "setColLogsrc"),
    _field_select("status", "Status", False, "setColStatus"),
])

_SAMPLE_COLS = ["Use Case Name", "Rule Logic", "MITRE Technique(s)", "Description", "Log Source", "Status"]
_SAMPLE_HEAD = '<div class="dr dh" style="grid-template-columns:repeat(6,minmax(0,1fr))">' + "".join(
    dth("smp", "c%d" % i, h, sortable=False) for i, h in enumerate(_SAMPLE_COLS)) + '</div>'


def _sample_row(vals):
    return '<div class="dr" style="grid-template-columns:repeat(6,minmax(0,1fr))">' + "".join(
        dcell(_SAMPLE_COLS[i], esc(v)) for i, v in enumerate(vals)) + '</div>'


SAMPLE_TABLE = '<div class="dt" style="margin:12px 0">%s%s</div>' % (_SAMPLE_HEAD, "".join(_sample_row(r) for r in SAMPLE_ROWS))

WIZARD = T("""
<div class="card" style="margin-top:12px;background:#FBFAF8;box-shadow:none">
<div class="card-b">
<p class="sub" style="font-size:12.5px;margin-bottom:10px">Map each field to the right column of your file, then apply — we re-read the uploaded file with your mapping. Only the name column is required.</p>
<div class="grid g3" style="gap:10px">[[selects]]</div>
[[table]]
<div class="row" style="gap:8px;margin-top:10px">[[apply]][[cancel]]</div>
</div></div>""", selects=FIELD_SELECTS, table=SAMPLE_TABLE,
              apply=btn("{{applyLabel}}", "primary", size="sm", attrs='onClick="{{applyMapping}}"'),
              cancel=btn("Cancel", "", size="sm", attrs='onClick="{{cancelWizard}}"'))

ENV_ECHO_LINE = ("Environment: Windows, Linux, ESXi, IaaS, Containers, Office Suite, Identity Provider, "
                  "Network Devices, Android, iOS, macOS, SaaS · OT/ICS assets · managed mobile · "
                  "sheets: Assets, Log Sources, Tooling, Crown Jewels")
ENV_ABSENT = alert("warn", "No environment workbook — the full ATT&CK matrices will be assessed, so the score is a lower bound.")
ENV_BLOCK = T("""
<sc-if value="{{envPresent}}" hint-placeholder-val="{{true}}"><p class="sub" style="font-size:12.5px;margin-top:14px">[[line]]</p></sc-if>
<sc-if value="{{envAbsent}}" hint-placeholder-val="{{false}}"><div style="margin-top:14px">[[warn]]</div></sc-if>""", line=ENV_ECHO_LINE, warn=ENV_ABSENT)

WARNINGS = T("""<div class="stack" style="gap:6px;margin-top:12px">[[w1]][[w2]]</div>""",
             w1=alert("warn", 'Three disabled rules were found — they will score as "partial" at best unless you enable "Count disabled rules as coverage" above.'),
             w2=alert("warn", "Four rows have a MITRE Techniques value that couldn't be parsed as a valid ATT&CK ID — see the Invalid tag(s) tile."))

RUN_BTN = btn("{{runLabel}}", "primary", "play", attrs='onClick="{{runAssessment}}"')
BACK_BTN = btn("Back — change files", "", size="sm", attrs='onClick="{{backToFiles}}"')
FOOTER_LINK = btn("Or keep it for later — it's saved in your assessment list.", "link", size="sm")

BOTTOM_ACTIONS = T("""
<sc-if value="{{is.gated}}" hint-placeholder-val="{{false}}">
  <div style="margin-top:14px">[[reqform]]</div>
  <div class="row" style="margin-top:12px">[[back1]]</div>
</sc-if>
<sc-if value="{{ungated}}" hint-placeholder-val="{{true}}">
  <div class="row between wrap" style="margin-top:14px;gap:10px">
    <div class="row" style="gap:10px">[[runbtn]][[back2]]</div>
    <span class="faint num" style="font-size:12px">{{runsHint}}</span>
  </div>
</sc-if>
<div style="margin-top:12px">[[footer]]</div>""", reqform=request_access_form(), back1=BACK_BTN, back2=BACK_BTN, runbtn=RUN_BTN, footer=FOOTER_LINK)

PREVIEW_CARD = T("""
<div class="card rise" style="margin-top:12px"><div class="card-h"><h2 style="font-size:15px">Parse preview — check before running</h2></div>
<div class="card-b">
[[tiles]]
<sc-if value="{{isPdf}}" hint-placeholder-val="{{false}}"><div style="margin-top:12px">[[extraction]]</div></sc-if>
[[detected]]
<sc-if value="{{colmapOpen}}" hint-placeholder-val="{{false}}">[[wizard]]</sc-if>
[[envblock]]
[[warnings]]
<hr class="hr" style="margin:16px 0">
[[bottom]]
</div></div>""", tiles=TILES_ROW, extraction=EXTRACTION_NOTICE, detected=DETECTED_COLS, wizard=WIZARD, envblock=ENV_BLOCK, warnings=WARNINGS, bottom=BOTTOM_ACTIONS)

RULE_CARD_TPL = T("""<div class="card" style="padding:10px 12px;box-shadow:none;margin-bottom:8px">
  <div class="row between" style="gap:8px"><b style="font-size:13px">{{u.name}}</b><span class="chip {{u.tagTone}} xs">{{u.tagText}}</span></div>
  <div class="row wrap" style="gap:8px;margin-top:6px">
    <span class="chip outline xs mono">{{u.techOrNone}}</span><span class="faint" style="font-size:12px">{{u.logsrc}}</span><span class="faint" style="font-size:12px">· {{u.status}}</span>
  </div>
</div>""")
RULE_SHEET_BODY = T("""
<sc-if value="{{isPdf}}" hint-placeholder-val="{{false}}"><p class="sub" style="font-size:12.5px;margin-bottom:10px">Rows from PDF/DOCX documents are AI-extracted when the assessment runs, so this list may be empty until then.</p></sc-if>
<sc-for list="{{ruleCards}}" as="u" hint-placeholder-count="4">[[card]]</sc-for>""", card=RULE_CARD_TPL)
RULE_SHEET = sheet("rules", '<h2 style="font-size:16px">{{sheetTitle}}</h2>', RULE_SHEET_BODY, "", aria="Rule list")

BODY = T("""
<div class="pagehead"><div class="row" style="gap:8px"><span style="color:var(--accent)">[[ic]]</span><h1>New MITRE Assessment</h1></div></div>
<div style="margin-bottom:14px">[[privacy]]</div>
<sc-if value="{{stageForm}}" hint-placeholder-val="{{true}}">
[[tabs]]
[[filepanel]][[sentinelpanel]][[splunkpanel]]
[[about]]
[[actors]]
[[exclusions]]
[[tail]]
</sc-if>
<sc-if value="{{stagePreview}}" hint-placeholder-val="{{false}}">[[preview]]</sc-if>
[[rulesheet]]""", ic=icon("target", 18), privacy=PRIVACY, tabs=SRC_TABS,
          filepanel=panel("src", "file", FILES_CARD), sentinelpanel=panel("src", "sentinel", SENTINEL_CARD), splunkpanel=panel("src", "splunk", SPLUNK_CARD),
          about=ABOUT_CARD, actors=ACTORS_CARD, exclusions=EXCLUSIONS_CARD, tail=FORM_TAIL, preview=PREVIEW_CARD, rulesheet=RULE_SHEET)

VALS = r"""
// Actor chip labels (name · attack_id): APT29 · G0016, Scattered Spider · G1015, LockBit · G0176, Lazarus Group · G0032,
// FIN7 · G0046, APT41 · G0096, Kimsuky · G0094, Mustang Panda · G0129
// Runs-remaining hint text pattern: "{n} run(s) remaining for your organisation" (singular/plural below)
const src = self.tabVals('src', ['file', 'sentinel', 'splunk']);
const curSrc = src.current;
const isFile = curSrc === 'file', isSiem = !isFile;
const f = S.form || {};
const setF = (k) => (e) => self.setIn(['form', k], e.target.value);

const dropRules = Object.assign(self.dropVals('rules', 'acme_sentinel_usecases_v2.xlsx', '36.9 KB'), { removeAria: 'Remove acme_sentinel_usecases_v2.xlsx' });
const dropEnv = Object.assign(self.dropVals('env', 'acme_environment_v2.xlsx', '9.5 KB'), { removeAria: 'Remove acme_environment_v2.xlsx' });
const rulesFile = !!dropRules.file;
const envPresent = !!dropEnv.file;

const actorsSel = S.actors || {};
const actorList = D.actors.map((a) => { const on = !!actorsSel[a.id]; const label = a.name + ' · ' + a.id;
  return { id: a.id, label: label, aria: on ? 'true' : 'false', cls: 'chip ' + (on ? 'violet on' : 'outline'),
    toggle: () => { const n = Object.assign({}, actorsSel); n[a.id] = !on; self.setIn(['actors'], n); } }; });

const exclSrc = (S.exclusions && S.exclusions.length) ? S.exclusions : [{ target: '', reason: '' }];
const exclusions = exclSrc.map((x, i) => ({
  n: i + 1, target: x.target || '', reason: x.reason || '',
  targetAria: 'Exclusion ' + (i + 1) + ' target', removeAria: 'Remove exclusion ' + (i + 1),
  setTarget: (e) => { const arr = exclSrc.slice(); arr[i] = Object.assign({}, arr[i], { target: e.target.value }); self.setIn(['exclusions'], arr); },
  setReason: (e) => { const arr = exclSrc.slice(); arr[i] = Object.assign({}, arr[i], { reason: e.target.value }); self.setIn(['exclusions'], arr); },
  remove: () => { const arr = exclSrc.slice(); arr.splice(i, 1); self.setIn(['exclusions'], arr.length ? arr : [{ target: '', reason: '' }]); },
}));

const submitDisabled = isFile && !rulesFile;
function computeError() {
  if (isFile && !rulesFile) return 'Please add your detection-rule export first';
  if (curSrc === 'sentinel' && !(f.tenantId && f.clientId && f.subId && f.resourceGroup && f.workspace && f.secret)) return 'Please fill in every Sentinel connection field, including the client secret';
  if (curSrc === 'splunk' && !(f.host && f.token)) return 'Please fill in the Splunk host and the auth token';
  if (exclusions.some((x) => (!!x.target.trim()) !== (!!x.reason.trim()))) return 'Every scope exclusion needs both a target and a reason';
  return null;
}
const liveErr = computeError();
const bannerMsg = S.submitErrMsg || liveErr || (isFile ? 'Upload failed' : 'SIEM pull failed');

const TILE_N = D.tiles;
const gated = P.view === 'gated';
const runsRemaining = S.runs == null ? 3 : S.runs;

const sheetId = (S.sheets && S.sheets.rules && S.sheets.rules.id) || 'all';
const TAG_TEXT = { customer: 'Tagged by you', ai: 'AI-mapped — verify', manual: 'Edited by reviewer', unmapped: 'Not mapped to any technique', invalid: 'Tags invalid — treated as untagged' };
const TAG_TONE = { customer: 'ok', ai: 'med', manual: 'blue', unmapped: 'grey', invalid: 'crit' };
const catOf = (r) => (r.tag === 'unmapped' ? 'untagged' : (r.tag === 'invalid' ? 'invalid' : 'tagged'));
const filteredRules = D.rules.filter((r) => sheetId === 'all' || catOf(r) === sheetId);
const ruleCards = filteredRules.map((r) => Object.assign({}, r, { techOrNone: r.tech || '—', tagText: TAG_TEXT[r.tag], tagTone: TAG_TONE[r.tag] }));
const sheetTitle = ({ all: 'All rules (' + TILE_N.total + ')', tagged: 'Already tagged (' + TILE_N.tagged + ')',
  untagged: 'For AI tagging (' + TILE_N.untagged + ')', invalid: 'Invalid tag(s) (' + TILE_N.invalid + ')' })[sheetId];

const colmapS = S.colmap || {};

return {
  src, isFile, isSiem, ungated: !gated,
  form: { name: f.name || '', industry: f.industry || '', region: f.region || '', customer: f.customer || '', org: f.org || '',
    dept: f.dept || '', preparedBy: f.preparedBy || '', purpose: f.purpose || '',
    tenantId: f.tenantId || '', clientId: f.clientId || '', subId: f.subId || '', resourceGroup: f.resourceGroup || '', workspace: f.workspace || '', secret: f.secret || '',
    host: f.host || '', port: f.port || '', app: f.app || '', token: f.token || '' },
  setName: setF('name'), setIndustry: setF('industry'), setRegion: setF('region'), setCustomer: setF('customer'), setOrg: setF('org'),
  setDept: setF('dept'), setPreparedBy: setF('preparedBy'), setPurpose: setF('purpose'),
  setTenantId: setF('tenantId'), setClientId: setF('clientId'), setSubId: setF('subId'), setResourceGroup: setF('resourceGroup'), setWorkspace: setF('workspace'), setSecret: setF('secret'),
  setHost: setF('host'), setPort: setF('port'), setApp: setF('app'), setToken: setF('token'),
  drop: { rules: dropRules, env: dropEnv },
  actorList: actorList,
  countDisabled: !!S.countDisabled, toggleCountDisabled: () => self.setIn(['countDisabled'], !S.countDisabled),
  exclusions: exclusions, addExclusion: () => self.setIn(['exclusions'], exclSrc.concat([{ target: '', reason: '' }])),
  bannerMsg: bannerMsg, submitCls: submitDisabled ? 'disabled' : '', submitAria: submitDisabled ? 'true' : 'false',
  submitLabel: self.busy('upload') ? 'Uploading & parsing…' : 'Upload & preview',
  submitForm: () => { if (submitDisabled) return; const err = computeError(); if (err) { self.setState({ submitError: true, submitErrMsg: err }); return; }
    self.setState({ submitError: false, submitErrMsg: '' }); self.runBusy('upload', 900, () => self.setIn(['stage'], 'preview')); },
  stageForm: S.stage !== 'preview', stagePreview: S.stage === 'preview', backToFiles: () => self.setIn(['stage'], 'form'),
  tiles: { nTotal: String(TILE_N.total), nTagged: String(TILE_N.tagged), nUntagged: String(TILE_N.untagged), nInvalid: String(TILE_N.invalid),
    openAll: () => self.openSheet('rules', 'all', 480), openTagged: () => self.openSheet('rules', 'tagged', 480),
    openUntagged: () => self.openSheet('rules', 'untagged', 480), openInvalid: () => self.openSheet('rules', 'invalid', 480) },
  isPdf: P.format === 'pdf',
  colmapOpen: !!colmapS.open, toggleWizard: () => self.setIn(['colmap', 'open'], !colmapS.open),
  colmap: { name: colmapS.name || '1', techniques: colmapS.techniques || '3', logic: colmapS.logic || '2',
    description: colmapS.description || '4', logsource: colmapS.logsource || '5', status: colmapS.status || '6' },
  setColName: (e) => self.setIn(['colmap', 'name'], e.target.value), setColTech: (e) => self.setIn(['colmap', 'techniques'], e.target.value),
  setColLogic: (e) => self.setIn(['colmap', 'logic'], e.target.value), setColDesc: (e) => self.setIn(['colmap', 'description'], e.target.value),
  setColLogsrc: (e) => self.setIn(['colmap', 'logsource'], e.target.value), setColStatus: (e) => self.setIn(['colmap', 'status'], e.target.value),
  applyLabel: self.busy('remap') ? 'Re-parsing…' : 'Apply mapping',
  applyMapping: () => self.runBusy('remap', 900, () => self.setIn(['colmap', 'open'], false)),
  cancelWizard: () => self.setIn(['colmap', 'open'], false),
  envPresent: envPresent, envAbsent: !envPresent,
  runLabel: self.busy('run') ? 'Starting…' : 'Run assessment', runAssessment: () => self.runBusy('run', 1200),
  runsHint: (runsRemaining === 1 ? '1 run remaining for your organisation' : runsRemaining + ' runs remaining for your organisation'),
  sheetTitle: sheetTitle, ruleCards: ruleCards,
  sheets: { rules: self.sheetVals('rules', 480) },
};
"""

STATE = {
    "stage": "form",
    "tab": {"src": "file"},
    "drop": {"env": {"active": False, "file": "acme_environment_v2.xlsx"}},
    "actors": {},
    "countDisabled": False,
    "exclusions": [{"target": "", "reason": ""}],
    "form": {"name": "", "industry": "", "region": "", "customer": "", "org": "", "dept": "", "preparedBy": "", "purpose": "",
             "tenantId": "", "clientId": "", "subId": "", "resourceGroup": "", "workspace": "", "secret": "",
             "host": "", "port": "", "app": "", "token": ""},
    "colmap": {"open": False, "name": "1", "techniques": "3", "logic": "2", "description": "4", "logsource": "5", "status": "6"},
    "submitError": False, "submitErrMsg": "",
}

TAB_ACTIVE = "document.querySelector('.tab.on') && document.querySelector('.tab.on').textContent.trim() === '%s'"
SHEET_OPEN = "document.querySelector('aside.sheet').style.transform.startsWith('translateX(0')"
SHEET_CLOSED = "getComputedStyle(document.querySelector('aside.sheet').previousElementSibling).opacity === '0'"
CLICKS = [
    {"text": "Pull from Microsoft Sentinel", "check": TAB_ACTIVE % "Pull from Microsoft Sentinel"},
    {"text": "Upload a file", "check": TAB_ACTIVE % "Upload a file"},
    {"css": '[aria-label="Detection rules export: choose a file or drag it here"]',
     "check": "document.body.textContent.includes('acme_sentinel_usecases_v2.xlsx')"},
    {"text": "APT29 · G0016",
     "check": "Array.from(document.querySelectorAll('[aria-pressed]')).some(e => e.getAttribute('aria-pressed') === 'true' && e.textContent.trim() === 'APT29 · G0016')"},
    {"label": "Add exclusion", "check": "document.querySelectorAll('[aria-label^=\"Exclusion \"]').length >= 2"},
    {"text": "Upload & preview", "check": "document.body.textContent.includes('Parse preview — check before running')"},
    {"label": "Already tagged — click to see these rows", "check": SHEET_OPEN},
    {"css": "aside.sheet .sheet-h .xbtn", "check": SHEET_CLOSED},
    {"label": "Adjust columns", "check": "document.body.textContent.includes('Map each field to the right column of your file')"},
    {"text": "Back — change files",
     "check": "!document.body.textContent.includes('Parse preview — check before running') && getComputedStyle(document.querySelector('.card.rise')).opacity === '1'"},
]


def build(phone=False):
    stem = STEM + ("Phone" if phone else "")
    props = {"format": {"editor": "enum", "options": ["xlsx", "pdf"], "default": "xlsx", "section": "State"}}
    html = screen(stem, app_shell("mitre", BODY), VALS, DATA, STATE, props=props, phone=phone)
    return [(stem, html)]
