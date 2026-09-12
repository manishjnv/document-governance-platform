# Inventory — MITRE ATT&CK module (verbatim from the code sweep)

Source files under `apps/web/app/mitre/`: `page.tsx` (list), `new/page.tsx` (intake), `[assessmentId]/page.tsx`
(results shell), `connections/page.tsx`, `lib.ts` (all display metadata), `components/` (ExecutiveBand,
UploadSummaryCard, CoverageHeatmap, GapsRoadmap, AssumptionsNA, CompareView, TechniqueDrawer, DrillDownPanel,
RuleListPanel, CoverageSparkline, StateBadge, useSheetResize). No `/mitre/settings` route.

## 0. Shared metadata (lib.ts)

STATE_META — label / tooltip:
- covered → **Covered** — "At least one enabled detection rule maps here with high confidence."
- partial → **Partial** — "Only a disabled rule, a lower-confidence AI mapping, or a covered sub-technique reaches
  this — treat it as half-covered."
- not_covered → **Not covered** — "No detection rule maps here — this technique is a gap."
- not_applicable → **N/A** — "Doesn't apply to your environment (or was excluded by you), so it doesn't count toward
  the coverage percentage."
STATUS_META: pending **Not run yet** (grey) · running **Running** (sky) · completed **Completed** (emerald) ·
failed **Failed** (rose).
FEASIBILITY_META: short **Short term** "0–3 months: the log source this detection needs is already onboarded —
you can build it now." · mid **Mid term** "3–9 months: security tooling you already own can provide the needed
telemetry — onboard it first, then build the detection." · long **Long term** "9–18 months: needs a new telemetry
capability or bespoke detection engineering."
SOURCE_META: customer **Tagged by you** ("This mapping comes from the MITRE technique tag in your uploaded file.")
· keyword **Matched by rule** ("The rule's name or logic contains an exact ATT&CK technique name or a well-known
attacker tool/command, so it was mapped automatically — no AI involved.") · ai **AI-mapped** ("An AI model read
the rule and suggested this technique — spot-check before relying on it.") · manual **Edited by reviewer** ("A
reviewer manually set this mapping — it overrides the original tag, and coverage was recomputed from it.")
MAPPING_STATUS_PLAIN: customer_tagged **Tagged by you** · keyword_tagged **Matched by rule keyword** · ai_tagged
**AI-mapped — verify** · manual **Edited by reviewer** · tool_attested **Tool-attested — alert path confirmed** ·
unmapped **Not mapped to any technique** · invalid **Tags invalid — treated as untagged**.
STATE_PLAIN: **A rule detects this** · **Half-covered** · **No rule detects this** · **Doesn't apply to your
environment**.
Strength: ≥75 strong (emerald) · ≥45 moderate (amber) · else weak (rose). STRENGTH_TIP: "Detection strength
estimates how well the mapped rules would actually catch this technique (rule provenance, enabled state, and
whether the logic references the telemetry the technique expects). It is separate from the coverage % — coverage
only says whether a rule exists."
TIER_TIPS: 1 "Priority 1: top-prevalence technique across independent threat reports — near-universal in real
intrusions." · 2 "Priority 2: very common — a standard part of ransomware and intrusion playbooks." · 3 "Priority
3: common supporting behavior seen in many incidents." · 4 "Unranked: not on the curated priority list — rank
below priority 3."
Domains: **Enterprise**, **ICS / OT**, **Mobile** (that order). fmtDate → `Sep 8, 2026, 08:22 PM` style; `—` null.

---

## 1. `/mitre` — Assessment list

1. Header: `<h1>` Target icon + **MITRE Assessments**; **SIEM connections** (sm outline → /mitre/connections);
   **New assessment** (sm primary, Plus → /mitre/new).
2. Error banner: API detail or **Failed to load assessments**.
3. Toolbar (when items exist): search placeholder **Search by name, customer, or project…** aria-label **Search
   assessments by name, customer, or project** (h-8 w-56); select aria-label **Filter by status**: **All
   statuses**, **Not run yet**, **Running**, **Completed**, **Failed**; checkbox **Show archived (N)** (only if
   any archived); right: CoverageSparkline.
4. Action error: **Could not update the assessment**.
5. Empty: Target icon 28 + copy verbatim: "Upload your SIEM detection rules and we'll show you exactly which MITRE
   ATT&CK techniques you can and can't detect. You get a coverage score, a ranked gap list, and a build roadmap —
   tailored to the log sources you already have." + button **Start your first assessment**.
6. No-match: **No assessments match your search or filters.**
7. Card grid (1/2/3 cols), card `role="link"` aria-label `Open assessment {name}`.

Card: title (truncate); meta line: customer (medium), project_name, SIEM chip **Splunk** / **Sentinel** + ` · auto`
when scheduled (sky), **Archived** chip (bordered); right cluster: **Demo** chip (tooltip **Shared sample
assessment — visible to every signed-in user, read-only**), rename icon (Pencil, aria-label `Rename {name}`,
tooltip **Rename**), archive icon (Archive / ArchiveRestore, aria-label `Archive {name}` / `Unarchive {name}`,
tooltip **Hide from the default list — stays available in Compare. Nothing is deleted.** / **Bring back to the
default list.**); both hidden when not editable. Inline rename editor: input aria-label **New assessment name**,
Enter commits, Escape cancels, Check button aria-label **Save name**, X aria-label **Cancel rename**.
Body completed: `{strict_pct}%` large primary + `coverage — your rules detect {covered} of {applicable}
applicable techniques`; delta vs previous completed run `▲ n` / `▼ n` (title `{+}{delta} points vs your previous
completed run`); per-domain bars **Enterprise** / **ICS / OT** / **Mobile** with `{pct}%`.
Body non-completed: Loader2 (running only) + STATUS_HELP: pending "Uploaded and parsed — open it to run the
assessment." · running "Running now — mapping your rules to ATT&CK techniques. This takes a few minutes." · failed
"The run didn't finish — open it to see why and re-run."
Footer: status pill, `ATT&CK v{attack_version}`, right date.
CoverageSparkline: **Your trend so far** + polyline + `{first}% → {last}%`; tooltip `Coverage % across your {n}
completed runs, oldest to newest.` (needs ≥2 completed runs).
Loading: none today (design a skeleton of 3 cards).

Sample data (prod screenshot): abc ltd (Cisco cdc) 14.4% 132/918, Enterprise 17.9 / ICS 5.2 / Mobile 1.6, ▲14.1,
Completed, Sep 8, 2026 08:22 PM; Mitre Assessment (cisco · Cisco cdc) 0.3% 2/644, Enterprise 0.3, ▼78.4; Acme
MITRE Assessment (Acme Ltd, Demo) 10.4% 95/911, 13 / 4.1 / 0.8, ▲8.2, Aug 2; Test Assessment 2.2% 20/908, 2.3 / 2.1
/ 1.6, Aug 2. Trend 2.2% → 14.4%. Show archived (4).

---

## 2. `/mitre/new` — Intake wizard (max-w-3xl)

`<h1>` **New MITRE Assessment**.
Privacy notice (sky, ShieldCheck): "We never ask for credentials, raw log data, or personal data — upload rule
metadata and environment inventory only. Files are stored encrypted; only minimal rule excerpts are sent for AI
tagging."
Source tablist aria-label **Rule source**: **Upload a file** | **Pull from Microsoft Sentinel** | **Pull from
Splunk**.
Sentinel card **Microsoft Sentinel connection**: blurb "Read-only pull of your analytics rules via a service
principal with the **Microsoft Sentinel Reader** role. The client secret is used once for this pull and is
**never stored**." Fields: **Tenant ID (GUID)**, **Client ID (GUID)**, **Subscription ID (GUID)**, **Resource
group**, **Log Analytics workspace**, **Client secret (never stored)** (password). Footnote "This path doesn't take
an environment workbook yet, so the whole ATT&CK matrix set is assessed — the score reads lower than reality."
Splunk card **Splunk connection**: blurb "Read-only pull of your saved searches via the Splunk REST API. The
management port (usually 8089) must be reachable from ScopeWise — for Splunk Cloud that means allowlisting our IP
on the stack. The auth token is used once for this pull and is **never stored**." Fields **Host** (e.g.
acme.splunkcloud.com), **Management port** (8089), **App** (optional — all apps if empty), **Auth token (never
stored)**.
**Your files** card (upload source): two DropZones: **Detection rules export** + red `*`, hint **xlsx, xls, csv,
pdf or docx · up to 50MB**; **Environment workbook (recommended)**, hint **xlsx with Assets, Log Sources, Tooling,
Crown Jewels sheets**. DropZone: aria-label `{label}: choose a file or drag it here`, UploadCloud icon, **Drag &
drop or click to select** + hint; chosen file → green strip FileSpreadsheet + filename + size + X aria-label
`Remove {file.name}`. Errors `{label}: only {exts} files are supported` / `{label}: file must be under 50MB`.
Note: "If one device sends more than one kind of log, list each log type as its own row in Log Sources —
"Infoblox - DNS logs" and "Infoblox - SSH logs" — so each stream gets credited separately." Template links
(Download icon): **Use-case template**, **Environment template**; note "Without the environment workbook we
assess the full ATT&CK matrices, so your score reads lower than reality."
**About this assessment** card: **Assessment name** (e.g. Q3 SOC coverage); **Industry** select (**Select…** then
Financial Services, Banking, Insurance, Healthcare, Manufacturing, Energy & Utilities, Technology,
Telecommunications, Retail & E-commerce, Government & Public Sector, Education, Transportation & Logistics, Media &
Entertainment, Professional Services, Hospitality & Food Service, Pharmaceuticals & Life Sciences, Agriculture &
Food Production, Mining & Metals, Aerospace & Defense, Construction & Engineering, Maritime & Shipping, Other);
**Region** datalist input (e.g. North America; North America, Europe, Asia-Pacific, Middle East & Africa, Latin
America, United Kingdom, India, Global); **Customer / engagement** (optional; e.g. Acme Corp) — for SIEM sources a
dashed read-only box "Auto-set from your SIEM connection so scheduled re-runs group correctly."; helper "Compares
this run's trend only against the same customer's previous runs."; **Organization / project** (e.g. Contoso Bank
SOC), **Department or scope** (e.g. EMEA production estate), **Prepared by** (e.g. Jane Doe, Security
Engineering); **Purpose** textarea (e.g. Annual detection-coverage review for the audit committee).
**Threat actors of concern (optional)**: blurb "Pick any groups you track or worry about — gaps in techniques they
use will be prioritized in your roadmap. This never changes your coverage score, only the ordering." Toggle chips
aria-pressed, label `{name} · {attack_id}` (e.g. APT29 · G0016, Scattered Spider · G1015, LockBit · G0176,
Lazarus Group · G0032, FIN7 · G0046, APT41 · G0096, Kimsuky · G0094, Mustang Panda · G0129).
Checkbox **Count disabled rules as coverage** + sub-line "Off (recommended): a disabled rule scores as "partial"
at best, since it isn't actually alerting today."
**Scope exclusions**: blurb "Tell us what NOT to assess and why — e.g. "mobile: BYOD fleet is unmanaged",
"T1200: accepted risk, physical controls". Excluded items leave the score entirely, and the report lists them with
your reason." Rows: target input placeholder **T1200, mobile, or a platform (e.g. macOS)** aria-label `Exclusion
{i} target`; reason input placeholder **Why it's out of scope (required)**; Trash2 aria-label `Remove exclusion
{i}`. Button **Add exclusion**.
Submit full width **Upload & preview** / **Uploading & parsing…**. Validation: **Please add your detection-rule
export first** / **Please fill in every Sentinel connection field, including the client secret** / **Please fill
in the Splunk host and the auth token** / **Every scope exclusion needs both a target and a reason**; network
**Upload failed** / **SIEM pull failed**.

Parse preview card **Parse preview — check before running**:
- four tiles (title **Click to see these rows**): `{row_count}` **rule(s) found** · `{tagged}` **already tagged**
  (emerald) · `{untagged}` **for AI tagging** (amber) · `{invalid}` **invalid tag(s)** (rose) → RuleListPanel.
- extraction-pending notice (amber): "Your document isn't a spreadsheet, so rules will be AI-extracted from its
  text when the assessment runs — lower fidelity than the XLSX template."
- **Detected columns** (+ ` (sheet "{sheet}")`) chips `{Label}: column {n}` with labels **Use-case name**,
  **MITRE techniques**, **Detection logic**, **Description**, **Log source**, **Status**; button **Adjust columns**
  (Columns3).
- Column-mapping wizard: blurb "Map each field to the right column of your file, then apply — we re-read the
  uploaded file with your mapping. Only the name column is required." Per-field selects (name has red `*`),
  options **— not mapped —** then `{n}: {header}`; sample-rows table (headers or `col {n}`); **Apply mapping** /
  **Re-parsing…** + **Cancel**. 409: **Columns can only be adjusted before the assessment runs.**
- Environment echo: `Environment: {platforms}` + ` · OT/ICS assets` + ` · managed mobile` + ` · sheets: …`; absent
  (amber): "No environment workbook — the full ATT&CK matrices will be assessed, so the score is a lower bound."
- Warnings: amber list items.
- Gated: RequestAccessForm + **Back — change files**. Ungated: **Run assessment** (Play) / **Starting…** + **Back —
  change files**; `{n} run(s) remaining for your organisation`.
- Footer link **Or keep it for later — it's saved in your assessment list.**
- RuleListPanel subtitle when extraction pending: "Rows from PDF/DOCX documents are AI-extracted when the
  assessment runs, so this list may be empty until then."

Sample: acme_sentinel_usecases_v2.xlsx (175 rules: 153 tagged by you, 1 AI-tagged, 1 reviewer-edited, 4 unmapped,
3 disabled), acme_environment_v2.xlsx (platforms Windows, Linux, ESXi, IaaS, Containers, Office Suite, Identity
Provider, Network Devices, Android, iOS, macOS, SaaS · 29 log sources · 16 tooling · 7 crown jewels; OT/ICS;
Managed mobile).

---

## 3. `/mitre/[assessmentId]` — Results (AppShell fullWidth)

### 3.1 Header
`<h1>` Target + name + **Demo** chip (title **Shared sample assessment — read-only for everyone**); status pill.
Right cluster: **Past runs (N)** (History icon; only when completed and >1 run; opens a listbox aria-label **Past
assessment runs**: rows `{name}` + ` (archived)` + ` — this run` (current disabled), second line `{date} ·
{pct}%` and `({+|-}{delta} vs this)`, right mini-button **Compare** which switches to the Compare tab). **Exec
PDF** (FileDown; tooltip "A 1–3 page executive summary — scorecard, top-5 fixes, roadmap and trend. Made for
forwarding to leadership."), **Full PDF** ("The complete report: executive summary plus the detailed gap register,
coverage tables and appendices."), **XLSX** (FileSpreadsheet; "Full gap register as a spreadsheet — every
technique, rule, gap and assumption."), **PPT** (Presentation; "A presentation-ready briefing deck: headline
result, coverage chart, detection quality, top fixes and roadmap — for sharing with stakeholders."), **Navigator**
(FileJson; "For your technical team: a machine-readable layer file (JSON) to open at attack.mitre.org/navigator —
it paints your coverage onto MITRE's official interactive matrix. Not a readable document; use the PDFs for
that."). All disabled until completed with tooltip **Available once the assessment completes.** `created {date}`
(hidden on small screens). Download errors: **Failed to download the PDF report** / **Failed to download the
PowerPoint deck** / **Failed to download the XLSX export** / **Failed to download the Navigator layer**.
Meta line: `{project_name} · {scope_label} · Prepared by {prepared_by}` + purpose note. SIEM provenance: `Rules
pulled read-only from Microsoft Sentinel by the automatic schedule · connection "{name}" · workspace {ws} · {date}
· {n} rules`.
Run-state blocks: running (sky) Loader2 **Assessing your coverage…** + "We're mapping rules to techniques,
filtering to your environment, and computing the results. Untagged rules go through AI tagging, so this can take a
few minutes. The page refreshes itself."; failed (rose) **This run didn't finish.** + error + **Re-run
assessment**; pending "This assessment is uploaded and parsed, but hasn't been run yet." + **Run assessment**.
409 texts: **Assessment is already running** / **Assessment is already completed**.

### 3.2 ExecutiveBand (8 tiles, each clickable → DrillDownPanel; tooltips end with " Click to see the techniques
behind this number.")
**Coverage** `{pct}%` (primary; tooltip `Strict coverage: {covered} of {applicable} applicable techniques have at
least one qualifying detection. Weighted coverage (partial counts as half): {weighted}%.`) · **Enterprise** ·
**ICS / OT** · **Mobile** · **Covered** (emerald) · **Partial** (amber; subtitle "Each row shows why it only
counts as half-covered.") · **Not covered** (rose) · **N/A**.
Headline: `Of the {applicable} techniques that apply to your environment, your rules can detect {covered} (plus
{partial} partially)` + button **Is {pct}% bad?** (Info icon, dotted underline) tooltip "Probably not as bad as it
looks: early SIEM detection programs typically start under 10% strict coverage, because ATT&CK counts every known
attacker technique. The point of this assessment is the roadmap — the short-term items raise this number fastest
— not the grade itself."
**Top gaps:** first 5 gap chips (rose, tooltip `{name} — {hint}`) → technique drawer. Gated domains: `{Domain}: not
assessed — {reason}`. Right: `ATT&CK v{version} · run {date}`.

### 3.3 Tool-overlay banner (blue)
Bold `Including {tools}'s MITRE-evaluated detections: {adjusted_pct}%`; muted `({extra} open techniques those
tools were evaluated against · Vendor-evaluated in MITRE ATT&CK Evaluations — not proof the alerts are tuned,
monitored, or reaching your SOC. Source: evals.mitre.org)`; split line `Combined covered {n} = {rules} by SIEM
rules ({pct}%) + {tools} via attested tools ({pct}%)`. Admin/reviewer buttons `Client confirmed — attest all {n}
for {tool}` (**Attesting…**) with confirm dialog text `Attest all {n} credited techniques for {tool}?` + "This
records that your SOC receives and monitors {tool}'s alerts for these techniques, creates one auditable
tool-attested rule per technique in your name, and recomputes the coverage score."

### 3.4 UploadSummaryCard **What this assessment is based on**
Left: FileSpreadsheet + rules filename + chip `{n} rules` (→ RuleListPanel **All {n} rules**); status chips
**tagged by you**, **keyword-matched**, **AI-tagged**, **reviewer-edited**, **unmapped**, **invalid tags**, `{n}
disabled`. Right: environment filename + **OT/ICS** / **Managed mobile** chips; line `Platforms: {…} · {n} log
source(s) · {n} tooling · {n} crown jewel(s)` (log-source count is a toggle, title **See what each log source
actually detects for you**, expanding chips `{source}: {n} rule(s) → {m} technique(s)` → RuleListPanel titled
`What {source} gives you: …`). Amber notes for unmapped asset entries. Expander **How we read your inventory ({n}
entries)** (ChevronRight/Down) listing `**{entry}** ({sheet}) → {interpretation}`. No environment → amber "No
environment workbook was uploaded — the full ATT&CK matrices were assessed, so the coverage score is a lower bound."

### 3.5 Tab bar aria-label **Assessment result views**
**Coverage** · **Gaps & Roadmap** · **Assumptions & N/A** · **Compare**. Right: search input placeholder **Is it
covered? Try 'T1486', 'ransomware', 'linux', 'APT29'…** aria-label **Search techniques, attack stages, platforms,
threat groups and rules**; search icon button aria-label **Search this assessment** (tooltip "Search anything — a
technique ID or name, an attack stage, a platform/asset type, a threat group, or one of your rules — and see its
coverage state instantly."); FileDown aria-label/tooltip **Download only this tab as PDF**; FileSpreadsheet
**Download only this tab as Excel** (both hidden on Compare). Search results open DrillDownPanel titled `"{q}" —
{n} technique(s)` subtitle "Matches on technique ID/name, attack stage, platform, threat group, and your rule
names — grouped by coverage state. Click any row for the full story."

### 3.6 Coverage tab (CoverageHeatmap)
Filter bar: **Threat group:** select (**None — full matrix**, then `{name} ({id})`); **Runs on** dropdown (only
when >1 platform; label "Show only techniques that can run on… (% = coverage there)", search **Search
platforms…** at >8, **Clear — all platforms**, checkbox items `{platform}` + `{c}/{a} · {pct}%`); **Detected via**
dropdown ("Show only what a log source's rules detect", **Search sources…**, **Clear — all sources**, items
`{log_source}` + `{n} rule(s)`); threat-group stats `{c}/{a} of their techniques covered ({pct}%) · aka {aliases}`;
right **Download shown ({n})** (FileDown; tooltip "CSV of exactly the techniques currently shown — your
threat-group, platform, log-source and state filters all apply. The report buttons above always export the full
assessment."). Active-lens sentence: `Showing techniques used by **{group}** · that can run on **{platforms}** ·
detected by rules using **{sources}** — counts update to match.` (+ "Platform-independent techniques (e.g.
Reconnaissance) stay visible." / "Group technique lists are MITRE's directly-attributed set — tradecraft via the
group's malware and tools may go further.")
Legend row: toggles per state (aria-pressed; unselected dim; covered swatch is a 3-band gradient **1 rule** /
**2–3 rules** / **4+ rules**; tooltip = STATE tip + for covered " Darker green = more rules detect it (1, 2–3,
4+); the lightest shade means coverage rests on a single rule." + " Click to show only these techniques."); **Show
all** when filtered; **Hide sub-techniques** / **Sub-techniques hidden** (tooltip "Collapse the matrix to parent
techniques only — each parent shows how many of its sub-techniques are covered. Coverage counts don't change.");
hint **Click any technique for details.**
Per-domain sections: collapse button (aria-expanded) + domain label + drill `— {c}/{a} covered ({pct}%)` (+ ` with
current filters`). Grid: one column per tactic (`minmax(148px,1fr)`, horizontally scrollable). Tactic header
button `{name}` + `{c}/{a} covered` (tooltip `{name}: {covered} covered, {partial} partial, {not_covered} not
covered, {na} not applicable (strict {pct}%). Click for the list.`). Cells: `**{id}** {name}` buttons, sub-techniques
indented, covered depth shades, N/A muted; parents show `{c}/{a}` badge when sub-techniques hidden. Delegated
tooltip: `{id} — {name}\n{State}: {reason}. {n} rule(s) map here. {c} of {a} sub-techniques covered (hidden). Click
for details.`
Tactics (Enterprise): Reconnaissance, Resource Development, Initial Access, Execution, Persistence, Privilege
Escalation, Defense Evasion, Credential Access, Discovery, Lateral Movement, Collection, Command and Control,
Exfiltration, Impact. (Prod screenshot counts: Reconnaissance 3/46, Resource Development 0/50, Initial Access
7/22, Execution 15/64, Persistence 22/113, Privilege Escalation 19/96, Defense Evasion 14/148, Credential Access
16/67, Discovery 12/49, Lateral Movement 9/23, Collection 9/41; Enterprise 125/697 (17.9%).)
Design adds the run timeline (hero canvas): slider over runs, Play, cells turn green in the run that covered them.

### 3.7 Gaps & Roadmap tab
Heading **Gaps, ranked by priority** + chip **AI-written text** (violet; tooltip `Recommendation wording was
AI-generated ({model}). All numbers come from computed results, never from the AI.`) or **Standard text** (muted;
tooltip "The AI narrative was unavailable for this run, so recommendations use standard template wording. All
numbers are computed either way.").
Table (first 50 rows; sortable headers with arrows): **#** (title **Sort by rank**) · **Technique** (ID button →
drawer + name) · **Tactic** (hidden <md) · **Priority** (dot + text: **P1 · Critical** rose, **P2 · High** amber,
**P3 · Medium** sky, **Unranked** muted; + **Threat** violet marker tooltip "Prioritized for your declared threat
profile ({labels}): these threats are publicly reported to use this technique. Affects ordering only — never the
coverage score." and **Crown jewel** amber marker tooltip "Relevant to an asset you declared as a crown jewel.
Affects ordering only — never the coverage score.") · **Strength** (hidden <lg; `{score} · Strong/Moderate/Weak`
with dot or `—`) · **Feasibility** (dot + **Build now** emerald / **Onboard logs first** sky / **New capability**
slate; short-term rows add `via {log source}`) · **Recommendation** (min-w 280). Header tooltips: Priority "How
commonly attackers use this technique in real intrusions, from independent threat reports: P1 near-universal, P2
very common, P3 common. A violet dot means it is also tied to your declared industry or threat actors."; Feasibility
"How soon you could realistically build this detection: build now = the needed logs are already onboarded; onboard
first = your existing tooling can provide them; new capability = nothing you own produces this telemetry yet."
Below: **Show all {n} gaps** / **Show top 50 only** (when >50). Roadmap cards (3 cols): **Short term** / **Mid
term** / **Long term** with **0–3 months** / **3–9 months** / **9–18 months**, `{n} item(s)`, narrative paragraph,
clickable `{id} {name}` list; empty **Nothing in this bucket.**

### 3.8 Assumptions & N/A tab
Heading **Assumptions made in this assessment**; blurb "Read these before trusting the numbers — they describe
what we had to assume or could not verify." Chips `Your {n} rules:` **tagged by you** · **keyword-matched (no
AI)** · **AI-tagged** · **reviewer-edited** · **unmapped** · **with invalid tags** (→ RuleListPanel `{n} rule(s)
{label}`) + violet `{n} threat-profile matches` (subtitle "Your declared industry and threat actors lifted these
within their priority tier — ordering only, never the coverage score."). Assumption list (2 cols, left border);
empty **No assumptions were needed.**
Heading **Not-applicable techniques ({n})**; blurb "These leave the coverage denominator — the headline percentage
makes no claim about them. Grouped by reason; click any technique for its details." Four cards: **Whole matrix
not applicable** ("These ATT&CK areas don't apply to your environment at all.") · **Platform not in your
environment** ("These techniques only work on platforms your inventory doesn't include.") · **Deprecated by
MITRE** ("MITRE no longer maintains these techniques, so they aren't assessed.") · **Excluded by you** ("You asked
us not to assess these — each reason is shown exactly as you gave it."). Each: `{n} techniques` drill link;
reason → technique chips (`({n})` when >1; title `{Domain} — click for details`).
Sample assumptions (prod): "asset entries not mapped to ATT&CK platforms (ignored for platform filtering): IOT
Platform devices (105), Mainframe z/OS billing platform, Microsoft Exchange Server 2019 (hybrid, 4 nodes), …";
"Consolidated Usecase Tracker:2: MITRE ATT&CK update: tag 'T1562' has been restructured and is now represented
under T1685 (Disable or Modify Tools) in ATT&CK v19.1"; "0 rules matched deterministically by ATT&CK technique or
attacker-tool name (no AI involved); 5 sent to AI tagging"; "1 rules were AI-tagged (confidence ≥ 0.4) —
model-generated mappings, spot-check before operational use"; "4 rules remain unmapped to ATT&CK — they do not
count toward coverage"; "detected columns: description→col 3, enabled→col 12, log_source→col 4, logic→col 8,
name→col 2, severity→col 7, tags→col 10"; "7 detection-strength scores were AI-assessed (optional quality pass) —
all others use the deterministic heuristic"; "gap ranking prioritizes techniques associated with your declared
threat profile: Financial Services, Scattered Spider, LockBit affiliates, Asia-Pacific, APT41, Lazarus Group,
Kimsuky, Mustang Panda"; "2 crown-jewel entries didn't match a known platform/category and were not used for gap
prioritization: Telco subscriber billing platform, CyberArk credential vault".

### 3.9 Compare tab
**Compare with** select (**Select an earlier completed run…**, then `{name} — {date} ({pct}%)`); **Comparing…**;
empty "Nothing to compare against yet — run a second assessment later to see your coverage trend."; error
**Comparison failed**. Header `{current} ({date}) vs {baseline} ({date})`. Version mismatch (amber): "These runs
used different ATT&CK versions ({a} vs {b}) — techniques that exist in only one version are left out of this
comparison." Five DeltaChips (`▲ +n` / `▼ n` / `—`): **Coverage %** (pts; "Change in strict coverage percentage
since the older run. Up (green) is better.") · **Weighted %** ("Change in weighted coverage (partial counts as
half).") · **Covered** ("Change in the number of covered techniques.") · **Not covered** ("Change in the number of
uncovered techniques. Down (green) is better.") · **N/A** ("Change in not-applicable techniques (environment or
exclusion changes)."). **Tactics that moved** chips `{name} ▲ {n} pts` (tooltip `{Domain} / {name}: {a}% → {b}%
strict coverage.`); empty **No per-tactic changes.** Three lists: **Newly covered** ("Techniques you can detect now
but couldn't in the older run.") · **Regressed** ("Covered in the older run but not now — e.g. a rule was
disabled or removed.") · **N/A changed** ("Techniques that entered or left the applicable set — usually an
environment or scope-exclusion change, not a detection change."); rows `{id} {name}` + `{From} → {To}`; empty
**None.**

### 3.10 Sheets (all resizable via useSheetResize: min 360, max 95vw, ArrowLeft/Right ±40, shared width)
- DrillDownPanel: title + subtitle; grouped by state with `{Label} ({n})` sub-headings; rows: swatch + `**{id}**
  {name}` + sub-line (na_reason or STATE_PLAIN, `— {why}` for partial). Empty **Nothing to show here.**
- RuleListPanel: title + subtitle; rule cards: name; meta `{MAPPING_STATUS_PLAIN} · Disabled/Enabled/Status
  unknown · {log_source} · {row_ref}`; per mapping: technique chip (button → drawer) + `{SourceLabel}` + ` at {n}%
  confidence` + ` — {rationale}`. Empty **No rules in this group.** Truncation **Showing the first 500 rules only —
  the XLSX export holds everything.**
- TechniqueDrawer: title row `{id}` + StateBadge + strength chip `{Strong|Moderate|Weak} · {n}/100` (STRENGTH_TIP);
  tactics `·` joined; `Detection strength: {rationale}`; tool-credit box **Tool credit — MITRE-evaluated** (`{tools}
  was evaluated against this technique in MITRE ATT&CK Evaluations (evals.mitre.org). Credit alone never changes
  the coverage score — attesting the alert path does.` + button `We monitor {tool}'s alerts — count as covered` /
  **Attesting…**); N/A box **Why this doesn't count toward coverage**; explain blocks **What is this?** (name,
  definition, `Attackers use this to {use}`), **Where is the gap?** / **Where this fits** (`This is a **{tactic}**
  technique — {line}.`, `A log source you already collect — **{via}** — could see this activity.` or `Telemetry:
  {hint}.`, `Applies to: {platforms}`, `In scope because of your inventory: …`), **Why this counts as covered** /
  **Why is it a gap?**, **What would good look like?** (sketch or `No curated detection sketch for this technique —
  {hint}.`; `Starting point: copy your rule '{name}' ({id} {name}).`; `Telemetry ATT&CK expects for this technique:
  {list}` + ` — your '{via}' can provide it.` / ` — none of your onboarded log sources matches it yet.`; per
  component `**{component}:** your query needs {fields}. {where}` + gotcha); **Recommendation** box (sky);
  **Detection rules mapped here ({n})** (empty "None of your uploaded rules map to this technique."; cards with X
  remove aria-label `Remove the {id} mapping from {name}` tooltip "Remove this mapping — the rule's remaining
  mappings are kept and coverage is recomputed."; meta Enabled/Disabled rule + source label + `confidence {n}`
  (title **How sure the mapping is (1.0 = your own tag)**) + log source + rationale); **Showing mappings from the
  first 500 rules only.**; **Map another rule to this technique** (select aria-label **Rule to map to this
  technique**, **Choose a rule…**, button **Add**; footnote "The edit is recorded as "Edited by reviewer" and the
  coverage numbers update immediately."); edit error **Could not save the mapping change** / **Mappings can be
  edited once the assessment has completed**.

---

## 4. `/mitre/connections` — SIEM connections

Header: Plug + **SIEM connections**; **Add connection** (Plus, primary) + **Assessments** (ArrowLeft, outline).
Errors: **Failed to load connections** / **Could not delete the connection** / 403 **SIEM connections are managed
by org admins.**
Add/Edit form (inline card): `<h2>` **Add connection** / `Edit {name}`; blurb `Read-only pull of your detection
rules. The {client secret|auth token} is stored encrypted and never shown again.` (+ ` The service principal needs
the Microsoft Sentinel Reader role.`); platform tablist aria-label **Platform**: **Microsoft Sentinel** |
**Splunk**; fields **Name (optional)**; Sentinel: **Tenant ID (GUID)**, **Client ID (GUID)**, **Subscription ID
(GUID)**, **Resource group**, **Log Analytics workspace**; Splunk: **Host (e.g. acme.splunkcloud.com)**,
**Management port** (8089), **App (optional — all apps if empty)**; **Client secret** / **Auth token** with suffix
**(stored encrypted)** on create / **(blank = keep saved)** on edit; **Auto-pull schedule** select **Off — manual
pulls only** / **Daily** / **Weekly**; **Hour (UTC)** select (`00:00 UTC` … `23:00 UTC`, only with a cadence);
**Day of week** (Mon…Sun, weekly only). Form errors: **The client secret is required — it is stored encrypted and
never shown again.** / **The auth token is required — it is stored encrypted and never shown again.** / **Could
not save the connection**. Buttons **Save connection** / **Save changes** (**Saving…**) + **Cancel**.
Empty: "No saved connections yet. Add one to pull detection rules straight from Microsoft Sentinel or Splunk — on
a schedule if you like. Saved secrets are encrypted at rest and never shown again."
Table: **Connection** (name + `Splunk · {host}` / `Sentinel · {workspace}`) · **Schedule** (**Off** / `Daily ·
HH:00 UTC` / `Weekly · Mon HH:00 UTC`) · **Last pull** (date + last_status, or **never**) · **Health** (pill
**Healthy** emerald / `{n} failed in a row` rose) · **Coverage trend** (latest `{pct}%` link + delta + sparkline, or
`—`) · **Last error** (or `—`; also the per-row action message) · actions **Test** (**Testing…**; `OK — {n} rules
reachable` / **Test failed**) · **Pull now** (**Pulling…**; **Pull failed**) · Pencil aria-label `Edit {name}` ·
Trash2 aria-label `Delete {name}` with confirm `Delete "{name}"? Scheduled pulls stop; past assessments are kept.`
Loading: none today (design a skeleton).
Sample: "abc ltd Sentinel" (Sentinel · acme-sec-ops, Weekly · Mon 02:00 UTC, last pull Sep 8, 2026 · completed,
Healthy, 14.4% ▲14.1); "Cisco CDC Splunk" (Splunk · splunk.cisco-cdc.internal, Off, never, `2 failed in a row`,
last error "Connection refused: management port 8089 unreachable").

## 5. Cross-cutting
No loading skeletons anywhere in the module today; native confirms for attestation and connection delete (design
proper destructive dialogs); every state badge has a tooltip; sheets stack (technique drawer over drill-down).
