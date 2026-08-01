# Kickoff prompt — MITRE Assessment Phase 5 (final validation, cleanup, launch readiness)

Self-contained kickoff prompt. Paste everything below the line into a
fresh session (target model: Fable 5 main session). This is the LAST
planned phase of the MITRE module.

---

Complete **Phase 5** of the MITRE ATT&CK coverage-assessment feature for
ScopeWise — the closeout phase. `docs/planning/MITRE_ASSESSMENT_PLAN.md`
(§11 security, §13 Phase 5, §14 out-of-scope, §15 open questions) is the
authoritative design.

## Context

ScopeWise (FastAPI `apps/api`, Next.js `apps/web`). The MITRE module
Phases 0–4 are COMPLETE, verified, adversarially signed off, and **live
in production** as of 2026-08-02:

- Backend: dataset (ATT&CK v19.1), applicability/coverage/ranking pure
  logic, AI tagging + narrative agents, full API, hardened (two
  adversarial passes: Phase 2 REVISE→fixed, Phase 4 ACCEPT), migration
  029 in all 3 DBs.
- Frontend: `/mitre` list + wizard + results (heatmap/gaps/assumptions/
  compare tabs), PDF/XLSX download, per-domain bars, trend arrows,
  templates.
- Baselines: backend **649 passed / 7 skipped** (7th = prod-only
  WeasyPrint PDF render test); `tsc --noEmit` clean. Everything pushed
  (HEAD ≈ `8a608c0`) and deployed.

Unlike prior phases, most feature work is DONE. Phase 5 is validation +
two carried-over pending items + one small decision. Do NOT add new
feature scope (see plan §14 for what's deliberately deferred — column-
mapping wizard, per-mapping override UI, threat-informed weighting,
Navigator layer export, continuous re-assessment). If you believe a new
feature is needed, stop and ask rather than building it.

## Read first (one parallel burst), then state your plan in a few lines

1. Root `CLAUDE.md`; `docs/planning/MITRE_ASSESSMENT_PLAN.md` §11/§13/§15;
   `docs/phases/summaries/SESSION_HANDOFF_2026_08_01_MITRE_PHASE_0_1.md`
   (its Phase 4 section carries the Phase 5 checklist and the two pending
   items).
2. `apps/api/app/compliance/audit.py` + the `audit_logs` table's
   `resource_type` CHECK (the enum decision below).
3. `docs/RCA_LOG.md` — add an entry if any real bug surfaces here.

## Tasks (each is small; do them in this order)

### 1. AI-tagging quality smoke (carried from Phase 2)

Blocked since 2026-08-01 on the OpenRouter account daily cap (usage was
2.046 / 2.00). **Check the key first** — one cheap call, or the free
key-status endpoint. If it works: run a mixed dump (≈2 customer-tagged +
6 untagged rules) through create→run→results on the local dev stack
(with the dev CORS port set), and report mapped/unmapped counts plus 5
AI mappings hand-checked against what a human would tag. If still capped,
record it as still-pending and move on — do not block the phase on it.

### 2. Real-PDF render smoke on prod (carried from Phase 4)

The PDF render path only works where WeasyPrint's native libs exist
(prod image). Verify on prod: authenticate, create+run a small
customer-tagged assessment (no LLM needed), then
`GET /api/v1/mitre/assessments/{id}/report?format=pdf` and confirm a
valid PDF comes back (magic bytes `%PDF`, opens, numbers match the
stored summary). Use the standard VPS access; clean up the test
assessment after (soft-delete via the API). Report the outcome.

### 3. audit_logs resource_type enum decision (deferred wart)

MITRE audit rows currently use `resource_type="organization"` because
the `audit_logs.resource_type` CHECK is closed and extending it needs an
ALTER (a shared-schema change deliberately deferred through Phases 1–4).
Decide and either:
- (a) Extend the CHECK to add `mitre_assessment` via a new migration
  `030_audit_mitre_resource_type.sql` (idempotent, applied to all 3 DBs
  per the CLAUDE.md checklist; update `app/compliance/audit.py`'s
  allowed set and the mitre `log_action` calls), OR
- (b) Consciously keep `organization` and document why (the action
  string `mitre.*` already carries the semantics).
This is a security-adjacent shared-schema change — if you take path (a),
it needs an adversarial sign-off before push (Sonnet takeout per the
codex:rescue outage). Recommend (a) unless the migration cost outweighs
the audit-clarity gain; state your reasoning and let the acceptance
below gate it.

### 4. Final full-module review pass

One adversarial read of the module AS A WHOLE (not just a diff), focused
on anything the per-phase reviews couldn't see across seams: an
end-to-end cross-org trace (create in org A, attempt every read/download/
compare/run/delete/settings endpoint as org B), the settings→coverage
math path (can a weird-but-valid tunable combo produce a nonsense %?),
and confirmation the module is still registered NOWHERE in
`ReviewOrchestrator.agents`. Report file:line for anything found; fix
blocking items in-session with a re-review.

### 5. Launch-readiness closeout

- Update `docs/IMPLEMENTATION_PROGRESS.md`: mark the MITRE module
  COMPLETE (Phases 0–5), state the module's overall status in one line,
  and list any residual out-of-scope items (plan §14) explicitly as
  "deferred, not blockers."
- Answer plan §15 open questions in the doc (Q1 viewer XLSX access — it's
  currently allowed; confirm or change; Q2 marketing page — note as a
  separate content task; Q3 priorities — already user-approved).
- Regenerate nothing in `prompts/` (that mirror is for the 6 review
  agents only — MITRE prompts live in PROMPT_ENGINEERING_GUIDE.md).
- Write the final session handoff.

## Acceptance (run, don't assume)

- Full suite green at or above **649 passed / 7 skipped** (plus any new
  migration/enum tests); `tsc --noEmit` clean.
- If task 3 path (a): migration applied to edgp_dev + edgp_test (+ prod
  on deploy), adversarial sign-off logged.
- Prod PDF smoke result reported (pass, or a real bug filed in RCA_LOG).
- `git status` clean after commits; only intended files touched.

## Wrap-up

Do NOT commit/push/deploy unless the user explicitly says so. Report:
each task's outcome, the enum decision + reasoning, the tagging-smoke
result, the prod PDF result, any bugs found + fixed, and a one-line
"MITRE module is launch-ready / has residual blockers: …" verdict. This
is the module's closeout — leave the docs so a future reader sees the
whole feature as done.
