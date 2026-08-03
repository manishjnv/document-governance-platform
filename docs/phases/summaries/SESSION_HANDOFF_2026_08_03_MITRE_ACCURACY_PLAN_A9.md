# Session handoff — MITRE accuracy plan, Phase A9 (2026-08-03)

Report consolidation: XLSX Technique Tracker + PDF roadmap dedup. Read
`docs/planning/MITRE_ACCURACY_IMPROVEMENT_PLAN.md` (Ground rules + Phase
A9 block) before touching this area again.

## What shipped

**Commits** (master): `95afea6` (xlsx), `caafcfd` (pdf), `fa41b43`
(tests), docs commit (this file's own commit).

**PART 1 — XLSX (`app/mitre/report_xlsx.py`):** replaced "Technique
Register", "Gaps & Recommendations", and "Roadmap" (Roadmap was the same
gap dicts re-bucketed; Gaps was a subset of the Register — pure
duplication) with ONE **Technique Tracker** sheet:
- One row per applicable technique (`state != not_applicable`); covered
  rows leave the 8 gap-only columns blank (Priority, Threat match, Crown
  jewel, Feasibility, Roadmap bucket, Recommendation, Log fields needed,
  Via).
- 19 columns: Technique ID, Name, Tactic(s), Domain, State, Why,
  Strength, Priority (numeric `"P"0` format + `ColorScaleRule`, 14h
  pattern), Threat match, Crown jewel, Feasibility, Roadmap bucket
  (Short/Mid/Long as a plain value, separate from the descriptive
  Feasibility label), Recommendation, Log fields needed, Via, then four
  blank customer-tracking columns — Owner, Status, Target date, Notes.
- No interleaved section-header rows (the old Gaps sheet's bucket-header
  rows broke auto-filter/sort); auto-filter + frozen header span the
  whole sheet.
- Scope pruning: `coverage` and `gaps` per-tab downloads both now keep
  the Tracker (it carries both roles); `assumptions` unaffected.
- Read Me guide text rewritten to describe the merged sheet.

**PART 2 — PDF (`app/mitre/report.py` + `templates/detail.html` +
`templates/style.css`):** the old single block re-rendered every gap's
full narrative grouped by feasibility bucket, conflating "roadmap
at a glance" with "full per-gap detail". Split into two sections:
- **Roadmap** (`<h2 id="roadmap">`): per bucket, the existing prose +
  item count, followed by a compact 4-column index table — Technique
  ID, Name, Priority, and a `details p. N` cross-ref using the existing
  Phase 14e `target-counter` CSS pattern (`a.xref`).
- **Gap register** (`<h2 id="gapreg">`): the single, content-unchanged
  home of every gap's why-phrase/detection-sketch/telemetry-pointer/
  recommendation — reformatted from spaced-out `<div class="gap">`
  cards into one dense `<table class="compact">` (same text, far less
  chrome), one `<tr id="g-{technique_id}">` per gap so the roadmap's
  cross-refs resolve. The Phase 14i "Log fields reference" table
  (printed once, after the register) is unchanged.
- `_SECTION_SCOPES` updated: `coverage` ends before the roadmap heading;
  `gaps` now starts there, so the gaps-tab PDF keeps both the roadmap
  index and the full register.

## Honest page-count result (do not overstate this in future docs)

Measured with a real WeasyPrint render (disposable Docker container —
WeasyPrint has no native libs on this Windows dev machine) on a
synthetic-but-real 603-gap assessment (`compute_applicability` +
`compute_coverage` + `rank_gaps` run for real against the pinned ATT&CK
v19.1 dataset, zero use-cases so every applicable technique is a gap —
the worst case for this section):

| | Before | After |
| --- | --- | --- |
| PDF pages | 116 | 114 |
| PDF bytes | 836,905 | 952,299 |

**The cut is modest (~2 pages, ~1.7%), not the "large share" the
motivating note in the plan anticipated.** Root cause, confirmed by
code-path analysis: the dense-table reformat of the register saves some
space per gap over the old card layout, but the new Roadmap index table
adds back roughly the same number of pages (603 rows across 3 buckets).
There was no literal content *duplication* to remove in the pre-A9 code
— the single combined block only ever printed each gap once — so the
theoretical ceiling on savings from restructuring alone (without cutting
narrative content, which was out of scope) was always going to be small.
If a future phase wants a bigger PDF-size win, the next lever is
shortening the per-gap narrative itself (out of scope for a "report
layer only" phase), not further reshuffling of sections.

## Tests

4 new/rewritten tests in `test_mitre_report.py`:
`test_xlsx_tracker_structure`, `test_xlsx_tracker_formula_guard`,
`test_xlsx_scope_pruning`, `test_html_report_roadmap_index_and_register_dedup`,
`test_html_report_gaps_scope_keeps_roadmap_and_register` (that's 5 —
`test_xlsx_phase14c_structure` was renamed/rewritten in place, not net-new,
so the suite grew by 4). Full backend suite run solo on `edgp_test`
(checked `pg_stat_activity` first — 0 other connections): **863 passed,
7 skipped** (baseline was 859; `CLAUDE.md` updated). `npx tsc --noEmit`
clean (no frontend changes this phase).

## Deploy

Authorized per the phase's DEPLOY section. See the deploy commit's
message / this session's final report message for the SHA and smoke
table (VPS: `https://scopewise.assessiq.in`, containers `scopewise-*`
only, no migration this phase).

## Docs touched

`CLAUDE.md` (baseline line), `docs/planning/MITRE_MODULE_REFERENCE.md`
(§11 both report descriptions, §13 test table + baseline, §15 history
row), `docs/IMPLEMENTATION_PROGRESS.md`, `docs/planning/
MITRE_ACCURACY_IMPROVEMENT_PLAN.md` (A9 ticked — **A1-A9 all complete**).
