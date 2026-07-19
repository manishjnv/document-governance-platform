# Session Handoff — 2026-07-20: Document Lifecycle, Auth Overhaul, SEO Plan

**Headline:** Shipped the full 3-phase Document Lifecycle plan (Projects/
Versioning/Fix-verification), found and fixed a critical production bug
(every upload was crashing), added mandatory-project enforcement with
fuzzy name matching, expanded upload file-type support, built Google
Sign-In + email-OTP login end-to-end (verified live), and produced a full
enterprise SEO strategy + Phase 1 kickoff prompt for a future session.

**Commits (chronological):** `42fcfd5` `1ed9d99` `e966576` `cccc3e6`
`f1de9bd` `d4c6ef6` `271c709` (Document Lifecycle A/B/C) → `23731c5`
`84d3d0e` (mandatory project + file types + critical bugfix) → `67256e7`
`666954b` (project name fuzzy matching + dashboard density) → `2bbbcac`
`8d42b94` (Google SSO/OTP + SEO strategy v1) → `7d3bd9a` `c0b39e6` (OTP UX
polish + SEO companion docs). All pushed to `master`, all deployed to
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

### Enterprise SEO strategy (planning only — see below)

---

## Migrations applied this session (all 4 required places, per CLAUDE.md)

| # | What | edgp_dev | edgp_test | scopewise_prod | test_insights_extra.py fixture |
|---|---|---|---|---|---|
| 023 | `projects` table + `documents.project_id` | ✅ | ✅ | ✅ | n/a (no column on documents/reviews the fixture mirrors) |
| 024 | `document_link_suggestions` + `organizations.similarity_suggestion_threshold` | ✅ | ✅ | ✅ | added `similarity_suggestion_threshold` to fixture's `organizations` |
| 025 | Widened `documents.file_type` CHECK (doc/xlsx/xls/csv) | ✅ | ✅ | ✅ | n/a (fixture uses plain TEXT, no CHECK) |
| 026 | `users.google_sub` + `otp_codes` table | ✅ | ✅ | ✅ | added `google_sub` to fixture's `users` |

## Test suite

Backend: **457 passed, 2 skipped** (baseline was 402 at session start).
Frontend: `tsc --noEmit` clean throughout, checked after every change set.

## Deployment

Every code change this session was deployed to `scopewise.assessiq.in`
live, same session — multiple rebuild/restart cycles for `scopewise-api`
and `scopewise-web`, all verified healthy (`/health` 200, `/login` 200,
no crash loops in logs) after each.

---

## Open items for a future session

1. **Manual browser click-through still not done.** Every feature this
   session was verified via backend HTTP-layer tests + `tsc --noEmit`,
   not a live UI session — say so explicitly rather than claim full
   verification. Worth a dedicated pass: project create/upload, version
   upload + suggestion accept, version-diff view, Google Sign-In button,
   OTP login flow, all four new file types.
2. **SMTP_FROM_EMAIL is on `assessiq.in`, not `scopewise.assessiq.in`.**
   To send from the ScopeWise subdomain, add `scopewise.assessiq.in` as
   its own domain in Resend and complete its DKIM/SPF DNS verification
   (Cloudflare DNS — see item 3 for a caveat on doing that via API).
3. **Cloudflare API token's `dns_records` endpoint is broken for this
   token**, discovered while investigating the Resend/domain question.
   `GET /zones/{id}` (single zone) works and confirms correct token/zone/
   permissions (including `dns_records:read` explicitly listed); `GET
   /zones/{id}/dns_records` (the actual records-list endpoint) 403s with
   a generic "Authentication error" regardless of query params, IPv4
   forced, or re-saving the token. Root cause unresolved — looks like a
   Cloudflare-side inconsistency, not a config mistake. If DNS records
   need programmatic access later, expect to hit this again; the
   Cloudflare dashboard works fine as a workaround.
4. **`docs/phases/prompts/SEO_IMPLEMENTATION_PROMPT.md` is ready to run**
   — self-contained Phase 1 (Foundation) kickoff prompt. Leads with the
   homepage-has-zero-indexable-content and Cloudflare-blocks-AI-crawlers
   findings, scoped to one session's worth of work. Phases 2-4 are
   separate future sessions per `docs/planning/seo/IMPLEMENTATION_ROADMAP.md`.
5. **Finding deduplication still unimplemented** (carried over from prior
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
