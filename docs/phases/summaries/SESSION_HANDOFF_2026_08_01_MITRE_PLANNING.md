# Session handoff — 2026-08-01: MITRE assessment design (no code)

**Headline:** design-only session. Full design + implementation plan for
the new MITRE ATT&CK coverage-assessment module written and reviewed with
the user (`docs/planning/MITRE_ASSESSMENT_PLAN.md`); Phase 0 kickoff
prompt ready (`docs/phases/prompts/MITRE_PHASE_0_PROMPT.md`). No code,
migrations, or deploys — the SOW/RFP product is untouched.

## What the plan covers (headline)

Customer uploads SIEM use-case/detection dump + asset inventory (+ short
intake form) → MITRE ATT&CK coverage assessment: coverage % overall / per
domain (Enterprise+ICS+Mobile) / per tactic / per TTP; ranked gaps with
exact per-gap recommendations tied to their log sources; 0-3/3-9/9-18 mo
remediation roadmap; assumptions + explicit N/A techniques; in-app +
PDF + XLSX outputs; trend comparison between assessments. Input types:
xlsx/xls/csv/pdf/docx. **Hard constraint recorded: zero behavioral change
to existing functionality** — new `app/mitre/` package, new tables, new
`/mitre` frontend section; exactly two shared files gain one addition
each. Key decisions locked with the user are tabled in the plan doc.

## Doc-structure decision (recorded in CLAUDE.md)

Full design/plan docs go in `docs/planning/`; `docs/phases/prompts/` is
for short runnable kickoff prompts only (may point at a planning doc).
Historical full plans already in prompts/ stay put.

## Also in this commit set

- ~13 real SOW sample/template PDFs added under `docs/sample/`
  (user-sourced; feedstock for the ≥10-doc ground-truth labeling effort).
- `AGENTS.md` (a claude-mem plugin context dump at repo root) is NOT
  committed — added to `.gitignore`; it contains internal session
  observations that don't belong in the public repo.

## State

- No code changes; test baseline unchanged (583 passed / 6 skipped as of
  2026-07-24); prod untouched this session.
- `docs/IMPLEMENTATION_PROGRESS.md` header updated to 2026-08-01.

## Next action

Run Phase 0 via `docs/phases/prompts/MITRE_PHASE_0_PROMPT.md` in a fresh
session (data + pure logic, no UI). Before building, skim the plan's
locked-decisions table — do not re-litigate them.

## Agent utilization

- Opus (Fable): design discussion, plan + kickoff prompt authoring, docs
- Sonnet: n/a — no implementation this session
- Haiku: n/a
- codex:rescue: n/a — no code to gate (and companion still broken per memory)
