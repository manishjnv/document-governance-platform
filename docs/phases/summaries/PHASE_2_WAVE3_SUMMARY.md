# EDGP Phase 2 — Wave 3: Test Stabilization, Customization Wiring, Cleanup

**Status:** Phase 2 fully complete. Full `apps/api` suite: **334 passed, 0 failed, 0 errors.**
**Follow-on to:** `PHASE_2_WAVE2_SUMMARY.md` (Wave 2 left ~74 known test failures and an unwired customization system — both closed out here).
**Next:** Start Phase 3 per `docs/phases/prompts/PHASE_3_PROMPT.md`. Nothing blocking.

---

## What this session did

1. **Fixed a real event-loop bug breaking most DB-backed tests.** `pytest-asyncio` 1.x creates a new event loop per test function by default, but `tests/conftest.py`'s `test_engine` fixture was session-scoped — its asyncpg connection pool bound to test #1's loop, which closed right after, cascading into `RuntimeError: Event loop is closed` / `asyncpg.exceptions.InterfaceError` across the suite. Fixed via `asyncio_default_test_loop_scope = session` / `asyncio_default_fixture_loop_scope = session` in `pytest.ini`, and removed the now-dead (pytest-asyncio 1.x silently ignores it) custom `event_loop` fixture.
2. **Wired org customization into the review pipeline** (`app/admin/customization.py` — T-2091/2092/2093 rule/agent/scoring config was persisted but never read anywhere). Both `app/routers/reviews.py::trigger_review` and `app/routers/documents_bulk.py::bulk_trigger_review` now fetch per-org config once per request/batch and pass it into `ReviewOrchestrator.review()` (agent/rule filtering) and `DocumentScorer` (weight overrides). Rules/agents stay shared global singletons; org customization applies per-call, never by mutating shared state.
3. **Fixed the ~74 known Wave 2 test failures** plus several more that surfaced once the event-loop bug was gone — six parallel Sonnet subagents (test_admin/_extra, test_admin_ops, test_search_history/test_teams, test_approvals/test_approval_extras/test_audit, test_bulk_review, test_knowledge_base) plus direct fixes for test_compliance.py, test_predictions.py, test_insights_extra.py, test_admin_ops.py. Root causes: sync `TestClient` vs the session-scoped event loop (converted to `httpx.AsyncClient`+`ASGITransport`, matching `test_auth.py`'s pattern), fabricated FK references with no real parent row inserted, missing NOT NULL / CHECK-constraint columns in test fixtures, a broken hand-rolled JWT fixture, and a couple of real app bugs (see below).
4. **Fixed the 3 explicitly-deferred, pre-existing Phase 1 bugs** in `test_rules.py`/`test_scoring.py` (flagged out-of-scope since Wave 1): two were test bugs; the real one was `DocumentScorer` never actually reading a finding's `severity` field, scoring purely by keyword-matching description text — 5 findings explicitly marked "critical" but genericly worded could score a perfect 100.
5. **Removed dead `Settings.cors_origins`/`allowed_hosts`** — nothing read them (`main.py` drives both via raw `os.getenv()`), and they were a live foot-gun (pydantic-settings tries to `json.loads()` list-typed fields from env vars, forcing a fragile import-order workaround in `conftest.py` that's now simplified).

## Real application bugs fixed along the way (not just test issues)

- `ApprovalTemplate.approver_user_ids` (plain JSONB) couldn't round-trip `UUID` objects — added a `UUIDListJSONB` TypeDecorator.
- `detect_score_anomalies()` treated a zero-variance historical baseline (all scores identical, stdev=0) as "never an anomaly" regardless of how far the target score was — floored stdev at 2.0 score-points.
- `app/admin/user_lifecycle.py::bulk_import_users` compared `csv.DictReader.fieldnames` (a list) against a tuple literal — always `!=`, so every bulk import silently created zero users.
- `app/routers/documents_bulk.py`: missing `completed_at` on `status="completed"` (violates `ck_reviews_completed_has_timestamp`), which triggered a rollback that expired other in-flight `Document` objects in the same batch, crashing the next iteration on lazy-attribute access outside a greenlet context. Also added defensive UUID parsing so one malformed doc_id doesn't 500 the whole batch.
- `Organization.audit_retention_days` existed in the DB (raw SQL migration) but not the ORM model.
- `migrations/018_fix_search_history_updated_at.sql`: `search_history`/`saved_searches` were missing `updated_at`, which their `TimestampMixin` requires.

## Incident: a subagent ran `git stash` mid-session

One of the six parallel Sonnet subagents ran `git stash` to A/B-test its fix against the unfixed baseline. None of the subagents were sandboxed in isolated git worktrees, so this wiped every other subagent's (and the orchestrator's) uncommitted work across the whole shared working directory. Caught via a system alert about files reverting to pre-edit state; diagnosed via `git reflog` (`reset: moving to HEAD`); recovered by re-applying all lost edits from conversation context and re-verifying before committing. No work was permanently lost, but it cost a recovery detour.

**Lesson for future sessions:** if dispatching parallel subagents that write code in this repo, either (a) explicitly instruct them never to run `git stash`/`reset --hard`/`checkout --`/`clean`, even for their own before/after testing, or (b) give write-touching agents `isolation: "worktree"` so they can't collide with concurrent work.

## Verification

Full suite run twice consecutively, clean: `cd apps/api && python -m pytest -q` → **334 passed, 0 failed, 0 errors**, ~190-210s.

## Commits this session

- `ea11e1e` Fix Phase 1 auth UUID/int mismatch and bcrypt/passlib version drift
- `cb2b598` Phase 2 Wave 2: Advanced Features (T-2001-T-2100)
- `b92451d` Wire org customization into review pipeline; fix bulk-import CSV bug
- `1f407ed` Fix remaining Phase 2 test failures: FK gaps, check constraints, anomaly bug
- `4c9197c` Fix the 3 leftover Phase 1/2 items: scoring severity, bulk-review wiring, dead config

## Open items (non-blocking)

- `apps/web/app/(search)/` and `apps/web/components/` are untracked, uncommitted frontend directories of unknown origin/status — not touched this session, flagged for whoever owns frontend work to review.
- `docs/phases/prompts/PHASE_3_PROMPT.md` was edited (not by this session) to mark the Mobile App tasks (T-3041-T-3060) as deferred in favor of the PWA track — worth confirming that's an intentional, accepted decision before Phase 3 kicks off.

---

## Agent-utilization footer

- **Opus (main session):** architecture/judgment work — root-caused the event-loop bug via a minimal repro script, designed the org-customization wiring (orchestrator/rule-engine/scorer signature changes), diagnosed and redesigned the severity-blind scoring algorithm, recovered from the git-stash incident.
- **Sonnet (6 parallel subagents):** test-fixing sweep across test_admin/_extra, test_admin_ops, test_search_history/test_teams, test_approvals/test_approval_extras/test_audit, test_bulk_review, test_knowledge_base. Reworked: Y for 3 of 6 (stuck in self-spawned background-polling loops needing a resume nudge to produce a final report) — not a fix-quality issue, a background-task-discipline issue.
- **Haiku:** n/a — not used this session.
- **codex:rescue:** n/a — no security/auth/classifier-adjacent diff this session; the auth UUID fix was carried over from a prior session's work, not newly authored here.
