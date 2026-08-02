# Session handoff — MITRE Phase 14a: gap drill-down drawer (2026-08-02)

**Headline:** Phase 14a COMPLETE and DEPLOYED. The technique drawer now
answers *what is this / where is the gap / why is it a gap / what would
good look like* in plain English for every state, driven by two new
hand-curated data files + a pure derivation module. No migration, no
pipeline change, no runtime LLM. Suite **781 → 797 passed / 7 skipped**;
`tsc` clean; prod smoke green (login/mitre 200, API 401 unauth, explain
route registered, all `scopewise-*` containers healthy).

## Commits (pushed, deployed at `db0726b`)

- `58384f6` — MITRE sample test-data kit (generator + fixtures; from the
  prior session, was untracked)
- `5ae5b27` — Phase 14 UX clarity plan + per-sub-phase kickoff prompts
  (also previously untracked)
- `98c82b0` — Phase 14a implementation
- `db0726b` — docs: reference/progress/baseline updates

## What landed (14a)

- `apps/api/app/mitre/data/technique_plain_language.json` — 57 curated
  techniques (priorities ∪ threat-profiles union; the plan's "~150" was
  an overestimate — the deterministic rule yields 57, test-enforced).
- `apps/api/app/mitre/data/tactic_lines.json` — 21 tactic-shortname story
  lines (the plan said 12; the v19.1 dataset actually has 21 shortnames
  across the three domains — all covered, test-enforced).
- `apps/api/app/mitre/plain_language.py` — pure: curated/fallback
  `describe_technique`, `detection_sketch`, golden-tested `derive_why`
  (6 state variants). **14c reuses this for the XLSX "Why" column.**
- `GET /assessments/{id}/techniques/{tid}/explain` + a small
  `ranking.technique_feasibility` helper (via/log-source for non-gap
  techniques; gaps reuse their stored gap entry).
- Frontend: `TechniqueExplain` type, per-open fetch in the results page,
  four blocks in `TechniqueDrawer` with graceful fallback to the pre-14a
  content when the fetch fails; existing N/A block kept as that fallback.
- `apps/api/tests/test_mitre_plain_language.py` — 16 tests: file
  validation vs the pinned dataset, why-phrase goldens (incl. the
  sample-kit covered-vs-disabled acceptance), endpoint E2E
  (sibling closest-rule, 404/409).

## Next action

Phase **14b** (clickable numbers — needs 14a's drawer, now merged) per
`docs/phases/prompts/MITRE_PHASE_14_UX_PROMPT.md`. Then 14c/14d/14e/14f.
Tests pass: Y (797/7 + tsc clean). Open questions: none.

## Agent utilization

- Opus (main): full implementation, curated content authoring, tests,
  docs, deploy — self-executed (hot cache, curated security text is
  quality-sensitive; no mechanical N-file rollout to delegate)
- Sonnet: n/a — no delegable mechanical work this session
- Haiku: n/a — no bulk sweeps needed
- codex:rescue: n/a — read-only presentation endpoint reusing existing
  org-scoping helpers; not security/auth/classifier-adjacent (noted per
  the scale-rigor rule)
