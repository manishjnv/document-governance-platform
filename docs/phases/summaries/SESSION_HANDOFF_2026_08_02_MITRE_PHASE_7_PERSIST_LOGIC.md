# Session handoff — 2026-08-02 — MITRE Phase 7: persist detection logic

**Headline:** Phase 7 done per
`docs/phases/prompts/MITRE_PHASE_7_PERSIST_LOGIC_PROMPT.md` — detection
logic/query text is now persisted (`mitre_use_cases.logic`, migration 032)
and fed to both taggers. Before/after on a realistic
both-columns dump: keyword-tagged went **1/12 → 10/12** (9 fewer rows'
worth of AI calls; residue only for genuinely fuzzy rules). NOT
committed/pushed/deployed — user gate per the kickoff wrap-up. **After
this, the MITRE module has NO known quality gaps** (remaining plan-§14
items are optional features, built only on request).

**Commits:** none (working tree holds the change set).

**Tests:** full suite **687 passed / 7 skipped** (baseline 686 + 1 new
E2E; the XLSX assertions extended an existing test). Migration 032
applied to edgp_dev + edgp_test
(`\d mitre_use_cases` shows `logic text`); **prod pending deploy**. No
frontend change → tsc untouched (verified nothing renders description).

**Adversarial (light Sonnet pass, per prompt): ACCEPT, zero blocking
findings.** All five vectors verified clean against the working tree +
live DBs: prompt injection (tagging payload is `json.dumps`-encoded; the
narrative agent receives only aggregated computed data, never raw
logic), cap enforcement end-to-end (2000 DB / 2000 scan / 500 LLM
excerpt; extraction rows correctly leave logic NULL; no historical row
can exceed the caps), report injection (logic appears nowhere in the
HTML; the XLSX cell is `_guard`ed and test-pinned), NULL safety at every
consumer. The one V4 note — `GET .../use-cases` doesn't return `logic` —
is the deliberate YAGNI call below; the reviewer agreed it blocks
nothing (no UI renders description/logic).

**Next action:** on user approval — commit, push, standard VPS loop,
**apply migration 032 to `scopewise_prod`**, smoke.

---

## What changed

- **Migration `032_mitre_use_case_logic.sql`** — idempotent, txn-wrapped
  `ADD COLUMN IF NOT EXISTS logic TEXT`. Plain nullable column, no CHECK →
  the 5th ORM-sync-point rule doesn't apply; model gains
  `logic: Mapped[Optional[str]]` in lockstep. Not a `test_insights_extra`
  table.
- **`router.create_assessment`** — description and logic stored
  **separately**; the old "fold logic into description when description is
  empty" fallback is gone. Logic keeps the Phase 6 `[:2000]` cap (32K/cell
  is legal XLSX). pdf/docx extraction rows and customer-tagged rows are
  unaffected (their logic stays NULL).
- **`service.py`** — both tagger dict builds now pass
  `"logic": uc.logic or ""`; the keyword matcher already scanned all three
  fields (`_FIELD_CAP=2000`), the LLM excerpt cap (`EXCERPT_CAP=500`)
  already applied per field. The Phase 6 "logic is dead" ponytail comment
  removed — it's alive now.
- **`report.py`** — XLSX "Use-Case Mappings" sheet gains a final "Logic"
  column (the `sheet()` helper `_guard`s every cell, so `=`-payload query
  text can't execute as a formula). `_load_use_case_dicts` passes logic
  through. HTML report and the drawer never showed description, so per the
  prompt's "only if already shown" rule they get nothing — noted, not a
  deviation.

## Before/after (the point of the phase)

12-rule dump where every rule has a prose description AND the tool string
only in the logic column — exactly the case that silently dropped logic
pre-032: before **1/12** keyword-tagged (11 to AI), after **10/12** (2 to
AI). All 9 new mappings hand-verified correct (mimikatz→T1003.001,
`-enc`→T1059.001, schtasks→T1053.005, vssadmin delete→T1490,
`wevtutil cl`→T1685.005, rundll32→T1218.011, wmic→T1047, nltest→T1482,
rclone→T1567.002); the 2 residual rows (impossible travel, beaconing) are
genuinely non-keywordable and correctly go to AI. Bonus precision check:
`PSEXESVC` does NOT false-fire the `psexec` alias (boundary guard), and
that row was already covered via the "Service Execution" name match.

## Tests added (4 assertions across 2 files)

`test_logic_persisted_and_fed_to_both_taggers` (test_mitre_api.py):
both-columns dump stores both fields distinctly (the dropped-logic
regression), keyword pre-pass fires on a logic-only tool string
(schtasks → T1053.005 covered), and the mocked AI tagger receives the
real logic text for the residue row. `test_xlsx_formula_injection_guard`
extended: new Logic column present at J and a `=cmd|...` logic payload is
apostrophe-guarded.

## Deviations

None of substance. Logic is not added to the `GET .../use-cases` API
response (nothing in the UI displays it; XLSX is the export surface —
YAGNI, one line away if a drawer feature ever wants it).

## Files touched

Modified: `apps/api/app/mitre/{router,service,report}.py`,
`apps/api/app/models/mitre_use_case.py`,
`apps/api/tests/test_mitre_{api,report}.py`.
New: `apps/api/migrations/032_mitre_use_case_logic.sql`.

## Agent utilization

- Opus/Fable (main): recon, all implementation + tests, before/after
  demo, docs (small classifier-feed change; files hot — self-execute).
- Sonnet: light adversarial pass on the logic-injection vectors —
  ACCEPT, zero blocking · reworked: N.
- Haiku: n/a — no bulk sweeps.
- codex:rescue: n/a — companion broken (memory 2026-07-23); Sonnet
  fallback per standing approval.
