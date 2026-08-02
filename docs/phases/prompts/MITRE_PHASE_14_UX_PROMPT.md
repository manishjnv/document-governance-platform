# Kickoff prompts — MITRE Phase 14: UX clarity (14a–14f)

Run one sub-phase per fresh session, in order (14d and 14f may run any
time after 14a). Paste everything inside a block. Design authority:
`docs/planning/MITRE_UX_CLARITY_PLAN.md`.

---

## 14a — Gap drill-down drawer

Implement MITRE Phase 14a per section "14a" of
`docs/planning/MITRE_UX_CLARITY_PLAN.md`. Read that plan plus
`docs/planning/MITRE_MODULE_REFERENCE.md` first — mandatory before
touching anything under `apps/api/app/mitre/` or `apps/web/app/mitre/`.

Scope: extend the existing TechniqueDrawer so every technique state
renders four plain-language blocks (what is this / where is the gap /
why is it a gap / what would good look like), driven by two NEW curated
data files under `apps/api/app/mitre/data/`
(`technique_plain_language.json` with per-technique plain definition +
detection_hint for the ~150 tier-1/2 + threat-profile techniques, and a
12-entry tactic one-liner map) with fallback to the ATT&CK description
first sentence from `attack.json`. Why-phrases are derived
deterministically from existing result data (no pipeline changes, no
new scoring). Add a test validating every curated technique ID against
the pinned dataset (pattern: the `threat_profiles.json` test) and
goldens for the why-phrase derivation.

Constraints: no migration, no new settings, curated text hand-written
(never runtime-LLM). Acceptance: all four blocks render for all six
states; the sample kit (`docs/sample/MITRE_Sample/`, README playbook)
rows 4/5 (logic vs none) and 15 (disabled) produce visibly different
why-text. Full backend suite + `npx tsc --noEmit` clean (check
CLAUDE.md for the current suite baseline; single-runner rule applies).
Update `MITRE_MODULE_REFERENCE.md` + `IMPLEMENTATION_PROGRESS.md`.
Don't commit/deploy unless I say so.

---

## 14b — Every number clickable

Implement MITRE Phase 14b per section "14b" of
`docs/planning/MITRE_UX_CLARITY_PLAN.md` (read it plus
`docs/planning/MITRE_MODULE_REFERENCE.md` first). Requires 14a's drawer
to be merged — verify it exists before starting.

Scope: one reusable drill-down list panel (technique name, state color,
plain state phrase, click-through to the 14a drawer) wired to every
number per the plan's wiring table: coverage/domain tiles, state tiles,
top-gap chips, per-tactic counts, parse-preview tiles, assumption
counts, N/A category counts. Plus microcopy: pluralization fixes
("1 rule remains unmapped"), hover definitions on legend items and
column headers, and the coverage-headline subtitle + "is this % bad?"
info popover.

Constraints: frontend-only plus any tiny API field already computed but
not exposed (no pipeline changes). Acceptance: no numeric stat on the
assessment or parse-preview screens is inert; keyboard accessible;
`npx tsc --noEmit` clean; backend suite untouched or still green.
Update the two docs. Don't commit/deploy unless I say so.

---

## 14c — Excel export polish

Implement MITRE Phase 14c per section "14c" of
`docs/planning/MITRE_UX_CLARITY_PLAN.md` (read it plus
`docs/planning/MITRE_MODULE_REFERENCE.md` first). Reuses 14a's
plain-language file and why-phrases — verify 14a is merged.

Scope: XLSX builder in `apps/api/app/mitre/report.py`. New "Read Me"
first sheet (sheet guide, real colored legend cells, key numbers,
context line); all sheets get frozen headers, auto-filter, sane widths,
wrapped untruncated text; state/priority/feasibility color fills;
Technique Register gains Name + Why columns and tactic names instead of
TA IDs; Use-Case Mappings numerically sorted with plain-words mapping
statuses; Gaps grouped by feasibility with colored section headers;
Summary gains a plain-language explanation column and renames
"Strict %" → "Coverage %".

Constraints: no changes to computed numbers; openpyxl styling only.
Acceptance: existing XLSX tests extended (structure goldens, not pixel
styling); full suite green (check CLAUDE.md baseline; single-runner
rule). Regenerate a sample export against the kit in
`docs/sample/MITRE_Sample/` and eyeball it. Update the two docs. Don't
commit/deploy unless I say so.

---

## 14d — Project metadata + "what you uploaded" card

Implement MITRE Phase 14d per section "14d" of
`docs/planning/MITRE_UX_CLARITY_PLAN.md` (read it plus
`docs/planning/MITRE_MODULE_REFERENCE.md` first).

Scope: optional intake fields (organization/project name, scope label,
prepared-by, purpose note) riding the existing intake JSONB — verify
against the model that no migration is needed; if one IS needed, stop
and tell me before writing it (CLAUDE.md migration checklist has 5 sync
points). Surface the metadata on the assessment header and in both
exports' summary blocks. Add the "What this assessment is based on"
card (use-case file: name, rule count, tagged/keyword/AI/invalid split,
disabled count; environment file: name, platforms, OT/mobile flags,
inventory counts, unmatched entries) — all values already exist in
parse results/assumptions; numbers clickable via the 14b panel if 14b
is merged, otherwise plain.

Acceptance: assessments created before this change render unchanged
(every field optional); card numbers exactly match the parse preview.
Suite + `tsc` clean. Update the two docs. Don't commit/deploy unless I
say so.

---

## 14e — PDF report redesign

Implement MITRE Phase 14e per section "14e" of
`docs/planning/MITRE_UX_CLARITY_PLAN.md` (read it plus
`docs/planning/MITRE_MODULE_REFERENCE.md` first). Requires 14a (curated
content) and 14d (metadata/upload summary) merged — verify.

Scope: rebuild the WeasyPrint HTML template in
`apps/api/app/mitre/report.py`. Order: cover (project metadata, upload
summary, version, headline + plain subtitle) → executive section, HARD
max 2 pages (per-domain traffic-light scorecard, top-5 fixes in plain
words with threat-profile tie-ins, roadmap-at-a-glance with the
effort-to-impact projection, trend when a previous completed run
exists) → detailed section (stacked per-tactic CSS/SVG bars with tactic
one-liners, gap register grouped by feasibility where each entry
carries why-it's-a-gap + detection sketch + via-log-source + the
AI-recommendation with badge, mini per-domain parent-level heatmap
grid) → appendices (register, N/A, assumptions, mappings with 14c's
plain-words/ordering fixes). Table of contents with real page numbers
(`target-counter`), running header with project name + page N of M,
cross-references from executive items to detail pages.

Constraints: deterministic HTML/CSS/inline-SVG only — no JS, no
runtime LLM for layout/visuals; computed numbers unchanged.
Acceptance: prod-only render test still passes; executive section
never exceeds 2 pages regardless of gap count; numbers match UI/XLSX.
Suite green (CLAUDE.md baseline). Update the two docs. Don't
commit/deploy unless I say so.

---

## 14f — Past-run history

Implement MITRE Phase 14f per section "14f" of
`docs/planning/MITRE_UX_CLARITY_PLAN.md` (read it plus
`docs/planning/MITRE_MODULE_REFERENCE.md` first). Note: the `/mitre`
list page ALREADY shows past runs with status, coverage %, trend arrow,
and domain mini-bars — build on it, don't rebuild it.

Scope: "Past runs" dropdown in the assessment header (date, coverage %,
delta; jump to any run; "Compare with this run" shortcut into the
Compare tab); list enrichment (14d project name on rows, client-side
search/filter by name and status, coverage sparkline across completed
runs); rename + archive (soft flag — archived runs hidden from the
default list but still selectable in Compare; NO deletes). Prefer the
existing JSONB for the rename/archive flags; if nullable columns are
genuinely needed, stop and tell me before writing a migration.

Acceptance: any past run reachable in two clicks from inside an
assessment; archived runs still available in Compare; suite + `tsc`
clean. Update the two docs. Don't commit/deploy unless I say so.

---

## 14g — Per-item evidence trail

Implement MITRE Phase 14g per section "14g" of
`docs/planning/MITRE_UX_CLARITY_PLAN.md` (read it plus
`docs/planning/MITRE_MODULE_REFERENCE.md` first). Best run after
14c/14d/14e so its output slots into their surfaces; degrade gracefully
if any of those aren't merged.

Scope: surface the already-persisted provenance per item. Per rule: the
mapping journey (file row ref → validation outcome → mapping source +
verbatim stored rationale + confidence → which technique cells it
affects + strength breakdown). Per environment entry: extend
`parse_environment_file` with an additive per-entry interpretations
list (entry → platform matched / ICS or mobile flag / skipped via
Present=No / unrecognized) and persist it with results; render in the
14d card expansion, a 14c XLSX sheet, and a 14e PDF appendix ("How we
read your files"). Per intake input: which gaps got threat-match badges
from industry/actors, which N/A rows each exclusion produced, which
rules the disabled-rules policy demoted.

Constraints: no coverage-number changes; parser change is additive
output only (existing tests must pass unmodified except new
assertions). Acceptance: every rule and environment entry of the sample
kit (`docs/sample/MITRE_Sample/`) shows a correct evidence chain — rows
15/16/17 and the ESXi/Mainframe entries read exactly as the plan's
examples. Suite (CLAUDE.md baseline, single-runner rule) + `tsc` clean.
Update the two docs. Don't commit/deploy unless I say so.

---

## 14h — Report branding & polish (self-contained, one-go prompt)

Written to be run by a fresh session on any account with this repo
checked out — carries its own context; verification is done afterwards
by the orchestrating session.

```text
You are working in the ScopeWise repo (AI-powered SOW/RFP review
platform; FastAPI backend in apps/api, Next.js frontend in apps/web).
This task touches ONLY the MITRE ATT&CK coverage-assessment module's
report generation. Context you need:

- The module lives in apps/api/app/mitre/. Reports are generated
  server-side in apps/api/app/mitre/report.py (~1,150 lines): a PDF
  via WeasyPrint (HTML built with Python f-strings — no templating)
  and an XLSX via openpyxl. Phases 14a-14g recently shipped a full UX
  overhaul (executive+detailed PDF sections, ToC with page numbers,
  colored XLSX with a Read Me sheet); do not undo any of it.
- MANDATORY reads before any edit:
  docs/planning/MITRE_UX_CLARITY_PLAN.md (section 14h is your spec),
  docs/planning/MITRE_MODULE_REFERENCE.md (module invariants),
  CLAUDE.md at repo root (test baseline + rules).
- A populated sample kit exists in docs/sample/MITRE_Sample/ (see its
  README.md) — use it to generate before/after renders.

Implement Phase 14h exactly as specified in the plan's 14h section,
as four sequential work units, ONE git commit each, in this order:

1. REFACTOR (enabling, zero behavior change): move the PDF HTML out of
   report.py into Jinja2 templates under
   apps/api/app/mitre/templates/ (base layout + cover / executive /
   detail / appendix partials + one stylesheet file). Jinja2 is
   already installed — add no dependency. Split the XLSX builder into
   apps/api/app/mitre/report_xlsx.py. Contract: every existing report
   test passes UNMODIFIED in this commit; rendered HTML may differ in
   whitespace only.
2. BRANDING: ScopeWise logo on PDF cover + running page header (reuse
   an existing logo asset from apps/web/public/ — copy it into the
   module's assets; never fetch anything from the internet at
   runtime); professional font stack (system/bundled fonts only);
   optional diagonal watermark text. Per-org overrides for report
   display name, accent color, and watermark text via the existing
   get/set-with-org-override pattern in
   apps/api/app/admin/customization.py — backend keys only, NO admin
   UI, NO logo upload (deferred — needs file storage). Defaults must
   render when no override is set.
3. XLSX POLISH (openpyxl native only — xlsxwriter is installed but
   must NOT be used): data bars on coverage-% columns; 3-color scale
   on priority tiers; a native Excel bar chart on the Coverage by
   Tactic sheet; sheet protection on the Read Me sheet; workbook core
   properties (title, author "ScopeWise", company = org display
   name).
4. PDF METADATA + DOCS: WeasyPrint document metadata (title, author,
   subject, keywords incl. org + ATT&CK version); update
   docs/planning/MITRE_MODULE_REFERENCE.md and
   docs/IMPLEMENTATION_PROGRESS.md; add tests (template rendering
   smoke, customization-key overrides, XLSX structure incl. new chart
   sheet elements, metadata presence).

Hard constraints:
- Computed assessment numbers must not change anywhere.
- No new pip/npm dependencies; no playwright, no pandas, no S3.
- No DB migration. If per-org keys somehow require one, STOP and
  report instead of writing it (the repo has a 5-point manual
  migration checklist you must not trigger).
- Backend suite baseline is in CLAUDE.md (currently 800 passed / 7
  skipped) — must not regress; new tests may raise it. Before running
  pytest, verify no other session is using the shared test DB:
  docker exec edgp-postgres psql -U edgp_user -d edgp_test -tc
  "SELECT count(*) FROM pg_stat_activity WHERE datname='edgp_test'
  AND pid <> pg_backend_pid();"  -- must be 0 (deadlocks if not).
- cd apps/web && npx tsc --noEmit must stay clean (you likely touch
  no frontend; run it anyway).
- Commit per unit as described. Do NOT push. Do NOT deploy. Do NOT
  amend or rebase existing commits.

Self-verification before finishing: regenerate the PDF and XLSX for
an assessment built from docs/sample/MITRE_Sample/usecases_primary.xlsx
+ environment_full.xlsx (a test or script render is fine — no live
deployment needed) and confirm: logo on cover and page headers,
watermark when set, org accent color applied when the key is set,
data bars + chart visible when the XLSX is opened, PDF file
properties populated.

Final report (required, in this exact shape): (a) the four commit
hashes + one-line summary each; (b) full-suite result line and tsc
result; (c) list of new/changed files; (d) which acceptance checks
you verified and how; (e) anything you could not do, stated plainly.
```

---

## 14h — "What logs do I need?" per gap (telemetry field guidance)

Implement MITRE Phase 14h per section "14h" of
`docs/planning/MITRE_UX_CLARITY_PLAN.md`. Read that section plus
`docs/planning/MITRE_MODULE_REFERENCE.md` BEFORE touching anything under
`apps/api/app/mitre/` or `apps/web/app/mitre/` — the reference doc is
mandatory context (pipeline semantics, curated-file pattern, ORM sync
points, test baseline).

**Problem.** For a not-covered technique we tell the customer which log
source *category* could see it, but never which **fields** their query
needs — and never why an already-onboarded source might still not carry
them. Close that gap.

**Scope — one curated data file plus three read-only surfaces.**

1. Create `apps/api/app/mitre/data/telemetry_fields.json`, keyed by
   ATT&CK data-component name exactly as it appears in
   `attack.json`'s `data_sources`. Follow the shape and header-comment
   style of `data/threat_profiles.json` (a `description`, a `written`
   date, then the map). Each entry has exactly three keys:
   - `fields`: list of plain-English query parameters (no vendor field
     names, no KQL/SPL).
   - `where`: one sentence, vendor-neutral, naming the usual event
     sources (e.g. "Windows Event ID 4688, Sysmon Event ID 1, Linux
     auditd execve, or EDR process telemetry").
   - `gotcha`: ONE sentence naming the most common reason an
     already-onboarded source still can't support the detection. This is
     the point of the phase — do not skip it or pad it with generalities.

   Curate these 35 components (measured coverage: top 25 = 83% of all
   technique→component references, top 35 = 88%):

   Process Creation · Command Execution · Network Traffic Content ·
   File Creation · Network Connection Creation · Application Log Content ·
   OS API Execution · Network Traffic Flow · File Modification ·
   Module Load · File Access · Windows Registry Key Modification ·
   Process Access · File Metadata · Logon Session Creation ·
   Application Permission · User Account Authentication ·
   Process Metadata · Script Execution · Logon Session Metadata ·
   Service Creation · Application State · Response Content · Host Status ·
   Process Modification · User Account Metadata · User Account
   Modification · Cloud Service Modification · System Settings ·
   Scheduled Job Creation · Active Directory Object Modification ·
   Device Alarm · API Calls · File Deletion · Driver Load

2. Add a pure helper to `apps/api/app/mitre/plain_language.py` (module
   docstring already explains the curated-file rule) —
   `telemetry_requirements(technique_id, index=None) -> list[dict]`:
   for each of the technique's `data_sources`, return the curated entry
   or `{"component": name, "fields": [], "where": None, "gotcha": None}`
   when uncurated. Deterministic, no LLM, no network.

3. Surface it in exactly three places, adding NO new UI area:
   - `GET /assessments/{id}/techniques/{tid}/explain` → add
     `good.telemetry` (the helper's output). Render it in
     `apps/web/app/mitre/components/TechniqueDrawer.tsx` inside the
     existing "What would good look like?" block as one compact line per
     component: fields, then `where`, then the gotcha in muted text.
   - `apps/api/app/mitre/report.py` XLSX: a "Log fields needed" column on
     the "Gaps & Recommendations" sheet (respect the existing bordered/
     centered/wrapped styling helpers — do not hand-roll new styling).
   - `apps/api/app/mitre/report.py` PDF/HTML: one line per gap entry in
     the detailed gap register, under the existing detection sketch.

**Hard constraints.**
- No coverage/scoring/pipeline changes. No migration. No new settings.
- Curated text is hand-written and reviewable — NEVER generated by an LLM
  at runtime, consistent with the coding-over-AI rule in this repo.
- **Honesty boundary:** we never ingest raw logs (the wizard promises
  this). Wording must be "your query needs X; your <source> should carry
  it — verify the connector", never "your source is missing X". Do not
  add any claim of field-level verification.
- Techniques with no `data_sources` (62 of them) must keep their existing
  "bespoke detection engineering" verdict unchanged.

**Tests (add to `apps/api/tests/test_mitre_plain_language.py`).**
- Every key in `telemetry_fields.json` is a real component name present
  in `attack.json` — pattern: the existing
  `test_curated_ids_all_resolve_ok` / `threat_profiles` validation test.
- Every entry has non-empty `fields`, `where`, and `gotcha`.
- All 35 listed components are curated (guards against a partial file).
- `telemetry_requirements` returns curated data for T1059.001
  (Process Creation / Command Execution) and degrades to the bare
  component name for an uncurated one.
- Extend the XLSX structure golden in `apps/api/tests/test_mitre_report.py`
  for the new column.

**Acceptance.**
- Full backend suite green — baseline is in `CLAUDE.md` (801 passed /
  7 skipped as of 2026-08-02); the `edgp_test` single-runner rule applies,
  check `pg_stat_activity` before a full run.
- `cd apps/web && npx tsc --noEmit` clean.
- Regenerate the customer sample and eyeball one gap end to end:
  `cd apps/api && PYTHONPATH=. python ../../scripts/generate_uploadsample.py`
  then confirm a top gap (e.g. T1059.001) shows fields + where + gotcha in
  the drawer, the XLSX column, and the PDF register.
- Update `docs/planning/MITRE_MODULE_REFERENCE.md` (file map, API table,
  §13 test table, §15 history row) and `docs/IMPLEMENTATION_PROGRESS.md`.

Don't commit, push, or deploy unless I explicitly say so. Report the
unified diff plus a change log under 200 words.
