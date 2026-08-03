# MITRE Accuracy & Template Improvement Plan — sequenced kickoff prompts

**Written:** 2026-08-03. Source: consultant-style review of
`Claude_MITRE_Assessment_Review_Prompt.md` + module audit (this session).
Run phases **in order, one per session**, each with the prompt block below
pasted into a fresh session. Check off phases here as they complete.

## Ground rules (every phase — copy into every session)

1. Read `CLAUDE.md`, `docs/planning/MITRE_MODULE_REFERENCE.md`, and this
   plan's phase block BEFORE touching code. SIEM phases also read
   `docs/planning/MITRE_SIEM_INTEGRATION_PLAN.md`.
2. Backend baseline **809 passed / 7 skipped** (`cd apps/api && python -m
   pytest`); frontend `cd apps/web && npx tsc --noEmit` clean. Never run
   pytest while another session might be (shared `edgp_test` deadlocks —
   check `pg_stat_activity` first). Update the CLAUDE.md baseline line
   when new tests land.
3. **Invariants that never break:** all numbers deterministic (LLM only
   tags + narrates, never introduces a number); raw logs are never
   ingested and field-level verification is never claimed (honesty
   boundary — wording is "your query needs X", never "your source is
   missing X"); module isolation (no `ReviewOrchestrator` registration,
   no shared-file churn beyond the documented touchpoints); existing
   template headers/sheet names NEVER change — additions only.
4. Migrations (if any): no runner exists — apply to `edgp_dev`,
   `edgp_test`, prod `scopewise_prod` on deploy, AND check
   `test_insights_extra.py`'s hand-rolled schema + any ORM
   `CheckConstraint` mirroring the change (CLAUDE.md 5-point checklist).
5. One commit per logical unit. Do NOT deploy unless the user says so.
   End of phase: update `MITRE_MODULE_REFERENCE.md` §15 history +
   `docs/IMPLEMENTATION_PROGRESS.md`, tick the phase here, write a short
   handoff in `docs/phases/summaries/` if the session ends.

## Sequence & status

| Phase | Item | Status |
| --- | --- | --- |
| A1 | Fix the consultant review prompt doc | ☑ |
| A2 | Sigma-based tagging accuracy benchmark | ☑ |
| A3 | Rule-vs-inventory telemetry cross-check (shelfware detector) | ☑ |
| A4 | Crown Jewels → gap-ranking lift (or drop) | ☑ |
| A5 | Keyword alias expansion (vendor/appliance vocab) | ☑ |
| A6 | Customer template upgrade + optional health columns | ☑ |
| A7 | Sentinel data-connector auto-import | ☑ |
| A8 | Threat-profile expansion + region weighting | ☑ |
| A9 | Report consolidation: XLSX Technique Tracker + PDF roadmap dedup | ☑ |
| A10 | Device-level truth: platform synonyms, per-stream guidance, coverage-by-log-source, unmonitored-capability check | ☑ |
| A11 | Report/template visual polish: XLSX header fills, template borders, executive PDF flow | ☑ |
| A12 | Scope auto-trend to the same customer (params JSONB, no migration) | ☐ |

Deliberately dropped: "covered"→"has detection" relabel (pure
positioning — needs a user decision, not a build session; raise it when
A6 ships). CMDB header synonyms folded into A6.

---

## Phase A1 — Fix the consultant review prompt doc (tiny, docs-only)

```text
Read CLAUDE.md, docs/planning/MITRE_MODULE_REFERENCE.md §§1,3,5, and the
"Ground rules" section of docs/planning/MITRE_ACCURACY_IMPROVEMENT_PLAN.md.

Task: rewrite docs/planning/Claude_MITRE_Assessment_Review_Prompt.md so a
fresh consultant session can actually run it. Keep its role/persona and
review-criteria framing. Changes:
1. Embed the CURRENT field inventory verbatim (build it from
   MITRE_MODULE_REFERENCE.md §5 + apps/api/app/mitre/ingest.py + the two
   templates in apps/web/public/templates/): a table of field → sheet/
   intake location → required/optional → which engine consumes it.
   Include the Sentinel pull as a collection path.
2. Add a "Hard invariants — do not recommend violating these" section:
   deterministic numbers; raw logs never ingested / no field-level
   verification claims; LLM tags+narrates only; don't redesign.
3. Remove "Sample logs" from the customer-provides list. Demote
   architecture/network diagrams to "optional narrative context only".
4. Cut "Parser coverage" and "Normalization coverage" from the assessed
   layers OR mark them "assessable only once optional parser/normalized
   columns ship (plan phase A6)". Note ATT&CK v19.1 has no mainframe
   platform — z/OS support means custom off-framework mappings; say so.
5. Replace "Final scoring" with a defined rubric: per-field verdict table
   (keep / make-optional / remove / add) + one 0-10 data-sufficiency
   score with the scale stated.
Acceptance: doc reads standalone (no repo access needed to review the
form); no code touched. Report: unified diff + <200-word changelog.
```

## Phase A2 — Sigma-based tagging accuracy benchmark (highest accuracy value)

```text
Read CLAUDE.md, docs/planning/MITRE_MODULE_REFERENCE.md §§7-8,
docs/planning/PROMPT_ENGINEERING_GUIDE.md (MITRE section), and the Ground
rules of docs/planning/MITRE_ACCURACY_IMPROVEMENT_PLAN.md.

Task: build an OFFLINE accuracy benchmark for the tagging ladder using
public Sigma rules (github.com/SigmaHQ/sigma — rules carry ATT&CK tags in
their `tags:` field, license: DRL, attribution in the script header).
Contract:
1. scripts/benchmark_tagging.py (dev-run-only, like
   scripts/build_attack_data.py — NEVER imported by the app): downloads or
   reads a local clone of the Sigma repo, samples N rules (default 300,
   seedable) that have attack.tXXXX tags, converts each to the module's
   use-case row shape (title→name, description→description,
   detection→logic as YAML text, logsource→log_source), strips the tags
   as ground truth.
2. Runs the REAL keyword pre-pass (keyword_tag.py) and optionally the
   real MitreTaggingAgent (flag --with-ai, uses the configured OpenRouter
   key; default off so the script is free/deterministic) over the rows.
3. Reports per-layer and combined precision / recall / F1 at
   technique-id level (sub-technique exact and parent-level-credit
   variants), plus a confusion sample (top 20 misses/false tags), plus
   per-confidence-bucket accuracy so the 0.7/0.4 thresholds can be judged
   empirically. Output: printed table + JSON dump to a path given by
   --out.
4. A small pinned fixture (20-30 Sigma-derived rows, checked in under
   apps/api/tests/fixtures/) + a pytest that runs the KEYWORD layer only
   against it and asserts precision ≥ a measured floor — a regression pin,
   not a benchmark (no network, no LLM in tests).
Do NOT change any threshold or prompt in this phase — measure only.
Acceptance: script runs clean on a fresh clone; new test green; suite
809+1/7. Report: diff + the measured metrics table + <200-word changelog.
```

## Phase A3 — Rule-vs-inventory telemetry cross-check (shelfware detector)

```text
Read CLAUDE.md, docs/planning/MITRE_MODULE_REFERENCE.md §§3,6 (quality +
ranking), apps/api/app/mitre/quality.py and ranking.py, and the Ground
rules of docs/planning/MITRE_ACCURACY_IMPROVEMENT_PLAN.md.

Task: surface a deterministic warning when a technique is
covered/partial ONLY by rules whose declared log_source maps (via the
existing ranking category bridge) to a telemetry category that does NOT
appear in the customer's Log Sources/Tooling sheets. Today this signal
exists inside quality.py's telemetry-match scoring but never surfaces as
an assumption. Contract:
1. Pure function (coverage or quality layer — pick the seam that avoids
   duplicating the bridge) returning affected technique ids + the rule
   names + the missing category, ONLY when an environment workbook with a
   Log Sources sheet was provided (no workbook → no claim).
2. Each affected technique adds ONE assumption line, wording within the
   honesty boundary: "T1059.001 is covered by rule 'X', but its log
   source 'Y' doesn't match anything in your Log Sources sheet — verify
   that telemetry is actually flowing." NEVER changes state, coverage %,
   ranking, or strength values.
3. Surface: assumptions list (summary JSONB — existing pipeline slot),
   which already flows to the UI tab, PDF appendix, and XLSX Assumptions
   sheet with zero renderer changes. Verify all three render it.
4. Tests: golden for flagged/not-flagged (source present, source absent,
   no workbook, tooling-sheet match counts as present), plus one E2E
   assertion in test_mitre_api.py that the assumption appears.
Acceptance: suite green (809+new)/7, tsc clean, no summary-shape changes
beyond additional assumption strings. Report: diff + changelog <200 words.
```

## Phase A4 — Crown Jewels: wire into gap ranking (kill the dead field)

```text
Read CLAUDE.md, docs/planning/MITRE_MODULE_REFERENCE.md §6 (ranking,
Phase 11 threat weighting), apps/api/app/mitre/ranking.py + ingest.py
(crown_jewels parsing), and the Ground rules of
docs/planning/MITRE_ACCURACY_IMPROVEMENT_PLAN.md.

Context: the Crown Jewels sheet is parsed and echoed but consumed by no
engine (verified 2026-08-03). Task: make it matter, using the EXACT
Phase 11 pattern (annotation + within-tier ordering lift, never a tier
jump, never a state/% change). Contract:
1. Deterministic keyword bridge from crown-jewel entry text to ATT&CK
   platform/category hints (reuse/extend the ranking keyword maps — e.g.
   "database"→application/cloud, "payment"→application, "AD"/"domain
   controller"→identity, "vcenter"/"esxi"→ESXi). Unmatched entries → one
   assumption line, never an error.
2. Gaps whose technique's platforms/data-category intersect the derived
   hints get `crown_jewel_relevant: true` (summary gap dict) and sort
   above equal-tier, equal-threat-relevance peers — a THIRD sort key
   after tier and threat_relevance. Toggleable org tunable
   `crown_jewel_weighting_enabled` default true (mitre_settings pattern,
   no migration).
3. UI: small chip on gap rows (mirror the Phase 11 "Threat match" chip);
   PDF/XLSX gap register gains the flag column/badge where the threat
   chip already renders. Drawer "why" text unchanged.
4. Tests: bridge goldens, ordering golden (lift within tier only),
   toggle-off keeps annotation, no-sheet no-op; template still parses.
Acceptance: suite green, tsc clean, coverage %s byte-identical on the
sample kit. Report: diff + changelog <200 words.
```

## Phase A5 — Keyword alias expansion (deterministic tagging vocab)

```text
Read CLAUDE.md, docs/planning/MITRE_MODULE_REFERENCE.md §7,
apps/api/app/mitre/keyword_tag.py + data/keyword_aliases.json (39
entries, cited sources), and the Ground rules of
docs/planning/MITRE_ACCURACY_IMPROVEMENT_PLAN.md. Requires phase A2's
benchmark script (use it to validate additions).

Task: grow keyword_aliases.json with high-precision vendor/appliance/
tool vocabulary. Candidate families (research + cite a source per entry,
same in-file citation style): LOLBAS binaries not yet covered
(certutil, regsvr32, mshta, rundll32, bitsadmin, wmic...), credential
tools (lazagne, secretsdump, rubeus, kerbrute), C2/frameworks
(cobalt strike beacon, sliver, brute ratel), persistence artifacts
(schtasks /create, sc create, registry run key paths), cloud CLI abuse
markers, DNS/appliance markers (dnscat, iodine), backup-destruction
markers (vssadmin delete shadows, wbadmin delete). Rules:
1. Precision over recall — an alias that could fire on benign SOC prose
   ("look at exe files" class) is rejected; keep the
   punctuation-significant matching semantics; ambiguous terms out.
2. Run the A2 benchmark keyword-only before/after; additions must not
   lower precision. Include both metric tables in the report.
3. Pin every new alias family with an FP-regression test case (existing
   pattern in test_mitre_agents.py keyword pins).
4. Cap this pass at ~40 new entries — curation quality over bulk.
Acceptance: suite green, benchmark precision non-decreasing, recall up.
Report: diff + before/after metrics + changelog <200 words.
```

## Phase A6 — Customer template upgrade + optional health columns

```text
Read CLAUDE.md, docs/planning/MITRE_MODULE_REFERENCE.md §5,
apps/api/app/mitre/ingest.py (header/sheet synonym lists + sheet
selection logic), the two templates in apps/web/public/templates/, and
the Ground rules of docs/planning/MITRE_ACCURACY_IMPROVEMENT_PLAN.md.
This phase touches the customer-facing contract — be conservative.

HARD CONSTRAINT: existing headers, sheet names, and column order stay
byte-identical. Additions only. Old templates and every dump that parses
today MUST still parse identically (add a regression test asserting the
detected column map for the OLD template layout is unchanged).

Task, three parts:
1. Use-case template (scopewise-mitre-use-cases.xlsx):
   a. Append optional columns AFTER Status: "Severity" and
      "Last Triggered" (date or "never"). Ingest: new field synonyms
      (severity/priority/criticality; last triggered/last fired/last
      alert) parsed leniently, stored per-row. Storage: mitre_use_cases
      needs the columns — migration 036 (two nullable columns) with the
      FULL 5-point CLAUDE.md migration checklist (dev/test/prod DBs +
      test_insights_extra.py grep + ORM CheckConstraint grep).
   b. Consume: quality.py — "last triggered: never/blank on an
      old-looking dump" and severity feed small strength adjustments
      (define exact deltas in-code as module constants; a rule that has
      never fired can't reach "strong"). No coverage-state change.
   c. 2-3 more example rows in the template showing: a disabled rule, an
      untagged rule (AI will map it), a multi-technique tag cell.
   d. VERIFY ingest's sheet-selection for the dump BEFORE adding any
      extra sheet to this workbook; if it takes the first/only sheet, an
      Instructions sheet is unsafe here unless selection is made
      name-aware — if so, put instructions in a text box on the Rules
      sheet or skip. Do not guess: read the code.
2. Environment template (scopewise-mitre-environment.xlsx): unknown
   sheets are tolerated, so:
   a. Add a "Read Me" FIRST sheet: what each sheet is for, what's
      optional, one line on how the data is used (assumption-honest).
      Verify the sheet-name synonym matcher can't mistake "Read Me" for
      a data sheet.
   b. Log Sources sheet: append optional columns "Parser / Format",
      "Normalized (Y/N)", "Last Event Seen". Ingest parses them into the
      environment dict when present (synonyms: parser/format/ingest
      format; normalized/cim/ecs; last event/last seen/last ingest).
      Consume: ranking feasibility — a needed-category source with
      Normalized=N or stale Last Event Seen downgrades short→mid with
      the reason in the gap hint; absent columns change nothing.
      This is what makes "parser/normalization coverage" assessable
      (prompt-doc promise from phase A1).
   c. Assets sheet: widen header synonyms for common CMDB exports
      (ServiceNow: "os", "operating system", "ci type", "class";
      Lansweeper: "ostype"). Synonym additions only.
3. Docs: MITRE_MODULE_REFERENCE.md §5 + §15, IMPLEMENTATION_PROGRESS.
Tests: old-layout regression, new-column parse goldens, feasibility
downgrade golden, migration applied to edgp_test before running.
Acceptance: suite green, tsc clean, both templates open in Excel and
round-trip through real ingest in a test. Report: diff + changelog.
```

## Phase A7 — Sentinel data-connector auto-import (kill the manual Log Sources sheet)

```text
Read CLAUDE.md, docs/planning/MITRE_MODULE_REFERENCE.md §§3,9 (from-siem
paths), docs/planning/MITRE_SIEM_INTEGRATION_PLAN.md IN FULL (egress
guard contract is non-negotiable), apps/api/app/mitre/connectors/*, and
the Ground rules of docs/planning/MITRE_ACCURACY_IMPROVEMENT_PLAN.md.
SECURITY-ADJACENT: adversarial sign-off (Sonnet takeover per the
codex:rescue outage memory) required BEFORE any push.

Task: when an assessment is created via from-siem / from-connection
(Sentinel), also pull the workspace's onboarded tables/data-connector
inventory and auto-populate the environment Log Sources (and derivable
Assets platforms) so Sentinel customers skip the manual workbook.
Contract:
1. Extend the Sentinel connector with ONE additional read: the
   workspace's tables (Log Analytics tables API or dataConnectors ARM
   list — pick the one already reachable through the pinned-host egress
   guard with the existing token scopes; document the choice and REQUIRED
   permissions in MITRE_SIEM_INTEGRATION_PLAN.md). Same host allowlist,
   same caps, same error taxonomy — NO new egress capabilities.
2. Map table names → the module's log-source/platform vocabulary via a
   deterministic in-code table (SecurityEvent→Windows Event Logs/Windows,
   Syslog→Linux, SigninLogs→Identity Provider/Entra ID, AWSCloudTrail→
   IaaS, CommonSecurityLog→Firewalls, DeviceProcessEvents→EDR...).
   Unmapped tables listed in an assumption, never dropped silently.
3. Auto-derived environment merges UNDER any customer-supplied workbook
   (explicit beats derived; provenance noted in params.siem +
   assumptions: "log sources auto-imported from Sentinel (N tables)").
   inventory_provided semantics: auto-import counts as provided for Log
   Sources but NOT for Assets unless platforms were derivable — keep the
   lower-bound assumption honest.
4. Failure isolation: inventory-pull failure NEVER fails the assessment —
   degrade to no-environment behavior + assumption, mirroring narrative
   degrade discipline.
5. Tests in test_mitre_siem.py style: mapping goldens, merge-precedence,
   degrade path, secret-absence, no-network guarantee.
Acceptance: suite green; sign-off verdict logged in the session handoff.
Report: diff + changelog + the sign-off outcome.
```

## Phase A8 — Threat-profile expansion + region weighting

```text
Read CLAUDE.md, docs/planning/MITRE_MODULE_REFERENCE.md §6 (Phase 11
threat weighting), apps/api/app/mitre/data/threat_profiles.json +
test_mitre_threat_profile.py, and the Ground rules of
docs/planning/MITRE_ACCURACY_IMPROVEMENT_PLAN.md.

Task, same curation discipline as Phase 11 (every technique id must
resolve `ok`, every entry cites a public source in-file):
1. Industries: extend from 10 toward ~18-20 (candidates: education,
   telecom, media, legal, hospitality, transport/logistics, pharma
   distinct from healthcare, agriculture, mining — only where a citable
   sector threat report exists; no source → no entry).
2. Actors: extend from 10 toward ~20 G-coded groups, prioritizing groups
   relevant to the new industries.
3. Region weighting: intake already collects region (200-char free
   text). Add a curated region_profiles map (coarse: NA/EU/APAC/MEA/
   LATAM + a few country aliases) → actor lists, from citable regional
   targeting reports (ENISA, CISA advisories, M-Trends regional data).
   Region matches add threat_relevance labels through the SAME
   within-tier lift — third input to build_threat_profile, no new sort
   key, no % change. Unknown region text = no-op (exact current
   unknown-industry semantics). Wizard: keep free text; optionally add a
   datalist of the profiled regions.
4. Tests: extend test_mitre_threat_profile.py patterns — id validity,
   alias integrity, region lookup golden, unknown no-op, lift-within-
   tier golden. Update the plan/reference docs' profile counts.
Acceptance: suite green, all ids resolve ok (test-enforced), sources
cited for 100% of new entries. Report: diff + entry-count table +
changelog <200 words.
```

## Phase A9 — Report consolidation: XLSX Technique Tracker + PDF roadmap dedup

Added 2026-08-03 after UI testing on the Acme sample (841 gaps). User
decision: merge the three overlapping XLSX sheets into one working
tracker; PDF keeps 100% of its content but stops repeating it (the
Phase 14i print-once-reference-elsewhere pattern).

```text
Read CLAUDE.md, docs/planning/MITRE_MODULE_REFERENCE.md §11 (reports)
+ §13, apps/api/app/mitre/report_xlsx.py, report.py, report_common.py,
templates/ (base/executive/detail), and the Ground rules of
docs/planning/MITRE_ACCURACY_IMPROVEMENT_PLAN.md. Report layer ONLY:
no coverage/ranking/pipeline change, no migration, no new settings.
Backend baseline 859 passed / 7 skipped (858 + the A7-hardening
regression test, commit 64b99e4); tsc clean.

PART 1 — XLSX: replace the "Technique Register", "Gaps &
Recommendations", and "Roadmap" sheets with ONE "Technique Tracker"
sheet (Roadmap is the same gap dicts re-bucketed; Gaps is a subset of
the Register — pure duplication today). One row per applicable
technique (covered rows keep gap-only columns blank), NO interleaved
section-header rows (they break sort/filter), auto-filter across the
whole sheet, frozen header. Columns in order:
  Technique ID | Name | Tactic(s) | Domain | State (plain words) |
  Why (derive_why) | Strength | Priority (numeric with "P"0 format —
  14h pattern) | Threat match | Crown jewel | Feasibility | Roadmap
  bucket (Short/Mid/Long as a VALUE) | Recommendation (narrative
  override else hint) | Log fields needed (telemetry_lines) | Via |
  Owner | Status | Target date | Notes
The last four are BLANK customer-tracking columns (that is the point
of the merge — a working tracker). Keep: _guard on every attacker-
influenced cell, ColorScaleRule on Priority, state fills, wrapped
text. N/A, Assumptions, Summary, Coverage by Tactic, Use-Case
Mappings, Read Me, How We Read Your Files sheets are UNCHANGED except
the Read Me guide text, which must describe the new sheet. Update the
scope pruning map in the export endpoint: scopes that previously kept
Register/Gaps/Roadmap now keep the Tracker (check router.py +
report_xlsx.py for how scope prunes sheets; gaps and coverage scopes
both keep Tracker).

PART 2 — PDF: keep ALL content, remove only repetition. The roadmap
section currently re-renders full gap entries the register already
printed. Keep the roadmap prose (short/mid/long narrative), bucket
counts, and effort-to-impact projection; replace the re-listed gap
entries with a compact per-bucket INDEX TABLE: Technique ID, Name,
Priority, and a "details p. N" cross-reference into that gap's
register entry — use the existing target-counter page-ref pattern
from Phase 14e (executive.html "details p. N"); register entries
need stable anchor ids if they lack them. The gap register itself is
untouched (single home of per-gap detail). Executive scope output
unchanged; the gaps tab scope keeps register + roadmap index. On the
841-gap Acme-class sample this should cut a large share of pages —
report the before/after page count from a real render.

Tests (test_mitre_report.py): rewrite the XLSX structure goldens for
the Tracker (headers exact, one covered row with blank gap columns +
blank tracking columns, one gap row fully populated, sheet count,
formula-guard readback on the new columns, scope pruning); PDF golden
for the roadmap index table (IDs present, no duplicated recommendation
text in the roadmap section, cross-ref markup present). Run the FULL
backend suite alone on edgp_test (check pg_stat_activity first) +
npx tsc --noEmit; expect 859+/7 — update the CLAUDE.md baseline line.

Docs: MITRE_MODULE_REFERENCE.md §11 (both report descriptions) + §13
test table + §15 history row; IMPLEMENTATION_PROGRESS.md; tick A9 in
this plan's status table. Commit per logical unit (xlsx / pdf / docs).

DEPLOY (authorized): push to master, standard VPS loop (docker compose
-f docker-compose.vps.yml build + GIT_SHA up -d; no migration), then
smoke on https://scopewise.assessiq.in: download full XLSX for the
"Acme MITRE Assessment" — Tracker sheet present with tracking columns,
the three old sheets gone, Read Me updated; download full PDF —
roadmap section shows prose + index tables with page numbers, register
intact; scoped exports (gaps XLSX + gaps PDF + executive PDF) all
still 200. Touch ONLY scopewise-* containers.

Report: per-part diff summary, before/after PDF page count, XLSX sheet
list before/after, suite + tsc results, deploy SHA + smoke table.
```

## Phase A10 — Device-level truth (4 small pieces, one theme)

Added 2026-08-03 after Acme UI testing surfaced the "Infoblox problem":
a DNS appliance whose rows land in the unmapped-assets assumption, and —
worse — a device whose primary telemetry (DNS logs) can be entirely
unmonitored while nothing in the product says so from the device's side.
**Overriding style rule for every piece: the customer-facing output must
be plain English a non-SOC manager understands on first read.** No
category jargon ("network telemetry category"), no ATT&CK-speak without
a gloss; every new UI element gets a plain-words tooltip; wording
examples below are the bar, match them.

```text
Read CLAUDE.md, docs/planning/MITRE_MODULE_REFERENCE.md §§5,6,12,
apps/api/app/mitre/ingest.py (_PLATFORM_RULES, _sheet_entries,
parse_environment_file), ranking.py (the log-source category bridge),
and the Ground rules of docs/planning/MITRE_ACCURACY_IMPROVEMENT_PLAN.md.
Backend baseline 863 passed / 7 skipped; tsc clean. No migration
expected (new curated JSON + parse-time fields in params + UI). All
numbers stay deterministic; the honesty boundary holds throughout: we
only compare what the customer DECLARED in their sheets — never claim
to have verified that any log is actually flowing.

PIECE 1 — Platform synonym additions (ingest.py _PLATFORM_RULES):
  photon os -> Linux, photon -> Linux (Photon OS is a Linux distro),
  infoblox -> Network Devices, dns appliance -> Network Devices,
  dns appliances -> Network Devices, rubrik -> Linux.
  Deliberately NO bare "dns" rule ("DNS servers" may be Windows/Linux
  boxes — precision over recall). One platform per row stays (no
  multi-platform mechanism). Tests in test_mitre_ingest.py: the three
  vendors resolve from full phrases ("Photon OS appliances" -> Linux,
  "Infoblox DNS appliances" -> Network Devices, "Rubrik backup
  appliances" -> Linux); "cisco ios" still -> Network Devices (ordering
  regression); AND a stay-unmapped pin: "IOT Platform devices" and
  "Mainframe z/OS billing platform" must REMAIN unmapped with the
  assumption line — ATT&CK v19.1 has no IoT/mainframe platform and
  mapping them would be dishonest. Comment the pin so a future session
  doesn't "fix" it.

PIECE 2 — "One row per log stream" guidance (no header changes):
  Environment template's Read Me sheet + the wizard's environment
  drop-zone helper text gain one plain line, e.g.: "If one device sends
  more than one kind of log, list each log type as its own row —
  'Infoblox - DNS logs' and 'Infoblox - SSH logs' — so each stream gets
  credited separately." Existing sheet names/headers byte-identical
  (Ground rule 3). Template regression test still green.

PIECE 3 — Coverage by log source (see what each device buys you):
  Deterministic read-time grouping: rules grouped by their log_source
  normalized through the SAME matcher the ranking bridge uses (reuse it
  — do NOT write a second normalizer); per group: rule count, the
  techniques those rules map to with states, and tactic names. Surface:
  (a) results page — the UploadSummaryCard's log-source list becomes
  clickable, opening the existing DrillDownPanel/RuleListPanel pattern
  with a header like "What Sysmon gives you: 12 rules alerting on 9
  techniques"; (b) one new XLSX sheet "Coverage by Log Source" (plain
  columns: Log source | Rules | Techniques covered | Attack stages |
  Techniques), added to the scope map alongside Use-Case Mappings.
  Ungroupable log_source values fall into an "Other / unrecognized"
  group, never dropped. No pipeline change — compute in the router/
  report layer from stored use_cases + technique_results.

PIECE 4 — Unmonitored-capability check (the Infoblox insight):
  New curated data/device_classes.json (same cited-and-test-enforced
  style as the other curated files): appliance-class keyword ->
  expected primary telemetry category + plain-English capability name.
  Seed ~10 classes: dns appliance/infoblox/bluecat -> network (DNS
  query logs), edr vendors -> endpoint (process/endpoint logs), email
  gateway/proofpoint/mimecast -> application (email logs), firewall
  vendors -> network (traffic logs), idp vendors -> identity (sign-in
  logs), backup/rubrik/veeam -> application (backup audit logs), proxy
  -> network, waf -> application. At parse time, for each Assets/
  Security Tooling entry matching a class: if NO Log Sources row maps
  to the expected category, emit ONE aggregated finding per device
  class (not per gap). Wording bar (match this): "Your inventory lists
  a DNS appliance (Infoblox), but no DNS-log source is declared. Its
  main security value — spotting attacks in DNS traffic — appears
  unmonitored. Declaring/enabling DNS query logging would move N gaps
  closer to buildable." N = the existing feasibility category
  intersection, aggregated; list the top few technique IDs. Surface:
  assumptions slot (free flow to UI tab, PDF appendix, XLSX Assumptions
  — verify all three render it) AND the UploadSummaryCard as a
  highlighted insight line. If the environment workbook has no Log
  Sources sheet at all, the check is silent (no claim without data).
  Tests: class-map integrity (keys resolve to real bridge categories),
  flagged/not-flagged goldens (DNS appliance + no DNS source ->
  finding; DNS appliance + DNS source -> silent; no workbook ->
  silent), wording snapshot, E2E assumption presence.

Wrap-up: full suite alone on edgp_test (pg_stat_activity first) +
npx tsc --noEmit; update the CLAUDE.md baseline, module reference
(§5/§6/§11/§12/§13/§15), IMPLEMENTATION_PROGRESS.md, tick A10 here.
Commit per piece (4 commits + docs).

DEPLOY (authorized): push, standard VPS loop (no migration), smoke on
https://scopewise.assessiq.in: re-create an Acme-style assessment —
Photon/Infoblox/Rubrik rows now resolve (orange unmapped line shrinks
to IoT + z/OS only), the unmonitored-capability insight appears when
DNS logs are omitted, log-source list is clickable, XLSX has the new
sheet. Touch ONLY scopewise-* containers.

Report: per-piece diff summary, suite + tsc results, deploy SHA, smoke
table with the before/after unmapped-assets line.
```

## Phase A11 — Report/template visual polish (XLSX headers, template borders, executive PDF flow)

Added 2026-08-03 from user UI/report review. Three cosmetic fixes, zero
behavior change — no numbers, no parsing, no pipeline. Verified starting
state: template header rows are bold but have NO fill; template content
cells have NO borders; every PDF section h2 carries `page-break`
(`page-break-before: always`), which strands mostly-blank pages in the
executive cut.

```text
Read CLAUDE.md, docs/planning/MITRE_MODULE_REFERENCE.md §11,
apps/api/app/mitre/report_xlsx.py, templates/style.css +
executive.html/detail.html/appendix.html, the two templates in
apps/web/public/templates/, and the Ground rules of
docs/planning/MITRE_ACCURACY_IMPROVEMENT_PLAN.md. Baseline: whatever
the CLAUDE.md line says when you start (863+/7); tsc clean. Run A10
first if it is still unchecked — this phase may touch the same files.

PIECE 1 — XLSX report header fills (report_xlsx.py): every sheet's
header row gets ONE consistent, unique background fill (use the
existing branded band color family — dark fill + the existing
white-bold font) so headers are visually distinct from data rows on
every sheet, including the Technique Tracker and any sheet added by
A10. Audit all sheets; some already have styled headers — make them
uniform, not additive. Data-row fills (state/tier colors) unchanged.

PIECE 2 — Downloadable templates (apps/web/public/templates/*.xlsx):
regenerate BOTH template files with styling only — header/sheet names
and all cell VALUES stay byte-identical to today (Ground rule 3; the
ingest regression test must still pass unchanged):
  a. Header rows: same unique fill as Piece 1 + bold white font.
  b. All-borders (thin) on header + example rows, AND pre-format ~100
     blank data rows per sheet with the same thin borders so customer-
     entered content lands in a visible grid (form feel). Column
     widths sized to the headers/examples.
  c. Do it via a small throwaway script run once (scratchpad, not
     committed) OR commit a scripts/build_mitre_templates.py if one
     does not exist — prefer the committed generator so future template
     edits stop being hand-surgery. Open both files after writing to
     verify (openpyxl readback assertions in the existing template
     test: header fill present, example-row border present).

PIECE 3 — PDF whitespace / flow (templates + style.css): target: no
page in the executive PDF (scope=executive) more than ~10-20% blank.
  a. Remove `page-break` from section h2s WITHIN the executive scope —
     content flows continuously; a section starts on a new page only
     when it would not fit at all. Keep `page-break-inside: avoid` on
     atomic blocks (scorecard, .fix cards, tables' header+first rows)
     so nothing splits ugly.
  b. Full PDF: keep hard breaks only where a genuinely new PART starts
     (cover -> executive -> detailed -> appendix). Between sections
     inside a part (roadmap -> gap register -> telemetry reference,
     tactic sections), drop the forced break and let flow decide.
  c. Verify with a real WeasyPrint render (Docker if local libs are
     absent — the A9 session's disposable-container pattern): report
     executive page count before/after and eyeball-describe the blank
     share; assert no orphaned heading (heading alone at page bottom —
     use `page-break-after: avoid` on h2/h3).
Tests: existing report goldens still green (styling asserts only where
the template test already reads styles); no numeric output changes.
Wrap-up: full suite alone on edgp_test + tsc, docs (reference §11,
progress, tick A11 here), commit per piece.

DEPLOY (authorized): push, standard VPS loop (no migration), smoke:
download both templates from the live wizard (header fill + bordered
grid visible in Excel), full + executive PDF (executive now flows
continuously, blank share visibly reduced), full XLSX (uniform header
fills on every sheet). Touch ONLY scopewise-* containers.

Report: per-piece diff summary, executive PDF page count before/after,
suite + tsc results, deploy SHA, smoke table.
```

## Phase A12 — Scope auto-trend to the same customer

Kickoff prompt for a fresh session (self-contained):

```
A12 — Scope MITRE auto-trend to the same customer

Read docs/planning/MITRE_MODULE_REFERENCE.md and
docs/planning/MITRE_ACCURACY_IMPROVEMENT_PLAN.md (status table) before
touching anything under apps/api/app/mitre/ or apps/web/app/mitre/.

PROBLEM (confirmed in code, 2026-08-03): The report's "Trend vs your
previous run" block auto-picks the org's most recent completed
assessment, filtered only by org_id — see the trend query in
apps/api/app/mitre/router.py (~lines 1814-1838, "Phase 14e: trend
block"). mitre_assessments (apps/api/app/models/mitre_assessment.py)
has no customer/project field — only org_id + free-text name. For an
org running assessments for multiple end customers, customer A's run
gets diffed against customer B's last run, producing garbage like
"applicability changed: 292" (real prod symptom, observed against
"Acme MITRE Assessment"). Trend must only compare runs for the same
customer.

FIX SPEC (deliberately migration-free — do NOT add a column or
migration):

1. Storage: optional `customer` string (trim, cap ~200 chars,
   empty -> absent) inside the existing params JSONB on
   mitre_assessments.
2. Intake: accept `customer` on the assessment-create API path and add
   one optional text input ("Customer / engagement") on the
   create/intake form in apps/web/app/mitre/. Show it in the
   assessment list/detail where the name is shown, if trivial.
3. Sentinel auto-import: stamp params["customer"] in
   _create_assessment_from_pull (service + all 3 call sites incl.
   scheduled pulls in tasks.py) from the connector/workspace name, so
   scheduled re-runs group naturally.
4. Trend query: add customer equality to the previous-run query in
   router.py using NULL-safe semantics (IS NOT DISTINCT FROM;
   SQLAlchemy is_not_distinct_from on params["customer"].astext) —
   NULL matches NULL, so existing orgs with no customer set keep
   today's behavior. When no prior run matches, the trend block is
   already omitted (previous is None) — keep that.
5. Unchanged: the explicit /assessments/{id}/compare/{other_id}
   endpoint stays user-choice, no filter. The trend rendering in
   apps/api/app/mitre/report.py (~line 299 trend_html) needs no
   change. Check whether the compare block also feeds the XLSX report
   and confirm nothing else consumes the auto-picked baseline.

CONSTRAINTS:
- No migration, no new tables/columns, no new dependencies.
- Minimal targeted tests only (project rule): trend picks
  same-customer baseline; NULL<->NULL still matches; cross-customer
  run is skipped; customer is truncated/stamped on the sentinel path.
- Backend baseline is 879 passed / 7 skipped
  (cd apps/api && python -m pytest) — don't regress; update the
  baseline line in CLAUDE.md if new tests land. Never run the suite
  while another session is running it (shared edgp_test DB deadlocks —
  check pg_stat_activity first).
- Frontend: cd apps/web && npx tsc --noEmit must be clean.
- Update the A-phase status table here (tick A12) and
  docs/IMPLEMENTATION_PROGRESS.md at session end.
- Do not commit/push/deploy until explicitly asked. Deployment, when
  asked, follows the standard VPS loop in CLAUDE.md (no migration to
  apply this time).

Report: working code + tests green + a short summary of diffs per
file.
```
