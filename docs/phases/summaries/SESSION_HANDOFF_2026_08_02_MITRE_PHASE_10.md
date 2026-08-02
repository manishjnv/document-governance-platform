# Session handoff — MITRE Phase 10: per-mapping reviewer override (2026-08-02)

**Headline:** Phase 10 (third optional MITRE feature, plan §14) built,
tested, adversarially signed off (ACCEPT), committed as `6ce8e48`,
pushed, and deployed to prod with migration 033. Suite **707 passed /
7 skipped** (solo, shared `edgp_test`); `tsc --noEmit` clean.

## What shipped

A reviewer can now correct individual technique mappings on a completed
assessment and the numbers update immediately:

- **`PATCH /api/v1/mitre/assessments/{id}/use-cases/{use_case_id}/mappings`**
  (admin/reviewer, org-scoped, completed-only → 409). Body =
  `{"technique_ids": [...]}` — the FULL new list for that rule (empty
  list = "maps to nothing", max 20 IDs). Every ID goes through
  `attack_data.resolve()`: revoked → successor (note returned),
  deprecated/unknown/malformed → 422. The row becomes
  `mapping_status='manual'` with each mapping
  `{source:"manual", confidence:1.0}`.
- **Inline deterministic recompute** (`service.recompute_results`):
  re-runs applicability/coverage/ranking with the thresholds stamped at
  run time — no tagging, no LLM. Updates `technique_results` +
  `summary.{overall,domains,gaps,roadmap,not_applicable,
  applicable_domains,counts}` (counts gains a `manual` key); narrative
  prose kept, with an appended assumption noting it may predate the edit.
- **Migration 033** adds `'manual'` to the `mapping_status` CHECK; the
  ORM `CheckConstraint` in `app/models/mitre_use_case.py` updated in
  lockstep (5th sync point honored). Applied to `edgp_dev`, `edgp_test`,
  `scopewise_prod`.
- **Concurrency:** `SELECT … FOR UPDATE` on the assessment row
  serializes concurrent edits; audit event `mitre.mappings_edited`
  (`resource_type='mitre_assessment'`); cache invalidated.
- **Frontend:** TechniqueDrawer gains role-gated edit controls (remove-X
  per mapped rule; "map another rule to this technique" select), with
  "Edited by reviewer" provenance badge (`SOURCE_META.manual`). Results
  page fetches `/auth/me` for the role gate (server enforces regardless)
  and refreshes assessment + rules after each edit.

## Tests (5 new, `apps/api/tests/test_mitre_mapping_edit.py`)

Manual provenance + recompute (state flips, counts, assumption note,
audit row), empty-list unmap, invalid/malformed/non-list/over-cap 422s,
non-completed 409, cross-org 404 both ways (foreign assessment AND
foreign use_case under own assessment) + viewer 403.

## Adversarial sign-off (REQUIRED — coverage-affecting mutation)

Sonnet takeover (codex:rescue still down): **ACCEPT, zero blocking
findings.** Verified: org scoping on both lookups, resolve() rejection
coverage + anchored ID regex (no ReDoS), recompute parity with the
pipeline's persist block, FOR UPDATE race handling vs re-run/concurrent
PATCH, audit correctness. Two non-blocking notes logged: per-ID string
length uncapped pre-normalization (list capped at 20, regex anchored —
matches app-wide posture), and the use-case row itself not FOR
UPDATE-locked (same-org soft-delete race, low impact).

## Deploy

Standard VPS loop (`git pull` → compose build → `GIT_SHA=… up -d`) +
migration 033 applied to `scopewise_prod` + smoke (`/mitre` 200, API
401 unauth). Prod at `6ce8e48`.

## Next

Optional Phases 11–13 remain build-on-request (kickoff prompt:
`docs/phases/prompts/MITRE_OPTIONAL_FEATURES_PROMPT.md`). Phase 13 is
design-first (brainstorming session before any code).

## Agent utilization

- Opus (Fable, main): recon, full implementation (backend + frontend + tests), docs, deploy — self-executed (files hot in cache, security-adjacent Tier 0 path)
- Sonnet: adversarial sign-off of the Phase 10 diff · verdict=ACCEPT · reworked: N
- Haiku: n/a — no bulk sweeps needed this session
- codex:rescue: n/a — companion outage (2026-07-23 memory); Sonnet takeover per standing fallback
