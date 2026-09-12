# Kickoff prompt — 2026-09-12 wrap-up: finish, deploy, enable orgs, polish

Single session. Copy everything below the line into a fresh Claude Code
session at `E:\code\DocumentGovernancePlatform`. Sentinel workbook work is
deferred and must not be touched.

---

## Context to read first, in this order

`CLAUDE.md` (Git/deployment + VPS sections are binding);
`docs/phases/summaries/SESSION_HANDOFF_2026_09_12_ENTITLEMENT_PRICING.md`
(what the run-entitlement gate is, what it gates, the prod tier update it
needs, and the other session's uncommitted files); the two newest other
handoffs in `docs/phases/summaries/` dated 2026-09-12 (deploy state,
scopesense.in dual-domain run); `docs/planning/SCOPESENSE_DOMAIN_CUTOVER.md`
(the site runs on scopewise.assessiq.in and possibly scopesense.in; do not
hardcode either in new code); `docs/planning/HOMEPAGE_BRANDING_SEO_PLAN.md`
§2 (brand voice), §5 (only citable statistics), §7 (what is ticked and the
"also not done" line); `docs/planning/CODE_REVIEW_MODULE_REFERENCE.md` §0–§1
and §5; memory `openrouter-key-identity` (the ScopeWise key had a $2 per-key
limit and was exhausted; whether that is fixed is unknown to you: check).

State when you start: local master is several commits ahead of origin
(run-entitlement gate `329d10b`, pricing unlink `a6a5bdb`, docs `6e3aef6`,
plus earlier same-day commits). Nothing since the last deploy is on the VPS.
The working tree still holds another session's unfinished Code Security
Review "highlight words" change (listed in the handoff §7).

## Goal, in order. One commit per step. Push and deploy happen in step 3 only.

### Step 1 — Settle the foreign uncommitted work
Files: `apps/api/app/codereview/report_xlsx.py`,
`apps/api/tests/test_codereview_report.py`,
`apps/web/app/codereview/[reviewId]/components/FindingDrawer.tsx`,
`docs/planning/CODE_REVIEW_MODULE_REFERENCE.md`, new
`apps/api/app/codereview/highlight_words.json`,
`apps/web/app/codereview/[reviewId]/components/highlightWords.ts`,
`scripts/generate_highlight_words.py`. Read the diff. It moves the keyword
highlight word lists to one JSON source with a generator for the web mirror
(same pattern as `generate_prompt_docs.py`). If it is coherent: run
`python scripts/generate_highlight_words.py` and confirm the TS mirror is
byte-identical, run `tests/test_codereview_report.py` (check
`pg_stat_activity` on edgp_test first per the single-runner memory), `tsc`
clean, then commit it as "Code review: highlight word lists from a single
JSON source". If it is incomplete or broken, do not delete it: tell me what
is wrong and leave it uncommitted. Never `git stash`/`reset`/`checkout`.

### Step 2 — Admin toggle so enabling an org is not a SQL job
Backend: in `apps/api/app/routers/admin.py` (the platform-admin router that
already checks `settings.platform_admin_emails` inline at ~line 146; copy
that check, or extract a `require_platform_admin` dependency into
`app/dependencies.py` now that there is a second use) add
`PATCH /api/v1/admin/orgs/{org_id}/tier` with body `{"subscription_tier":
"free"|"pro"|"enterprise"}` validated by the existing `SubscriptionTier`
enum, writing `organizations.subscription_tier`, audited via
`log_action` (resource type `organization`; check the audit CHECK
constraint list in `app/models/audit_log.py` and migration files before
using a new value; if `organization` is not allowed, use whatever the
overview endpoint already logs with, do NOT add a migration). Also add
`GET /api/v1/admin/orgs` returning org_id, name, tier, user count,
created_at if no such list exists (grep `admin.py` and `admin_extra.py`
first; reuse). Non-platform-admins get 403; a platform admin cannot
downgrade their own org (return 400). Tests in `tests/test_admin_extra.py`
style: platform admin can set pro, org admin gets 403, invalid tier 422,
self-downgrade 400. Four tests, no matrix.
Frontend: `apps/web/app/admin/page.tsx` (platform admin page) gets an
"Organisations" table with a tier select per row calling the PATCH, using
the existing table and dropdown components in `components/ui`. Also list
the pending access requests: the contact endpoint stores nothing, so read
`apps/api/app/routers/contact.py` and, if messages are only emailed, add a
one-line note on the admin page "Requests arrive by email with source
assessment_request / review_request"; do not build storage.
`tsc` clean. Commit "Admin: organisation tier toggle for the run-entitlement gate".

### Step 3 — Push, deploy, prod tier update, smoke
I am authorising push and deploy in this session.
1. `git log origin/master..HEAD --oneline`; `cd apps/web && npx tsc --noEmit`
   and `next build`; grep the marketing tree for "EDGP" and "/pricing" links
   (only `robots.ts`, the page itself and the nav comment may mention it).
2. `git push` (email-privacy amend pattern from the global playbook if
   rejected; never `git config`).
3. Deploy per `CLAUDE.md`: ssh a11yos-vps, `/opt/scopewise`, pull, build,
   `GIT_SHA=... up -d`, scopewise-* containers only. Confirm no migration
   newer than 039 exists; if one does, stop and tell me.
4. In-container Python 3.11 compile smoke (memory
   `prod-python-311-fstring-gotcha`).
5. Prod tier update: list orgs from `scopewise_prod` (`select org_id, name,
   subscription_tier, created_at from organizations order by created_at`),
   show me the list and ASK which orgs to set to `pro` before running any
   UPDATE. My own org bypasses by email. Use the new admin endpoint or SQL,
   your choice, but show the exact statement first.
6. OpenRouter key: call `GET https://openrouter.ai/api/v1/auth/key` with the
   key from the VPS `.env` (read it on the VPS, never print it) and report
   `limit`, `limit_remaining`, `usage`. If `limit_remaining` is 0, say so
   plainly; reviews will fail until I raise it.
7. Smoke via a Haiku subagent, checkmark table: 200 + correct title on `/`,
   the three `/product/*` pages, `/compare/scopewise-vs-manual-review`,
   `/resources/blog` and the four newest posts, `/resources/templates`,
   `/privacy`, `/terms`; `/pricing` returns 200 with a noindex meta and is
   absent from `sitemap.xml`; `robots.txt` disallows `/pricing`, `/mitre`,
   `/codereview`, `/admin`, `/login`, `/api`; no header/footer link to
   pricing; a free-tier test account (create one via email OTP on prod if
   needed, then delete it or tell me) sees the request-access form on
   `/mitre/new` after upload and gets 403 from the run endpoint; the
   contact endpoint accepts `source=assessment_request`.
8. Give me the exact GSC steps to resubmit the sitemap (I click).

### Step 4 — Landing-page polish that was skipped
1. **Product screenshots.** Start the local stack (Docker, api, web), sign
   in as the platform admin, ingest `docs/sample/MITRE_Sample/UploadSample/
   acme_sentinel_usecases_v2.xlsx` + `acme_environment_v2.xlsx` and run one
   assessment; ingest the NodeGoat golden fixture under
   `docs/sample/CodeReview_Sample/real/nodegoat/` as a code review; run one
   SOW review on a public sample under `docs/sample/SOW_Sample/` (never
   anything under `docs/sample/project/`). Playwright screenshots at 1440px:
   SOW results page, MITRE tactic heatmap, code review findings drawer.
   Optimise to WebP under `apps/web/public/screens/`, each under 200 KB, and
   place one per product card on the homepage and one hero image per
   product landing page with descriptive alt text. If the OpenRouter key is
   still capped, the SOW and MITRE runs will fail: use the MITRE assessment
   with `quality_ai_enabled` off (deterministic tagging still produces the
   heatmap) and skip the SOW screenshot, saying so.
2. **Per-pillar OG images** (1200×630) generated by the same script that
   made `og-default.png` (find it in `scripts/` or `apps/web/scripts/`),
   set as `openGraph.images` on the three product pages.
3. **`/about`:** add the name-rationale paragraph from plan §2 ("Scope" =
   what is in and out of a contract, a detection estate, a codebase), keep
   the existing author decision (ScopeWise Team, Organization schema).
4. Lighthouse Performance/Accessibility/SEO on `/` and one product page
   after the images land; fix any regression from the images (sizes,
   `priority` only on the above-the-fold hero, lazy elsewhere).
Commit as two commits: screenshots + OG images; about paragraph. Do not
deploy again in this session unless I say so.

### Step 5 — Severity calibration harvest, only if the key allows
Read `docs/planning/severity_calibration/README.md`. If step 3.6 showed
`limit_remaining` > 2, run the documented harvest command
(`scripts/severity_calibration_run.py`) against the local stack with the
VPS key injected per-process (never written to a local `.env`), report
documents used, findings per document, spend, and commit the generated
pack under `docs/planning/severity_calibration/` by file name. Otherwise
skip and say why.

### Not in scope
Sentinel workbook (deferred by owner). `/compare/[competitor]` (legal
sign-off first). Any new product feature. Any change under `apps/web/app/
{mitre,codereview,dashboard,upload,results,projects,versions,search}` beyond
what step 2 and step 4 screenshots need.

## Hard constraints
- Brand voice and claim rules from plan §2/§5 for any new copy or alt text.
- Security-adjacent step 2 (platform-admin PATCH): Sonnet adversarial
  takeover before commit (codex companion is broken); threat model:
  org admin tries to set their own tier; verdict in the handoff.
- Delegation per the global playbook: Sonnet for step 2 backend and
  frontend (parallel, one agent each, exact contract above), Haiku for
  smoke tables, Opus reviews every diff. Subagents never run git state
  commands.
- `tsc` clean before every commit; `pg_stat_activity` check before any
  pytest run on edgp_test.
- Stage files by name; never `git add docs/` or `git add .`.

## Session exit
`docs/IMPLEMENTATION_PROGRESS.md` entry; tick plan §7 "also not done"
items you completed; handoff
`docs/phases/summaries/SESSION_HANDOFF_<date>_WRAPUP.md` with commit list,
deployed SHA, smoke table, the prod tier changes made, the OpenRouter key
numbers, and the 4-line agent-utilization footer. Report in the final
message: commits, deployed SHA, what is still open, and the one thing I
must do next.
