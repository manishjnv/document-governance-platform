# Session handoff — MITRE Phase 11: threat-informed gap weighting (2026-08-02)

**Headline:** Phase 11 (fourth optional MITRE feature, plan §14) built
fully deterministically, tested, signed off (ACCEPT), committed as
`62f1df2`, pushed, and deployed to prod (no migration). Suite **713
passed / 7 skipped** (solo, shared `edgp_test`); `tsc --noEmit` clean.

## What shipped

Gap ranking now understands *who is likely to attack this customer*:

- **`app/mitre/data/threat_profiles.json`** (the curation-heavy piece):
  10 industry profiles keyed to the wizard's exact INDUSTRIES values
  (banking/insurance alias to financial services) and 10 named actor
  profiles with ATT&CK G-codes. 143 technique IDs, all machine-validated
  to resolve `ok` against the pinned v19.1 `attack.json` — a validator
  script ran during curation and `test_mitre_threat_profile.py` enforces
  it forever (catches ATT&CK-version drift). Sources cited in-file.
- **`ranking.build_threat_profile(industry, actors)`** — pure lookup;
  unknown industry/actor is a silent no-op (curated, never guessed).
  Exact-ID matching only (a profile listing T1566.001 lifts that
  sub-technique, not its parent — documented choice).
- **The weight:** one new sort key in `rank_gaps`, immediately after
  tier: profile-relevant gaps rank above equal-tier peers, never jump a
  tier, and coverage %/states are untouched by construction (ranking is
  strictly downstream of coverage). Gaps carry `threat_relevance`
  labels; toggle off → ordering reverts, annotation stays (provenance).
- **Org tunable** `threat_weighting_enabled` (default on) via the
  existing `mitre_settings` pattern; stamped into `params.thresholds` at
  run time, and the Phase 10 manual-edit recompute honors the stamped
  value + rebuilds the same profile from `params.intake`.
- **Intake/UI:** optional `threat_actors` multi-select in `/mitre/new`
  (chips fed by new `GET /threat-catalog`; server validates against the
  catalog — unknown names 422, deduped, max 10). Gap rows show a violet
  "Threat match" chip; tooltip names the matching industry/actors and
  states it affects ordering only. An assumption line records the active
  profile; the narrative's top-gaps JSON includes the labels.

## Verification

- Full suite **713 passed / 7 skipped** (solo-confirmed before running;
  one legitimate baseline fix: the settings round-trip test's exact
  defaults dict gained the 5th key).
- Golden before/after demo (real dataset, Healthcare profile): profile
  techniques rose within their tiers (e.g. T1003.001 #6→#4, T1486
  #8→#6; T1133/T1567.002/T1490 lead tier 2); tier-4 stayed last. No
  coverage number changed.
- **Sonnet light review: ACCEPT** — verified coverage-% invariance by
  construction, catalog-only strings reaching intake/narrative, no AI
  imports (guard test), recompute consistency incl. pre-Phase-11
  assessments defaulting the missing toggle to on, tier semantics, and
  React-escaped frontend. Its one cosmetic note (duplicate actors via
  raw API) was fixed in-session with a test assertion.

## Deploy

Standard VPS loop; **no migration** this phase. Prod at `62f1df2`;
smoke: `/mitre` 200, API 401 unauth, `/threat-catalog` auth-gated.

## Next

Remaining optional: Phase 12 (detection-quality scoring), Phase 13
(SIEM pull — design-first via brainstorming). Build only on request.

## Agent utilization

- Opus (Fable, main): recon, curation, implementation, docs, deploy — self-executed (hot cache; curation needs judgment against real dataset)
- Sonnet: light adversarial review of the Phase 11 diff · verdict=ACCEPT · reworked: N (one cosmetic note applied)
- Haiku: n/a — no bulk sweeps needed
- codex:rescue: n/a — companion outage; Sonnet takeover per standing fallback
