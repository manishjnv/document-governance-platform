# EDGP Phase 3: Performance, Scale & PWA — Summary

**Status:** Complete (trimmed scope). Full `apps/api` suite: **347 passed, 0 failed, 0 errors.** Frontend `tsc --noEmit`: 4 pre-existing errors, 0 new.
**Follow-on to:** `PHASE_2_WAVE3_SUMMARY.md`.
**Scope changes from `PHASE_3_PROMPT.md`:** Mobile app (T-3041-3060) deferred to PWA (pre-existing decision). i18n (T-3086-3095, 3098-3100) dropped entirely — no compliance/non-English need. Accessibility trimmed to a bare-minimum pass (T-3076-3080, 3082-3085, 3096); T-3081 (manual screen-reader testing) dropped as untestable in-session. Pure infra/vendor tasks with no code artifact in this repo (Kubernetes Ingress, Grafana, PgBouncer, DB read replicas, App/Play Store submission, ELK, CDN vendor setup) were treated as out of scope rather than faked — noted here, not implemented.

## What this session did

Three waves of parallel Sonnet subagents, reviewed and verified between each:

**Wave 1 — Performance (T-3001-3003, 3005-3008, 3010, 3016, 3019):**
- `migrations/019_performance_indexes.sql` — indexes on `documents(org_id, created_at)`, `findings(org_id, severity)`, `reviews(completed_at)` (checked existing migrations first to avoid duplicates).
- DB pool size/max_overflow/recycle made configurable via `app/config.py` (was hardcoded).
- 2 real N+1 fixes: bulk CSV user import doing a per-row `SELECT` (now a single prefetch), an approval-template apply loop doing per-approver `db.refresh()` (now one batched `SELECT ... IN`).
- `app/core/pagination.py` — offset-based pagination helper, applied to 3 previously-unbounded list endpoints.
- `GZipMiddleware`, `X-Response-Time-Ms` timing middleware, `GET /documents/batch?ids=...`.
- `app/core/cache.py` — fail-open Redis caching layer (never raises if Redis is down), applied to 3 analytics endpoints with `Cache-Control`/`ETag`, invalidated on document upload / review completion.

**Wave 2 — Scalability + PWA (T-3026-3029, 3061-3069, 3073):**
- `app/core/celery_app.py` + `app/tasks/document_tasks.py` — new `generate_pdf_report_task` (out-of-band PDF report generation; existing synchronous parse/report endpoints were left untouched since their response bodies are load-bearing for existing tests).
- `app/core/rate_limit.py` — in-memory token-bucket middleware, keyed by user id else IP, 429 + `Retry-After`.
- `app/core/circuit_breaker.py` — wraps the real Claude API call site in `app/insights/ai_insights.py` (closed/open/half-open, 5-failure threshold, 30s reset).
- PWA: `manifest.json`, `service-worker.js` (cache-first static, network-first API), install-prompt banner, update-available banner, IndexedDB offline doc cache + offline-action queue with online-event sync, online/offline status badge. No new npm dependency — native browser APIs only.

**Wave 3 — Accessibility (trimmed) (T-3076-3080, 3082-3085, 3096):**
- Skip link + `<main id="main-content">` landmark.
- ARIA labels/roles across error banners, status banners, custom clickable divs (keyboard handlers added), progress bar, chart wrapper.
- Form label/id association fixed on 3 pages.
- 1 contrast failure found and fixed (`--destructive` 4.47:1 → 4.60:1 against white).
- `Dialog`/`Sheet` (Radix) audited — installed but unused anywhere yet, focus trap intact for whenever adopted.
- `jest-axe` added + `tests/accessibility.test.tsx` written, but **could not run** — repo has no jest config/test script/`@testing-library/react` at all. Documented as a gap, not faked as passing; `tests/` excluded from `tsc` so the unrunnable file doesn't count as a new type error.
- Full report: `docs/phases/summaries/PHASE_3_ACCESSIBILITY_AUDIT.md`.

## Real bugs found and fixed along the way

- **Celery task event-loop bug**: `generate_pdf_report_task` called `asyncio.run()` but reused the app-wide shared async engine, which binds to whatever event loop first touched it. Second call in the same process → `RuntimeError: ... attached to a different loop` — the same bug class as the Phase 2 Wave 3 event-loop incident. Fixed by giving the task its own short-lived engine, disposed after each call.
- **`.gitignore` silently excluding `apps/web/lib/`**: the root `.gitignore`'s Python-venv `lib/` pattern was unanchored, matching any `lib/` directory anywhere in the repo. This had been silently blocking `apps/web/lib/utils.ts` (the shadcn `cn()` helper) and `exportCsv.ts` from ever being committed since they were created. Anchored to `/lib/` and `/lib64/` (repo-root Python build artifacts only); both files are now tracked.
- **Dead, unwired `RateLimitMiddleware` sketch** found in `app/dependencies.py` during Wave 2 — never mounted, now fully superseded by `app/core/rate_limit.py`. Flagged for cleanup, not removed this session (out of scope for the agent that found it).

## Process notes

- **Shared test-DB contention**: running 3 agents' full `pytest -q` concurrently against the same `edgp_test` Postgres DB in Wave 1 caused real lock contention on `TRUNCATE TABLE organizations CASCADE` (test fixtures reset state between tests) — agents ended up manually `pg_terminate_backend()`-ing each other's stuck connections to unblock themselves. From Wave 2 onward, agents were instructed to only run their own touched test files, with the orchestrator running the full suite once, serially, after each wave. No test-DB deadlocks recurred.
- All 3 subagents in Wave 1 initially returned a "waiting for background pytest" placeholder instead of a final report — required explicit resume nudges to force a synchronous finish (matches the background-polling-loop pattern noted in `PHASE_2_WAVE3_SUMMARY.md`).
- Mid-session, unrelated uncommitted edits to `docs/phases/prompts/PHASE_4_PROMPT.md` through `PHASE_7_PROMPT.md` (scope-trimming decisions for those future phases) appeared in the working tree, made by none of this session's agents. Left uncommitted and unstaged — flagged to the user, not touched.

## Commits this session

- `0439fd6` Phase 3 Wave 1: DB indexes/pool tuning, N+1 fixes, pagination, compression, response timing, batch endpoint, Redis caching
- `c43ac99` Phase 3 Wave 2: Celery task queue, rate limiting, circuit breaker, PWA; fix event-loop bug; fix `.gitignore` blocking `apps/web/lib/`
- `fec8de3` Phase 3 Wave 3: trimmed accessibility pass

## Verification

Full `apps/api` suite run after each wave and once more at the end: `python -m pytest -q` → **347 passed, 0 failed, 0 errors**, ~240s. `apps/web`: `npx tsc --noEmit` → 4 pre-existing errors (unrelated files), 0 new, after every wave.

## Open items (non-blocking)

- `docs/phases/prompts/PHASE_4_PROMPT.md`–`PHASE_7_PROMPT.md` have uncommitted scope-trimming edits from an unknown source (not this session's agents) — needs the user's attention before those phases start.
- `apps/web` has no jest/testing-library setup at all — `tests/accessibility.test.tsx` exists but cannot run until that infra is added (separate decision, out of this session's trimmed scope).
- Dead `RateLimitMiddleware` in `app/dependencies.py` (Wave 2 finding) should be deleted — fully superseded by `app/core/rate_limit.py`.
- Skipped as out-of-scope (no code artifact in this repo, would have been faked): Kubernetes Ingress, PgBouncer, DB read replicas/partitioning, Grafana/ELK/Prometheus vendor wiring, CDN setup, App/Play Store submission.

---

## Agent-utilization footer

- **Opus (main session):** scope plan, reviewed every subagent diff before commit, ran independent full-suite/typecheck verification after each wave (not trusting subagent-reported results), diagnosed and fixed the Celery event-loop bug directly (≤30 lines, already-open file), diagnosed and fixed the `.gitignore` bug directly, resolved the Wave-1 shared-test-DB contention by changing Wave 2+ agent instructions, flagged the unattributed Phase 4-7 doc edits rather than committing them.
- **Sonnet (8 parallel/serial subagents across 3 waves):** all implementation. Reworked: Y for all 3 Wave 1 agents (stuck reporting "waiting for background pytest" instead of a final result — needed an explicit resume nudge to force synchronous completion; matches the background-polling pattern from Phase 2 Wave 3, not a fix-quality issue). Wave 2/3 agents (4 total): reworked: N — clean single-pass reports, though the Celery agent's actual code had the event-loop bug caught in Opus review, not self-caught.
- **Haiku:** n/a — not used this session; grep/verification work stayed small enough for the Sonnet agents themselves or direct Opus commands.
- **codex:rescue:** n/a — no security/auth/classifier-adjacent diff this session (rate limiting and circuit breaker are resilience/availability, not auth; reviewed directly instead).
