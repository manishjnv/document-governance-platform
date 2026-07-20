# Session Handoff — 2026-07-20: Document Lifecycle, Auth Overhaul, SEO Plan + Phase 1

**Headline:** Shipped the full 3-phase Document Lifecycle plan (Projects/
Versioning/Fix-verification), found and fixed a critical production bug
(every upload was crashing), added mandatory-project enforcement with
fuzzy name matching, expanded upload file-type support, built Google
Sign-In + email-OTP login end-to-end and then simplified it further to
seamless auto-provisioning auth (no password anywhere in the real UI),
produced a full enterprise SEO strategy, fixed a live Cloudflare
misconfiguration that was blocking every AI crawler sitewide, and
implemented SEO Phase 1 (Foundation) end-to-end after discovering the
cloud-routine execution path for it was a dead end (see "Cloud routine
git-push 403" below).

**Commits (chronological):** `42fcfd5` `1ed9d99` `e966576` `cccc3e6`
`f1de9bd` `d4c6ef6` `271c709` (Document Lifecycle A/B/C) → `23731c5`
`84d3d0e` (mandatory project + file types + critical bugfix) → `67256e7`
`666954b` (project name fuzzy matching + dashboard density) → `2bbbcac`
`8d42b94` (Google SSO/OTP + SEO strategy v1) → `7d3bd9a` `c0b39e6` (OTP UX
polish + SEO companion docs) → `f02c8a7` `4792ed8` (button styling + first
handoff doc) → `46d2778` (seamless auth: password login UI removed,
OTP/Google auto-provision accounts) → `5eeb393` `9d862cd` (Cloudflare
AI-crawler block fixed + native `robots.ts`) → `bb59262` `0419599`
`c310d58` (SEO Phase 1 implementation + roadmap update + ESLint
build-error fix). All pushed to `master`, all deployed to
`scopewise.assessiq.in`.

---

## What shipped

### Document Lifecycle plan (all 3 phases)
- **Phase A — Projects:** first-class `projects` table (migration 023),
  `GET/POST /api/v1/projects` with rollup stats, dashboard grouping,
  per-project detail page. Discovered dormant T-2026–2029 similarity/
  version-diff code already in the repo from an unrelated earlier commit
  — reused it in Phase B instead of rebuilding.
- **Phase B — Versioning:** migration 024, explicit "upload new version"
  + retroactive "link to existing document" actions, similarity-based
  version suggestions (dismissible, persisted), dashboard version
  nesting with a trend indicator.
- **Phase C — Fix-verification:** `app/insights/fix_verification.py`
  diffs a new review's findings against the previous version's by
  category+section_ref; auto-resolves fixed findings and — critically —
  resets a prior manual "Mark Fixed" claim back to open if the re-review
  still finds the issue. Three-bucket Resolved/New/Persisted UI at
  `/versions/diff`.
- Full detail in `docs/IMPLEMENTATION_PROGRESS.md`'s existing Document
  Lifecycle entry (not duplicated here).

### Critical bug found and fixed (see `docs/RCA_LOG.md` #15)
Every real upload via `POST /api/v1/documents/upload` was crashing with
`NameError: name 'doc_id' is not defined` — a leftover log line from the
Phase B `_store_uploaded_document` refactor referenced a variable that
had moved out of scope. **This was live in production** between the
Phase B deploy and the fix later the same session. Caught only because
adding an HTTP-level test for the new mandatory-project validation
exercised the real success path for the first time. Fixed and redeployed
immediately.

### Mandatory project + name matching
- Upload now requires a `project_id` or `project_name` — 422 otherwise.
- `PATCH /{doc_id}/project` retroactively tags documents left without one.
- `find_matching_project()` treats a project name as the same project
  when case-insensitive-equal OR ≥90% similar after stripping generic
  company-type/descriptor words (Corp, Ltd, LLP, Technologies, Tech,
  Solutions, etc.) — "Acme Corporation," "ACME LTD," and "Acme
  Technologies" all resolve to one project.

### File-type support expansion
`.doc` (via `antiword`, added to `Dockerfile.prod`), `.xlsx` (`openpyxl`),
`.xls` (`xlrd`), `.csv` (stdlib) — all route through `parse_document`.
Excel parsers iterate every sheet/tab, not just the first (tested).

### Google Sign-In + email OTP login
- `POST /api/v1/auth/google` verifies Google Identity Services ID tokens
  (`google-auth` lib, no client secret needed) and links/logs in an
  **existing** user matched by email — no self-serve org creation via
  SSO, same constraint as `/auth/signup`.
- `POST /api/v1/auth/otp/request` + `/otp/verify` — 4-digit email code,
  10-minute expiry, 5-attempt lockout, auto-submits on the 4th digit, eye
  icon to reveal the masked input, branded HTML email (verified via a
  real send through Resend's SMTP relay this session).
- **Config fixed along the way:** the repo-root `.env` had Google/
  Cloudflare/Resend credentials pasted as loose notes instead of
  `KEY=VALUE` syntax — silently unreadable by pydantic-settings and
  `docker-compose --env-file`. Reformatted; wired `GOOGLE_CLIENT_ID` and
  `SMTP_*` through `docker-compose.vps.yml` into both the api container's
  runtime env and the web container's `NEXT_PUBLIC_GOOGLE_CLIENT_ID`
  build arg.
- **Email delivery:** Resend SMTP relay (`smtp.resend.com`), sending from
  `noreply@assessiq.in` — **not** `noreply@scopewise.assessiq.in`, because
  only the bare `assessiq.in` domain is DKIM/SPF-verified in Resend today.
  Sending from the subdomain would need it added as its own verified
  domain in Resend first (open item below).

### Dashboard density
Tighter table font/padding (more rows visible without scrolling), tighter
spacing between project sections, "Filter by Type" label+dropdown on one
line.

### Seamless auth: password login removed entirely
Login page (`apps/web/app/login/page.tsx`) has **no password form at
all** now — Google Sign-In and email-OTP are the only two entry points,
and both are seamless signup+login: an unrecognized email creates a
brand-new org+admin account on the spot
(`app/routers/auth.py::_get_or_create_user`, shared by both `/otp/verify`
and `/google`), an existing one logs straight in. No separate "sign up"
screen, no "new vs. returning user" distinction — everyone lands on
`/dashboard`, which already shows empty vs. populated state naturally.

**Scope call, made explicitly with the user rather than silently:**
`POST /auth/login`, `/auth/signup`, `/auth/password-reset(/confirm)`,
`/auth/change-password`, and `app/core/login_lockout.py` are all still in
the backend, unreachable from the real UI now but deliberately **not**
removed — ~15 test files use `POST /auth/login` purely as internal
plumbing to mint a JWT for test setup, and removing the endpoints would
have meant rewriting all of them for zero user-facing benefit. Full
rationale saved to memory
(`project_scopewise_seamless_auth_no_password.md`).

OTP codes are also now 4 digits (was 6), auto-submit as soon as all 4 are
entered, have an eye-icon show/hide toggle, and the email is a branded
HTML template (verified via a real send through Resend).

### Cloudflare misconfiguration found and fixed (live production issue)
While investigating Resend domain verification (unrelated), found that
Cloudflare's zone-level `bot_management.ai_bots_protection` was set to
`block` — this was generating the `Disallow: /` rules for GPTBot,
ClaudeBot, Google-Extended, etc. that the SEO strategy's baseline check
had already flagged. Fixed via the Cloudflare API (not the dashboard —
the token needed a "Bot Management" permission added first, distinct
from "DNS Settings," a genuinely confusing part of Cloudflare's
permission model). Disabling it revealed a second layer:
`is_robots_txt_managed: true` was what served `robots.txt` at the edge in
the first place — disabling that caused a 404 until `apps/web/app/robots.ts`
(Next.js native) was added the same session to replace it.

**Caveat, flagged to the user and left as an open decision:**
`ai_bots_protection` is a **zone-wide** setting (covers `assessiq.in`
too, the shared domain with another live site) — Cloudflare's classic
Bot Management has no per-subdomain scoping. Confirmed the main
`assessiq.in` site's own `robots.txt` is unaffected (served natively
from its own origin, never depended on Cloudflare's managed layer), but
its bot-management-level AI-crawler blocking is now off too as a side
effect. Would need a hostname-scoped Configuration/Transform Rule to
restore selectively if that matters for the main site.

### SEO Phase 1 (Foundation) — implemented end-to-end this session
Full strategy + companion docs (`docs/planning/SEO_STRATEGY.md`,
`docs/planning/seo/*.md`) were written mid-session. A cloud routine was
scheduled to implement Phase 1 (`trig_01EfYV9x6YVs3E8KHNsC1wMo`), but see
"Cloud routine git-push 403" below for why that path was abandoned in
favor of implementing directly in this session:

- Real SSR marketing homepage (was a 100% client-side redirect with
  literally the text "Redirecting..." and nothing else for a crawler to
  see) — value prop, three-step "how it works," six-agent grid,
  `Organization`+`WebSite`+`SoftwareApplication` JSON-LD.
- New `/product`, `/pricing`, `/about`, `/contact` pages (shared
  `MarketingHeader`/`MarketingFooter` components).
- `app/sitemap.ts` (Next.js native).
- Per-page `generateMetadata` + title template/`metadataBase` in the root
  layout for OG.
- No fabricated social proof/testimonials anywhere — accuracy validation
  is still in progress per `docs/IMPLEMENTATION_PROGRESS.md`.
- **Caught a real build-breaking bug:** `next build` runs ESLint and
  treats raw apostrophes/quotes in JSX text as errors
  (`react/no-unescaped-entities`), not warnings — `tsc --noEmit` doesn't
  catch this at all. First VPS deploy attempt failed on it; fixed and
  redeployed. This is why the Docker build (not local `tsc`) is the real
  gate for frontend changes in this repo.

**Still open in Phase 1**, all blocked on human dashboard access, not
code: GSC domain verification + sitemap submission, GA4 property
creation + install, Lighthouse baseline run against the live site. Exact
steps for each are in `docs/planning/seo/IMPLEMENTATION_ROADMAP.md`.

### Cloud routine git-push 403 (infrastructure finding, not an app bug)
The scheduled cloud routine for SEO Phase 1 fired, did the work in its
sandbox, but `git push` to `github.com/manishjnv/document-governance-platform`
consistently returned **403** — confirmed across two separate attempts
(the original run, then its own self-scheduled retry). Root cause: the
routine's `git_repository` source was a plain public HTTPS URL with no
write credentials configured — fine for the initial clone, not for
pushing. The `RemoteTrigger`/routine-creation API surface available in
this session has no field for supplying git push credentials. Net
effect: **any future cloud routine against this repo will hit the same
wall** until either a GitHub connector with write access is configured
account-side (check `https://claude.ai/customize/connectors`), or work
continues to be implemented directly in an interactive session instead
(what happened here for Phase 1).

---

## Migrations applied this session (all 4 required places, per CLAUDE.md)

| # | What | edgp_dev | edgp_test | scopewise_prod | test_insights_extra.py fixture |
|---|---|---|---|---|---|
| 023 | `projects` table + `documents.project_id` | ✅ | ✅ | ✅ | n/a (no column on documents/reviews the fixture mirrors) |
| 024 | `document_link_suggestions` + `organizations.similarity_suggestion_threshold` | ✅ | ✅ | ✅ | added `similarity_suggestion_threshold` to fixture's `organizations` |
| 025 | Widened `documents.file_type` CHECK (doc/xlsx/xls/csv) | ✅ | ✅ | ✅ | n/a (fixture uses plain TEXT, no CHECK) |
| 026 | `users.google_sub` + `otp_codes` table | ✅ | ✅ | ✅ | added `google_sub` to fixture's `users` |

## Test suite

Backend: **458 passed, 2 skipped** (baseline was 402 at session start).
Frontend: `tsc --noEmit` clean throughout, checked after every change set
-- note `tsc` alone is *not* sufficient for frontend changes in this repo,
see the ESLint build-error finding above; the VPS Docker build is the
real gate.

## Deployment

Every code change this session was deployed to `scopewise.assessiq.in`
live, same session — many rebuild/restart cycles for `scopewise-api` and
`scopewise-web`, all verified healthy (`/health` 200, `/login` 200, no
crash loops in logs) after each. Homepage/product/pricing/about/contact
all independently curl-verified live (200s, real HTML, no
"Redirecting..."), sitemap.xml and robots.txt verified serving correctly.

---

## Open items for a future session

1. **Manual browser click-through still not done.** Every feature this
   session was verified via backend HTTP-layer tests + `tsc --noEmit`/live
   `curl` checks, not an actual browser session — say so explicitly rather
   than claim full verification. Worth a dedicated pass: project
   create/upload, version upload + suggestion accept, version-diff view,
   Google Sign-In button, OTP login flow (including the new 4-digit
   auto-submit + eye-icon UX), all four new document file types, and the
   new marketing pages' visual polish.
2. **SEO Phase 1 exit items needing human dashboard access**: GSC domain
   verification + sitemap submission, GA4 property creation + install,
   Lighthouse baseline. Steps in
   `docs/planning/seo/IMPLEMENTATION_ROADMAP.md`.
3. **SEO Phase 2-4** — not started, roadmap in
   `docs/planning/seo/IMPLEMENTATION_ROADMAP.md`. Given the cloud-routine
   git-push 403 finding, do these directly in an interactive session
   rather than scheduling another cloud routine, unless a GitHub
   connector with write access gets configured first.
4. **Cloudflare's `ai_bots_protection` is now off zone-wide**, affecting
   the `assessiq.in` main site too (see "Cloudflare misconfiguration"
   above) — confirm with the user/main-site owner whether that's
   acceptable long-term or needs a hostname-scoped rule instead.
5. **SMTP_FROM_EMAIL is on `assessiq.in`, not `scopewise.assessiq.in`.**
   To send from the ScopeWise subdomain, add `scopewise.assessiq.in` as
   its own domain in Resend and complete its DKIM/SPF DNS verification.
6. **Cloudflare API token permission gaps turned out to be the recurring
   root cause** of several "mystery" 403s this session (`dns_records`,
   `bot_management` before "Bot Management" permission was added) — the
   token's permission list only grants exactly what's explicitly added in
   the Cloudflare dashboard's "+ Add more" UI, and Cloudflare returns the
   same generic "Authentication error" for both IP-restriction failures
   and missing-scope failures, which makes them easy to conflate.
   `dns_records` itself was never re-tested after "Bot Management" was
   added (a different scope), so it may or may not still fail --
   diagnose the same way (check `GET /zones/{id}` works first to isolate
   token/zone/IP from a specific endpoint's permission scope).
7. **Finding deduplication still unimplemented** (carried over from prior
   sessions, unrelated to this session's work) — Metric 1.4 remains
   structurally unmeasurable until built.

---

## Agent-utilization footer

- Opus/main session: all planning, design decisions, code review, and
  implementation this session (no subagent delegation used — direct
  execution throughout).
- Sonnet: n/a — not used this session.
- Haiku: n/a — not used this session.
- codex:rescue: n/a — not invoked. The critical NameError bug (RCA #15)
  touched auth-adjacent upload code but was a mechanical scope bug, not a
  security/auth-logic judgment call; fixed directly and verified via the
  new HTTP-level test instead.
