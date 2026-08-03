# Session handoff — MITRE A12: scope auto-trend to the same customer (2026-08-03)

## Headline

Fixed the real prod bug where the report's "Trend vs your previous run"
block compared assessments across different customers (observed live:
"▼ 7.4 points vs 'Acme MITRE Assessment' … applicability changed: 292" —
a diff against a different customer's environment). Trend auto-pick is
now scoped to the same customer via an optional `params.customer` key —
migration-free. Implemented by a parallel build session, independently
verified and deploy-confirmed by this session.

## What happened (two cooperating sessions)

1. **This session (orchestrator):** diagnosed the bug from the user's
   screenshot — the Phase 14e trend query in
   `apps/api/app/mitre/router.py` filtered only on `org_id`, and
   `mitre_assessments` had no customer/project field. Wrote the A12
   kickoff prompt into `docs/planning/MITRE_ACCURACY_IMPROVEMENT_PLAN.md`
   (commit `091ba26`), then scheduled a timed verification pass while a
   second session implemented.
2. **Build session:** implemented A12, ran suite + tsc, deployed to the
   VPS (commit `7405723`).
3. **This session (verification, per the standing lesson to re-verify
   self-reviewed build sessions):** all checks below passed — ACCEPTED.

## The A12 change (commit `7405723`)

All storage rides the existing `params` JSONB — **no migration, no new
columns** (5-point migration checklist not triggered).

- `_sanitize_customer()` in `router.py`: trim + 200-char cap; empty →
  key omitted entirely (never stored as `''`).
- `POST /assessments` gains optional `customer` Form field, merged via
  the existing `extra_params` seam (router.py ~407).
- Wizard (`apps/web/app/mitre/new/page.tsx`): "Customer / engagement"
  input on the upload path; Sentinel path shows an "auto-set from your
  connection" note instead.
- Sentinel/SIEM: `_create_assessment_from_pull` auto-stamps
  `params.customer` from the saved connection name (preferred — stable
  across scheduled re-runs) or raw workspace. One seam covers all 3
  pull paths (token-at-trigger, saved-connection, scheduled worker).
- Trend query (router.py ~1853): added
  `params['customer'].astext IS NOT DISTINCT FROM <this run's customer>`
  — NULL matches NULL, so orgs that never set a customer keep exact
  pre-A12 behavior. No matching prior run → trend block omitted (already
  the behavior).
- List rows expose `customer`; list search/placeholder includes it.
- Explicitly unchanged: `/assessments/{id}/compare/{other_id}`
  (user-picked baseline) and the XLSX export — neither consumes the
  auto-pick (confirmed).
- Known tradeoff: pre-A12 assessments have no customer key, so the first
  post-A12 run for a named customer won't trend against pre-A12 runs
  (they only match NULL↔NULL). Self-heals as new runs accumulate.

## Independent verification (this session)

| Check | Result |
| --- | --- |
| Diff review vs A12 contract (all 5 spec points) | Pass |
| `extra_params` → `params` merge plumbing | Pass (router.py 407) |
| Sentinel stamping covers all 3 call sites | Pass (shared helper) |
| New tests: same-customer pick / cross-customer skip / NULL↔NULL match + sanitize/stamping (connections, siem) | Present (5 tests) |
| Full backend suite (solo on edgp_test, pg_stat_activity checked first) | **884 passed / 7 skipped** (baseline was 879/7; CLAUDE.md updated in `7405723`) |
| `npx tsc --noEmit` | Clean |
| VPS repo SHA | `7405723` |
| Containers (`scopewise-web/api/worker` rebuilt; redis/postgres untouched) | All healthy |
| `GIT_SHA` in scopewise-api env | `7405723` |
| Smoke: `/login`, `/api/v1/health` | 200 / 200 |

## Commits

- `091ba26` — A12 plan + kickoff prompt (also removed stale duplicate
  A11 status row).
- `7405723` — A12 implementation + tests + docs (CLAUDE.md baseline
  879→884, MODULE_REFERENCE §15, IMPLEMENTATION_PROGRESS, plan tick).
- (this commit) — session handoff doc.

## State

- Tests pass: **Y** (884/7, reproduced independently)
- Next action: none pending — A12 closed; live trend for "Acme MITRE
  Assessment" will show a same-customer baseline (or no trend block)
  once the customer field is populated on future runs.
- Open questions: none. Parked (pre-existing): "covered"→"has detection"
  relabel.

## Agent utilization

- Opus (Fable): diagnosis, A12 prompt authoring, scheduled wake-up
  verification, deploy confirmation, this handoff. n/a rework.
- Sonnet: n/a — implementation ran in a separate full session, not a
  subagent of this one.
- Haiku: n/a — single-target checks, no bulk sweeps needed.
- codex:rescue: n/a — not security/auth-adjacent (trend-baseline
  selection, org isolation unchanged); independent cross-session
  verification served as the second pass.
