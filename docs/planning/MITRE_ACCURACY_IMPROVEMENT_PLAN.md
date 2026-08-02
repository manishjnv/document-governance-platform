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
| A8 | Threat-profile expansion + region weighting | ☐ |

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
