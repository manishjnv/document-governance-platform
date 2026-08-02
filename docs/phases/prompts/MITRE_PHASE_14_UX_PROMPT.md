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
