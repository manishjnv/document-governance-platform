# Session handoff — 2026-08-02 — MITRE Phase 9: column-mapping wizard

**Headline:** Phase 9 done per
`docs/phases/prompts/MITRE_OPTIONAL_FEATURES_PROMPT.md` — when column
auto-detection gets a dump wrong (or misses a column, e.g. tags under a
non-synonym header), the user can now map columns by hand in the wizard
and re-parse the stored file, instead of being forced onto the template.
**Committed `ed9cec9` and DEPLOYED to prod 2026-08-02** together with
Phase 8 (`cdf6cce`) — VPS at `ed9cec9`, no prod migrations; live smoke:
`/login` + `/mitre` 200, remap + navigator routes mounted and
auth-gated (401 unauth), GIT_SHA=ed9cec9 confirmed in-container (the
remap flow itself is covered end-to-end by the 6 API tests; a live
click-through needs a browser login).

**Commits:** `cdf6cce` (Phase 8) + `ed9cec9` (Phase 9), pushed; router
split per-phase via save/revert/re-apply, restore verified
byte-identical (sha256) to the 702/7-tested tree.

**Tests:** **702 passed / 7 skipped** — one full-suite run on an
isolated session DB certifies Phases 8+9 together (baseline 687 + 15
new; Phase 8's own final-suite output was lost to a session turnover
and its shared-DB rerun was contention-garbage, discarded).
`tsc --noEmit` clean. No migration this phase.

**Adversarial (light Sonnet pass, per kickoff): REVISE → fixed →
re-verified ACCEPT.** The reviewer's one blocking finding was the same
run-vs-remap TOCTOU I had independently found and fixed while the review
was in flight (the atomic status-conditional UPDATE guard is verbatim
the reviewer's own prescribed minimal fix); the re-review hand-traced
both lock interleavings under READ COMMITTED and confirmed closed. Two
smaller findings also applied: the remap re-parse now runs via
`run_in_threadpool` (house pattern), and `_csv_grid` gained the same
MAX_ROW_CELLS/MAX_TOTAL_ROWS budgets the xlsx/xls readers enforce (a
pre-existing gap the review surfaced; unit-tested). Org confinement,
override validation (incl. the bool-is-int gotcha), regex escaping, and
the React-only rendering of echoed cell text all verified clean.
Accepted residual: two concurrent remaps on a still-pending draft are
last-write-wins — a normal lost-update on preview state, no invariant
violated.

**Test-infra incident (recurring — now a memory + protocol):** repeated
hangs and phantom failures today from TWO sessions running the backend
suite concurrently on the shared `edgp_test` DB — conftest's `TRUNCATE
organizations CASCADE` deadlocks against the other run's
idle-in-transaction fixture connections, and its truncates delete the
other run's freshly-seeded orgs mid-test (FK violations, spurious 404s;
also hit Phase 8). An 85-minute, 42-failure "full suite" run from that
storm was discarded as meaningless. **Resolution that finally worked:
session-private test DB** — clone the schema
(`pg_dump -s edgp_test | psql edgp_testN`) and run with
`TEST_DATABASE_URL` pointing at it; the same subset that failed 5 ways
on the shared DB passed 69/69 (+1 skip) in 21s isolated. Full protocol
in memory (`edgp-test-single-runner-rule`).

**Next action:** none for Phases 8–9 — deployed and smoked. Remaining
optional MITRE work = Phases 10–13 of
`docs/phases/prompts/MITRE_OPTIONAL_FEATURES_PROMPT.md`, one per fresh
session, only if asked (10 = per-mapping override UI, 11 =
threat-informed weighting, 12 = detection-quality scoring, 13 = SIEM
pull — design-first). Housekeeping note: the session-private
`edgp_test9` DB clone is left in the local `edgp-postgres` container
for reuse per the `edgp-test-single-runner-rule` memory; drop it any
time with `DROP DATABASE edgp_test9`.

---

## What was built

- **`ingest.py`:** `parse_use_case_file(..., column_override=None)` — an
  explicit `{field: 0-based index}` map REPLACES auto-detection (header
  row + sheet still located by detection; only the field→column
  assignment is overridden). `validate_column_override` rejects unknown
  fields, non-int/bool/out-of-range indexes, duplicate targets, and a
  missing name column (→ 422). The parse result (and both preview
  responses) now carries `headers` (stringified header row) and
  `sample_rows` (first ≤5 non-empty data rows, cells capped at 200
  chars) so the wizard can render a real preview grid. All existing
  trust-boundary guards (row caps, cell-width caps, sheet caps) run
  unchanged on every re-parse.
- **`router.py`:** the create-time row-build loop (tag validation +
  tagged/unmapped/invalid counts + per-row notes) extracted into
  `_build_use_case_rows`, shared by create and remap so validation stays
  identical. New **`POST /assessments/{id}/remap`** (admin/reviewer,
  org-scoped): 409 unless `pending`; loads the assessment's own
  `use_cases` MitreFile row (422 for pdf/docx extraction dumps — no
  columns to map), `storage.download`s the stored bytes, re-parses with
  the override, then **atomically guards against a concurrent /run**
  (status-conditional UPDATE in the same transaction as the row
  replacement — the pending-check alone ran before the slow parse, a
  real TOCTOU closed during self-review) before DELETE+reinserting the
  use-case rows. `params.columns/sheet/warnings` updated;
  `parse_assumptions` keeps env-workbook notes and swaps only the stale
  per-row tag notes (regex on the sheet-prefixed row refs, escaped).
  Audited as `mitre.assessment_remapped`. Response = a fresh parse
  preview (same shape as create) so the wizard can swap state in place.
- **Frontend (`/mitre/new` + `lib.ts`):** preview card gains an "Adjust
  columns" button (spreadsheet dumps only) opening a compact panel: six
  field→header dropdowns (defaulted from the detected map, name
  required), a scrollable sample-rows table rendered from
  `headers`/`sample_rows`, Apply → POST remap → preview refreshes in
  place. React text rendering only — no HTML sinks.

## Deviations

- The create-time 422 for a dump with NO detectable name column still
  stands — remap requires an assessment to exist, so the truly
  undetectable case keeps the template escape hatch. The wizard covers
  the common failure (wrong/missed columns on an otherwise-detected
  sheet). Building a create-with-override path for the 422 case is easy
  later if real dumps demand it.
- Remap applies to the use-case dump only; environment-workbook sheets
  keep name-synonym detection (the kickoff's field list covers exactly
  the six use-case fields).

## Files touched

Modified: `apps/api/app/mitre/{ingest,router}.py`,
`apps/web/app/mitre/new/page.tsx`, `apps/web/app/mitre/lib.ts`,
`apps/api/tests/test_mitre_ingest.py`.
New: `apps/api/tests/test_mitre_remap.py`.
(Plus Phase 8's still-uncommitted files in the same tree.)

## Agent utilization

- Opus/Fable (main): recon, implementation, tests, TOCTOU self-review
  fix, DB-deadlock diagnosis/recovery, docs.
- Sonnet: light adversarial pass — REVISE (1 blocking = the TOCTOU
  already fixed in-flight, + 2 smaller applied), re-verified ACCEPT ·
  reworked: N.
- Haiku: n/a.
- codex:rescue: n/a — companion broken (memory 2026-07-23).
