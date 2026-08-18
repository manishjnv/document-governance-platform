# Session handoff — VFQ engagement + report-export productization (2026-08-13/14)

**Headline:** First real-customer MITRE engagement (Vodafone Qatar / "VFQ",
via Wipro MDR) ran end-to-end on ScopeWise: their SOC's 371 Sentinel rules +
environment workbook validated, assessed (28.7% coverage, 193/673), the
deliverables reviewed/corrected, and every hand-fix then productized — a new
PPTX briefing-deck export, the XLSX restyle, a Reference-KQL column, and
three accuracy fixes in the ranking engine. Baseline moved 886→890/7 during
this session (later sessions took it to 935/7). All deployed to prod.

**Written retroactively 2026-08-19** at user request ("document all for
future reference") — this session predates the 08-18 Splunk/tool-coverage
handoff but was never written up.

---

## 1. The VFQ engagement (customer-specific work)

All customer files live in `docs/sample/project/` which is **gitignored on
purpose** (line 70 of `.gitignore`) — the repo is public and these files
contain real VFQ rule names, staff names and infrastructure counts. They
exist ONLY on this machine (E: drive). Anything needed by the product was
generalized into code; the folder itself is reference material.

| File | What it is |
| --- | --- |
| `profile.xlsx` | Raw team export: 371-rule tracker, log-source inventory, their own heatmap, per-vendor device counts |
| `scopewise-mitre-use-cases (4).xlsx` | ScopeWise-template rule dump (validated: all headers auto-detect) — **modified**: `Last Triggered = never` written into 284 rows whose validation found no events (matched row-by-row against profile.xlsx; `.bak` beside it) |
| `scopewise-mitre-environment (4).xlsx` | ScopeWise-template environment workbook (validated: all 4 sheets auto-detect) |
| `mitre-context-{rules,environment,heatmap}.md` | Governance/validation metadata that doesn't fit the templates — **modified**: 19 unclassified vendor rows marked `Non-CJ*` (assumed Non-CJ, decision 2026-08-13; revisit if VFQ classifies) |
| `VFQ - MITRE Assessment-attack-coverage.xlsx` | The full report from the live run — **hand-patched** (see §2) |
| `VFQ - MITRE Assessment - Action Workbook.xlsx` | Customer-share cut: 3 tabs (Summary / Technique Tracker / Use-Case Mappings), purple theme, KQL column, zero tool branding |
| `VFQ_MITRE_Assessment_Report.pptx` | 18-slide client deck hand-built on the WME template's design system (python-pptx script in session scratchpad, since productized) |
| `WME_SOC_Assessment_Report_v2.pptx` | The Wipro deck whose design system (Tenorite font, purple `341954` / teal `00A98B` / magenta `B71D6B`, card-with-accent-bar, keyword highlighting) was extracted — design reference only, no content copied |

**Run prep decisions (durable):**

- `quality_ai_enabled = true` written directly into prod `mitre_settings`
  for org `002c42da-…` (manishjnvk@gmail.com's org) — the AI strength
  re-rating now runs for every assessment in that org.
- Wizard inputs used: customer "VFQ", industry Telecommunications, region
  MEA, actors APT33/APT34 (threat weighting confirmed firing in the run).
- Mobile + ICS matrices correctly N/A (no MDM fleet / no OT assets
  declared) — this **raises** nothing and hides nothing: N/A leaves the
  denominator. Open questions for VFQ: Intune fleet? facility OT? macOS
  (they have a macOS keychain rule but no Macs declared — 18 techniques
  N/A'd)? SaaS beyond O365 (6 techniques N/A'd)?
- ATT&CK reconciliation (customer-audit ready): site shows Enterprise
  222 + 475 = 697 active; report = 673 applicable + 18 macOS-N/A +
  6 SaaS-N/A = 697 — exact. 37 deprecated in the N/A appendix; revoked IDs
  auto-remapped (19× T1562-family → T1685/T1686).

## 2. Report review — what was wrong and how it was fixed

Three defects found reviewing the generated XLSX, first hand-patched into
the VFQ file, then **fixed at the source** (commits `640a09c`, `2e2b08a`):

1. **Wrong via/recommendation** — T1685.005 "Clear Windows Event Logs"
   recommended building on `EmailAttachmentInfo`. Two stacked causes in
   `ranking.py`: `_feasibility` took telemetry categories in raw ATT&CK
   component order (a lone application-log component outranked two endpoint
   components), and `_LOG_SOURCE_RULES` knew only product names — Sentinel-
   native table names (`SecurityEvent`, `DeviceProcessEvents`, `Syslog`,
   `Device*`) provided **nothing**, so an email table was the only
   "application" provider. Fixed: dominant-category-first ordering + native
   table vocab.
2. **Crown-jewel matching starved** — 28 of VFQ's 30 crown-jewel entries
   missed the curated phrase rules ("IP Network: Fortinet (36 devices)"-
   style inventory phrasing). Fixed: `crown_jewel_hints` falls back to the
   same platform normalizer the Assets sheet uses (`ingest._match_platform`).
   Note: with broad crown jewels the flag saturates (399/480 gaps for VFQ) —
   it's context, not a filter.
3. **Roadmap over-promise** — "413 gaps buildable now" with 284/371 rules
   never having fired. Fixed: XLSX Summary appends a source-health caveat
   with the real never-count whenever rules carry `Last Triggered: never`
   (`_load_use_case_dicts` now passes `last_triggered` through).

Tests: 3 regression goldens added; baseline 886→889/7.

## 3. Productization (commits `8d9505f`, `d4fccc0` + later polish)

- **PPTX briefing-deck export** — `app/mitre/report_pptx.py`
  (`build_pptx_export`), `GET /assessments/{id}/export.pptx`, PPT button on
  the results page. Started at 9 slides; expanded same-day to the full
  18-slide structure of the hand-built deck after user review ("less data,
  no clarity"): cover · agenda + how-to-read cards · 4 dividers · scope &
  inputs · methodology · headline tiles · tactic bar chart · quality
  doughnut · log-source table · **derived** What's-Working / Key-Gaps
  evidence cards (each gap card carries a "What to do" line) · top-5 fixes
  · roadmap with outcomes + never-caveat · next steps with Effort·Impact
  tags · closing. Analyst-judgment slides became data-derived equivalents —
  deterministic, data-gated (skip when their data is absent). New dep:
  `python-pptx==1.0.2`. Later sessions capped it at 20 slides and added the
  typography/mosaic passes (see the 08-18 handoff).
- **XLSX restyle** — `report_xlsx.py` adopted the same palette (purple
  headers, teal section bands, zebra rows, lavender grid) and the Technique
  Tracker sorts **gaps first in ranked order** (work-queue reading).
- **Reference KQL column** — per-Sentinel-table illustrative skeletons in
  the Tracker for buildable gaps, each opening with the discipline header
  (confirm table has data / audit-mode first / allowlists before alerting —
  the anti-false-positive + anti-never-fires teaching). Prose/multi-word
  sources honestly get no query. "Log fields needed" now leads with the
  component matching the gap's chosen telemetry category.
- **Docs refreshed** — `MITRE_MODULE_REFERENCE.md` prod-state header
  corrected (was claiming A1–A8 pending), lens-arc + PPTX + restyle
  documented (commits `a211571`, `aa97194`, `0419486`).

## 4. Commit ledger (this session, all pushed + deployed)

| Commit | What |
| --- | --- |
| `a211571` | Docs: reference refresh — prod through A12 + lens features |
| `640a09c` | Ranking: dominant-category feasibility, Sentinel table vocab, CJ platform fallback |
| `2e2b08a` | XLSX: never-fired source-health caveat |
| `aa97194` | Docs: baseline 889/7 |
| `8d9505f` | PPTX export + XLSX restyle + Reference KQL + fields alignment |
| `0419486` | Docs: PPTX/restyle in reference, baseline 890/7 |
| `d4fccc0` | PPTX deck: full 18-slide structure + tracker gaps-first sort |

Deploys verified on the VPS each time (`GIT_SHA` in container + smoke).

## 5. Gotchas learned (worth knowing before touching this again)

- **Stored assessments freeze their vias/CJ flags/narrative** — ranking
  fixes only reach a NEW run (or Phase-10 recompute); export-time changes
  (XLSX/PPTX builders, caveat) apply to old assessments immediately.
- **python-pptx template surgery**: removing slides needs
  `prs.part.drop_rel(rId)` as well as `_sldIdLst.remove` — otherwise the
  saved zip carries duplicate part names and Excel/PowerPoint may prompt
  repair.
- **PowerPoint COM for visual QA works well** (export slides to PNG,
  eyeball with Read) — but the user's own open PowerPoint window locks the
  file; check `presentation.Saved` via COM before closing it
  (PS 5.1 `powershell.exe` needed — pwsh lacks `GetActiveObject`).
- **Bash heredocs eat one backslash layer** on this Windows setup — for
  Python patches matching literal `\uXXXX` sequences in source, build
  anchors with `chr(92)`.
- The WME template's docProps carried `author: steve` — deck builders must
  always set core properties explicitly.

## 6. Next actions (as of 2026-08-14; see 08-18 handoff for what actually happened next)

1. VFQ to answer the scope questions (Intune/OT/macOS/SaaS) and classify
   Telco + Access Ops assets.
2. Validation sprint for the 284 silent rules — biggest trust win, no new
   engineering.
3. Re-run the assessment after the ranking fixes for corrected vias in all
   exports (fresh run also re-generates the AI narrative).
4. Quarterly re-runs trend against the 28.7% baseline (customer field set).

---

Tests pass: Y (890/7 at session end; suite is 935/7 as of 2026-08-19).
Open questions: VFQ scope answers (§6.1); crown-jewel flag saturation UX.

**Agent utilization**
- Opus: everything — review, fixes, deck/workbook builds, feature code (files hot in context throughout; no delegation-sized mechanical work emerged)
- Sonnet: n/a — no delegation
- Haiku: n/a — no delegation
- codex:rescue: n/a — no security/auth-adjacent diffs (report/ranking logic only)
