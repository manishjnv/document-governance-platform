# Session handoff — 2026-09-12 — Run-entitlement gate + pricing unlink

**Headline:** free-tier organisations can now upload documents, create MITRE
assessments and use the column wizard, but cannot start a review or an
assessment; they see a request-access form instead. `/pricing` is kept but
unlinked and unindexed. Both changes committed locally, **not pushed, not
deployed**.

## Commits (this session)

| SHA | What |
|---|---|
| `329d10b` | Run-entitlement gate (api + web + tests) |
| `a6a5bdb` | Marketing: unlink and noindex `/pricing` |
| (this commit) | Docs: this handoff, progress entry, plan amendment |

Earlier in the same calendar day, other sessions landed the homepage
branding build, content phase, CWV/templates, deploy, scopesense.in runbook
and the severity-calibration scripts; see their own handoffs in this folder.

## 1. Why

The ScopeWise OpenRouter key hit its per-key limit (see memory
`openrouter-key-identity` and `SESSION_HANDOFF_2026_09_12_*` for the
calibration block). Every signed-in user could start LLM-spending runs, and
sign-up is open (Google or email OTP auto-provisions an org). The owner
asked that only approved organisations may run, that everyone else can still
see how intake works, and that the run action be replaced by a contact form.

## 2. Design

- **Entitlement source:** the existing `organizations.subscription_tier`
  column (`free | pro | enterprise`, default `free` on sign-up, CHECK
  constraint in `app/models/organization.py`). It was never enforced anywhere
  and no API writes it (the `OrganizationUpdate` schema carries the field but
  no router uses it). No migration, no new table, no flag framework.
- **Rule:** `runs_enabled(subscription_tier, email)` in
  `apps/api/app/entitlements.py` returns True when
  `settings.require_paid_tier_for_runs` is False, or the email is in
  `settings.platform_admin_emails`, or the tier is `pro`/`enterprise`.
  Email comes only from the signed JWT (`TokenData.email`); there is no
  endpoint that changes a user's email.
- **Dependency:** `require_runs_enabled` loads the org tier and raises
  `403` with `RUNS_DISABLED_DETAIL` (a human-readable sentence that the
  existing frontend error paths already render). Missing org or DB error
  fails closed.
- **Gated surfaces (the only LLM-spending entry points):**
  - `POST /api/v1/reviews/{doc_id}/trigger` (`app/routers/reviews.py`)
  - `POST /api/v1/documents/bulk-review` (`app/routers/documents_bulk.py`)
  - `POST /api/v1/mitre/assessments/{id}/run` (`app/mitre/router.py`)
  - Celery scheduled SIEM pull (`app/mitre/tasks.py::_run_scheduled_pull_async`):
    checked right after the connection lookup, before secret decryption and
    before any pipeline call. A disabled org gets a `status='failed'`
    assessment row carrying the same message (plan §2.6 says failed pulls
    must be visible) and the task returns `{"status": "skipped", "reason":
    "runs_disabled"}`.
- **Deliberately not gated:** document upload, MITRE assessment creation
  (`POST /assessments`, `/from-siem`, `/from-connection`), the remap wizard
  (re-parses the stored file only), connections CRUD, and the whole Code
  Security Review module (no LLM; the consultant's scan runs on their own
  key).
- **Current-user payload:** `GET /api/v1/auth/me` now returns
  `assessments_enabled: bool` (`app/schemas/auth.py`), computed with the same
  function, so the UI and the API can never disagree.
- **Settings:** `require_paid_tier_for_runs: bool = True` in
  `app/config.py`. `tests/conftest.py` sets the env var to `false` **before**
  `import app.config` (the Settings singleton is built at import; putting the
  line after the import silently did nothing and failed 12 tests until moved).
  45 test files create free-tier orgs and would otherwise all 403.

## 3. Frontend

- `apps/web/components/RequestAccessForm.tsx` (new): name, work email,
  hidden honeypot, posts `{name, email, message, source}` to
  `/api/v1/contact` (the endpoint already accepts `source` up to 50 chars).
  Copied from the templates gate so styling and focus rings match.
- `apps/web/app/mitre/new/page.tsx`: fetches `/auth/me` on mount; when
  `assessments_enabled === false` the Run button is replaced by the form
  (`source=assessment_request`, message includes the assessment id). Back
  button and "keep it for later" line unchanged. `handleRun` also
  early-returns as defence in depth. Unknown/undefined is treated as enabled
  so an older API cannot lock the UI.
- `apps/web/app/dashboard/page.tsx`: same flag read from the existing
  `/auth/me` call; `handleReview` opens a `Dialog` hosting the form
  (`source=review_request`) instead of posting. Table component untouched.

## 4. Verification

| Check | Result |
|---|---|
| `tests/test_run_entitlement.py` (6 cases) + `test_review_trigger_guard.py` + `test_mitre_schedule.py` | 20 passed |
| Implementer's wider run: `test_mitre_api.py`, `test_review_trigger_guard.py`, `test_bulk_review.py`, `test_admin_config.py` + new file | 48 passed |
| `cd apps/web && npx tsc --noEmit` | clean (after gate and after pricing change) |
| Secrets / TODO gate on the staged diff | clean |
| Adversarial review (Sonnet takeover, codex companion broken) | **accept**; 7 vectors checked, none exploitable |
| Email-change route that could reach the admin carve-out | none exists |

Full suite was **not** run (shared `edgp_test` was in use by another session
part of the day; single-runner rule). Baseline remains 973 / 7 until someone
runs it solo.

## 5. Pricing unlink (`a6a5bdb`)

Owner reversed the branding-plan decision: pricing is quote-only and must not
be discoverable on prod. Page kept at `/pricing` for direct sharing.
Removed from `MarketingNav` (desktop + mobile, `NAV_LINKS` now empty with a
comment), `MarketingFooter` Products column, `sitemap.ts`; added to
`robots.ts` disallow; page metadata `robots: {index:false, follow:false}`.
Seven inline "pricing" links (homepage, three product pages, two solution
pages, the compare page) now point at `/contact`.
`HOMEPAGE_BRANDING_SEO_PLAN.md` context line and §7 step 5 amended.

## 6. Operations to do before / at deploy

1. **Prod DB:** every organisation that should keep running needs
   `UPDATE organizations SET subscription_tier='pro' WHERE org_id=...`.
   The owner's own account bypasses by email. Until this is done, all other
   prod orgs will see the request form. No migration to apply.
2. **Enable-on-request flow** is manual: requests arrive via the contact
   endpoint with `source` `assessment_request` or `review_request`; enabling
   is the SQL above. An admin-page toggle is a small follow-up if wanted
   (`admin_extra.py` has a GET for the tier; add a platform-admin-only PATCH).
3. Deploy is the standard loop in `CLAUDE.md`; frontend + api both changed.
4. Known trade-off: a free org with a scheduled SIEM pull records one failed
   assessment per scheduled run (visible by design). Change
   `_run_scheduled_pull_async` to skip silently if that proves noisy.

## 7. Not from this session, left uncommitted on purpose

Another session's in-progress Code Security Review work was in the tree and
was **not** staged: `apps/api/app/codereview/report_xlsx.py`,
`apps/api/tests/test_codereview_report.py`,
`apps/web/app/codereview/[reviewId]/components/FindingDrawer.tsx`, new
`apps/api/app/codereview/highlight_words.json`,
`apps/web/app/codereview/[reviewId]/components/highlightWords.ts`,
`scripts/generate_highlight_words.py` (keyword-highlight word lists moved to
a single JSON source). Whoever owns that should finish and commit it.

## 8. Pending from the day's original plan

- Blog posts for MITRE and Code Review (plan §7 step 7) — four posts exist as
  `pendingReview: true`; owner read-through then flip the flag.
- `/compare/[competitor]` pages — legal sign-off first.
- Product screenshots on the landing pages, per-pillar OG images, `/about`
  name-rationale paragraph.
- Severity calibration harvest — blocked on the OpenRouter key limit; scripts
  committed (`fbbdf9e`).
- Sentinel workbook first live test — needs a workspace from the owner.
- Push + deploy of everything since the last deploy, then the prod tier
  update above.

## Agent utilization

- Opus: seam design, diff critique of both implementers, verification, docs.
- Sonnet: backend gate (reworked: N) · frontend request-access form (reworked: N) · adversarial takeover (verdict accept).
- Haiku: n/a — no bulk sweeps needed.
- codex:rescue: n/a — companion MCP broken (memory 2026-07-23); Sonnet takeover used, verdict=accept.
