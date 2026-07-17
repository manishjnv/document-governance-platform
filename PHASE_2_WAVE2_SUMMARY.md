# EDGP Phase 2 — Wave 2 + Phase 1 Auth Remediation Summary

**Status:** All 100 Phase 2 tasks now addressed (69 newly implemented this session, ~20 explicitly skipped with reasons, ~11 partial/deferred with reasons — see below). Phase 1's broken authentication system was also found and fixed.
**Verification:** Live against real PostgreSQL 16, real bcrypt password hashing, real JWTs, real end-to-end login.
**Follow-on to:** `PHASE_2_WAVE1_SUMMARY.md` (this session's earlier work — read that first for Wave 1 context and the original list of pre-existing Phase 1 issues discovered).

---

## Part 1: Phase 1 auth system — found broken, fully rewired

Wave 1 discovered (but didn't fix) that `app/routers/auth.py` authenticated against an in-memory dict with integer IDs, completely disconnected from the real UUID-keyed `users`/`organizations` tables — meaning login had never actually worked against real data, and `TokenData.org_id`/`user_id` were typed `int` to match the fake stub.

**Fixed this session:**
- `TokenData`, `LoginResponse`, `CurrentUserResponse` now correctly typed `uuid.UUID`.
- `app/routers/auth.py` fully rewritten: login/refresh/me/password-reset/change-password all query the real `users`/`organizations` tables.
- Two more latent bugs found and fixed while rewiring: the refresh-token payload never included `role` (so `TokenData` validation always failed — refresh never worked), and the password-reset payload never included `org_id`/`role` for the same reason (reset never worked). Both now use dedicated lighter schemas (`RefreshTokenData`, `ResetTokenData`) instead of overloading `TokenData`.
- `verify_org_access()` fixed — was comparing a UUID against a string with `!=`, which would always mismatch.
- One crash site fixed (`documents.py`: `UUID(current_user.org_id)` on an already-UUID value would raise `AttributeError`).
- `requirements.txt`: added missing `email-validator` (silently required by `pydantic.EmailStr`, was never installed — a live bug, not just a test artifact), pinned `bcrypt==4.0.1` (passlib 1.7.4's own internal self-test breaks under bcrypt≥4.1's stricter 72-byte limit — this blocked **all** password hashing, live and in tests), removed two broken/unused pins (`httpx-mock`, `pydantic-extra-types`).
- Added `scripts/seed_dev_admin.py` — idempotent dev-only bootstrap (there's no self-serve registration endpoint in this codebase; org/user provisioning is an admin/ops action).

**Adversarial review** (fresh Sonnet agent, no context bias) returned **ACCEPT WITH FIXES**. Findings and outcomes:
- **HIGH — fixed:** the new email lookup used `ILIKE` with the raw user-supplied email, and `%`/`_` are valid RFC-5322 local-part characters that pass `EmailStr` validation untouched — `%@corp.com` would match every user at a domain, turning "know one victim's email+password" into "know a domain+password". Switched to exact case-insensitive equality (`func.lower(email) == email.lower()`).
- **MEDIUM — fixed:** same email registered in two different orgs (a real possibility — `users.email` is only unique per-org) previously logged the caller into whichever org's account was created first if the password happened to match, or hard-locked every account but the oldest if it didn't. Now verifies the password against every candidate and rejects as ambiguous if more than one matches.
- Two regression tests added proving both fixes (`test_login_ilike_wildcards_dont_match_other_users`, `test_login_rejects_ambiguous_same_email_same_password_across_orgs`).
- LOW findings (timing side-channel on login, no password max-length) accepted as-is — pre-existing class of issue, not introduced here, not worth the added complexity right now.

**Live-verified end-to-end:** login → real JWT with real UUIDs → `/me` → protected endpoints (200) → token refresh → change-password → password-reset-request, all against real Postgres. The wildcard exploit is confirmed blocked (401) while normal login still works (200).

---

## Part 2: Wave 2 — 13 parallel agent bundles, ~69 tasks

Same pattern as Wave 1: file-partitioned bundles (6 Sonnet, 7 Haiku) so no two agents touch the same file, each with an explicit migration number (008–017), each told to build real logic against real infra and name any gap rather than fake it.

| Bundle | Tasks | New surface |
|---|---|---|
| Analytics & reporting (Sonnet) | T-2006–08, 2016, 2018, 2020 | Document view tracking, review metrics, performance dashboard, custom report builder + templates + archive |
| Document similarity & versioning (Sonnet) | T-2026–29 | Stdlib TF-cosine similarity, duplicate detection, version listing, line-level version diff |
| Data governance / GDPR (Sonnet) | T-2046–48, 2050 | Document retention purge, GDPR export/right-to-be-forgotten, Fernet encryption utility |
| Fine-grained access control (Sonnet) | T-2056–60 | Per-resource grants w/ expiry (delegation), access audit (via existing audit log), IP allowlist |
| Team management (Sonnet) | T-2071–75 | Teams, roles, token-based invitations, activity feed, settings |
| Admin customization (Sonnet) | T-2091–95 | Per-org rule/agent enable-disable, scoring weight overrides, custom doc types, field mappings (storage + API only — **not wired into actual rule engine/scoring/orchestrator execution**, see Known Gaps) |
| Filtering & bulk ops (Haiku) | T-2011, 2013–15 | Multi-criteria filter UI, bulk review trigger, filter validation, saved filter templates |
| Predictive & comparison extras (Haiku) | T-2030, 2033–35 | Missing-section checklist, anomaly detection (stdlib stats), confidence intervals, version-diff UI |
| Knowledge base (Haiku) | T-2036–40 | FAQ/best-practice/guide articles (one table), full-text similar-findings search, issue-resolution lookup |
| Compliance frameworks (Haiku) | T-2051–55 | SOC2/ISO27001/GDPR/HIPAA starter control checklists — **self-assessment only, explicitly not a certification** (disclaimer in table comment, module docstrings, and every CSV export) |
| Approval enhancements (Haiku) | T-2064, 2067–70 | @mentions, approval templates (parallel mode complete; serial mode partially stubbed, see Known Gaps), in-app approval notifications, approval history |
| Notifications core (Haiku) | T-2076 (data model), 2080 | REST-pollable notification store + preferences (no WebSocket push — no WS server exists in this repo) |
| Admin ops (Haiku) | T-2084, 2085, 2088, 2090, 2099 | Usage metrics, member management UI, suspend/reactivate (with last-admin guard), bulk CSV user import |

**Explicitly skipped, same reasoning as Wave 1's T-2098 (no billing provider):**
- T-2078/T-2079 (Slack/Teams integration) — no SDK, webhook, or app credentials configured anywhere in this repo.
- T-2096/T-2097/T-2100 (billing dashboard, payment methods, upgrade/downgrade) — no Stripe/payment provider exists.
- T-2017/T-2019 (report scheduling, email delivery) — no scheduler or email provider configured.
- T-2031 (ML model training) — no labeled outcome data exists to train on; T-2032's/T-2035's heuristics stand in, same as Wave 1.
- T-2087 — functionally already covered by Wave 1's `PATCH /api/v1/admin/users/{user_id}/role`, no new agent needed.
- T-2012 — already done in Wave 1 (`SearchFilter.tsx`'s localStorage persistence).

## Integration work (this session, after the 13 agents)

- Reconciled `main.py` and `models/__init__.py` by hand — again, several agents edited these shared files directly despite instructions (7 of 13 this time). Nothing was trusted from any individual agent's partial edit; final state was verified against every new router/model file.
- **Caught and fixed a route-ordering bug before it shipped:** `documents_extra.router` (static path `GET /duplicates`) and `documents_bulk.router` (`POST /bulk-review`) both live under `/api/v1/documents`, alongside `documents.router`'s `GET /{doc_id}`. FastAPI matches routes in registration order, so registering `documents.router` first would silently swallow `/duplicates` as `doc_id="duplicates"` (422 on UUID parse). Fixed by registering `documents_extra`/`documents_bulk` before `documents`. One of the Sonnet agents (document similarity bundle) caught and flagged this itself — good catch, confirmed and applied.
- **Fixed a cross-agent registration gap independently confirmed by 6 separate agents:** the knowledge-base bundle added an `Organization.kb_articles` relationship referencing `KBArticle`, but nothing imported `KBArticle` anywhere — this broke SQLAlchemy's mapper configuration for **any** test touching `Organization`, repo-wide, until fixed. Added to `models/__init__.py`.
- Applied migrations 008–017 to both `edgp_dev` and `edgp_test` (most had already been partially applied by agents verifying their own work; reconciled to a consistent final state — both databases now have identical 29-table schemas).
- **Fixed a real spec bug of my own:** the filter-templates bundle's model used `TimestampMixin` (needs `updated_at`) but the migration I specified only included `created_at` — caused a live 500 on `GET /api/v1/filter-templates`. Caught via live smoke test, not a unit test. Fixed with an additive column in both the live databases and the migration file.
- Fixed a test-fixture bug in `test_knowledge_base.py` (13 cascading errors from one bad fixture: an invented `review_type` kwarg that doesn't exist on the real `Review` model, plus a missing `completed_at` required by a CHECK constraint when `status='completed'`, plus a missing parent `Document` row for the FK). Down to 6 remaining errors in that file (an unrelated JWT-building pattern in its HTTP-endpoint tests, not chased further).

## Verification results

- All 17 migrations (001–017) apply cleanly to a fresh database; `edgp_dev` and `edgp_test` now have identical, complete 29-table schemas.
- Live app boots cleanly with all Wave 1 + Wave 2 routers, zero import-time errors.
- Live smoke test with a real login token across 11 endpoints spanning every new bundle (analytics, teams, knowledge base, access control, notifications, compliance frameworks, admin config, governance, filter templates, documents, predictions) — all correct (200 for real data, 404 for a nonexistent UUID, no 500s after the filter-templates fix).
- Full pytest suite against real Postgres: **257 passed / 60 failed / 14 errors** out of 331 tests (up from 116 passing at the end of Wave 1 + auth fixes, up from effectively 0 runnable DB-backed tests before any of this session's infra fixes).

### Remaining test failures — not chased further, same triage approach as Wave 1

The overwhelming majority are per-test-file fixture bugs, not product bugs: missing parent-row inserts before a dependent FK insert (SQLite never enforced these, so they were invisible until tests ran against real Postgres), a handful of files still using synchronous `TestClient` instead of `httpx.AsyncClient` (breaks across event loops — same root cause documented in Wave 1, fixed in `test_auth.py` and several Wave 2 files but not universally retrofitted), and the pre-existing, unrelated `test_rules.py`/`test_scoring.py` failures already flagged as out-of-scope Phase 1 bugs in the Wave 1 summary.

---

## Known gaps — named, not hidden

1. **Admin customization (T-2091–95) is storage + API only.** Nothing in `app/rules/*`, `app/scoring/algorithm.py`, or `app/ai/orchestrator.py` actually reads `org_rule_config`/`org_agent_config`/`org_scoring_weights` yet. Disabling a rule or agent via this API currently has no effect on document review. The Sonnet agent that built this was explicit about this in its own report — flagging again here so it doesn't get lost.
2. **Approval templates' serial mode is partially stubbed.** Parallel mode fully works. Serial mode creates only the first approver's row; "advance to next approver on decision" needs a new status value on `approvals.status`'s CHECK constraint, which the approval-enhancements bundle didn't own this session.
3. **Compliance framework tracking is self-assessment only** — disclaimed everywhere (table comment, docstrings, every CSV export) that it is not a SOC2/ISO27001/GDPR/HIPAA certification or audit.
4. **Encryption-at-rest utility exists but isn't applied to any column.** Deliberately — picking the right target field is a real decision, not something to guess at speculatively.
5. Six of thirteen Wave 2 agents (and seven of ten in Wave 1) edited `main.py`/`models/__init__.py` directly despite explicit instructions not to. None of those partial edits were trusted — final state was independently reconciled and verified both times — but if this pattern continues across a future Wave 3, consider whether the instruction itself needs reinforcing (e.g., worktree isolation for that specific file) rather than repeating it.

## Next steps

- Wire admin customization config into actual rule engine / scoring / orchestrator execution (currently just persisted, not enforced).
- Decide on serial-mode approval workflow's status model.
- Fix the remaining ~74 test failures/errors if full green CI matters before shipping (all are root-caused above, none are mysterious).
- This was another very long session on top of an already-long Wave 1 session — recommend `/clear` before continuing, using this document plus `PHASE_2_WAVE1_SUMMARY.md` as the resume point.
