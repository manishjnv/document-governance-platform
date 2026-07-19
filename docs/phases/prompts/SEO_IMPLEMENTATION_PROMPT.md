# SEO Implementation — Phase 1 Kickoff Prompt (Next Session)

**Target duration:** 1 session for Phase 1 (Foundation). Phases 2-4 are
separate future sessions, sequenced in `docs/planning/seo/IMPLEMENTATION_ROADMAP.md`.
**Status:** Planning fully done (2026-07-20), zero implementation started.
**Origin:** Enterprise SEO strategy requested 2026-07-20, produced via the
`seo-plan` skill + a live-site baseline check.

Paste everything below into a new session to kick off Phase 1.

---

## Context: read these first, in one parallel batch

1. `docs/planning/SEO_STRATEGY.md` — the full strategy. Read Section 1
   (baseline findings) and Section 6 (technical foundation) closely —
   those are what Phase 1 implements.
2. `docs/planning/seo/IMPLEMENTATION_ROADMAP.md` — the task-level
   checklist this session executes (Phase 1 section specifically).
3. `docs/planning/seo/SITE_STRUCTURE.md` — full URL list + internal
   linking matrix, needed once you get past the four core pages into
   `/use-cases` etc. (later phases, but read now for the shape).
4. `CLAUDE.md` (repo root) — project conventions: docs folder purposes,
   testing baselines, VPS deployment/Caddy safety rules. Follow throughout,
   not just at the start.
5. `docs/RCA_LOG.md` — skim for anything touching `apps/web` routing,
   Next.js build/deploy, or Dockerfile — several entries are copy-pasted
   patterns that recur.

## The two critical findings driving Phase 1's priority order

Confirmed live against `https://scopewise.assessiq.in` on 2026-07-20 —
re-verify they're still true before starting, don't assume they're stale:

1. **The homepage (`/`) is a 100% client-side redirect with zero
   indexable content.** `apps/web/app/page.tsx` is a `'use client'`
   component whose entire body is a `useEffect` that redirects to
   `/login` or `/dashboard`. A crawler sees `<title>ScopeWise</title>` and
   the literal text `"Redirecting..."` — nothing else. **This is the
   single highest-priority fix.** Nothing else in this plan matters if
   the homepage has no content to index.
2. **Cloudflare's managed `robots.txt` blocks AI crawlers sitewide** —
   `Google-Extended`, `GPTBot`, `ClaudeBot`, `Applebot-Extended`, `CCBot`,
   `Bytespider`, `meta-externalagent`, `Amazonbot` are all
   `Disallow: /`, while `User-agent: *` (regular Googlebot/search) is
   allowed. This is almost certainly an unreviewed Cloudflare
   bot-management default, not a deliberate choice — but it blocks AI
   Overviews/ChatGPT/Perplexity-style visibility before it could ever
   start. **10-minute fix, do it first, in the same session as the
   homepage fix** (Cloudflare dashboard → your domain → Bots → AI
   Scrapers and Crawlers, or a custom Transform Rule — this is a
   dashboard change, not a code change, so it doesn't block on a deploy).

## Phase 1 scope (this session)

Full task list in `docs/planning/seo/IMPLEMENTATION_ROADMAP.md`'s Phase 1
section — summarized here:

### Engineering
- Fix the Cloudflare AI-crawler block (dashboard, not code — do this
  first, independent of everything else)
- Replace `apps/web/app/page.tsx`'s client-redirect shell with a real
  SSR/static marketing homepage. Move the "already logged in → redirect
  to `/dashboard`" check into `/dashboard`'s own auth guard instead of
  living on `/` — don't just delete the redirect, relocate the logic so
  logged-in users still land in the app, not on the marketing page.
- Build `/product`, `/pricing`, `/about`, `/contact` as new static pages
  under `apps/web/app/`
- `app/sitemap.ts` (Next.js App Router's native sitemap generation — no
  new dependency)
- `generateMetadata` per public page (Next.js Metadata API — title,
  description, Open Graph, Twitter Card; also no new dependency)
- `Organization` + `WebSite` + `SoftwareApplication` JSON-LD on the
  homepage (see `docs/planning/SEO_STRATEGY.md` Section 7 for the full
  schema-per-page-type table, only homepage's schema is in scope this
  phase)
- Google Search Console: verify domain ownership, submit the new sitemap
- GA4: install, confirm events fire on the primary CTA (signup/demo
  click) — needs a decision on what that CTA actually links to before
  this is meaningful (see open question below)
- Run Lighthouse/PageSpeed Insights against the new marketing pages once
  built; record the numbers in `IMPLEMENTATION_ROADMAP.md`'s "Baseline
  measurements" table at the bottom of that file (currently all
  "_pending_")

### Content
- Homepage copy: value proposition + product explanation. **No fake
  social proof** — no "trusted by X companies," no fabricated
  testimonials or logos. Per `docs/IMPLEMENTATION_PROGRESS.md`, accuracy
  validation (Metrics 1.1-1.4) is still in progress — don't let marketing
  copy imply more validation than actually exists yet.
- `/product` copy: plain-language explanation of the 6 AI agents (Scope/
  Delivery/Commercial/Security/PMO/Legal) + rule engine, from
  `docs/planning/4_AI_AGENT_SPECS.md`
- `/pricing` copy — even if it's "contact us for pricing" initially, the
  page needs to exist and be indexable

## Open question to resolve before/during this session

**What does the homepage's primary CTA actually do?** Options: (a) link
to the existing `/login` page's signup flow, (b) link to a "request a
demo" form that doesn't exist yet (new build), (c) something else. This
wasn't decided during planning — decide it in this session since GA4
event tracking and the homepage copy both depend on the answer. Default
to (a) (existing signup flow) unless there's a reason not to — it's the
only option that doesn't require new backend work, and
`POST /api/v1/auth/signup` already exists and works.

## Conventions to follow (see CLAUDE.md for full detail)

- No DB migrations expected for Phase 1 (pure frontend + Cloudflare
  dashboard + GSC/GA4 setup) — if you find yourself writing one, stop and
  check whether it's actually in scope for this phase.
- `cd apps/web && npx tsc --noEmit` clean before committing any frontend
  change.
- Full backend suite (`cd apps/api && python -m pytest`) should stay
  green even though this phase doesn't touch the backend — run it once
  before declaring the phase done, as a regression check.
- One commit per logical unit (e.g. "homepage rebuild," "sitemap +
  metadata," "GSC/GA4 setup notes" as separate commits), not one giant
  commit for the whole phase.
- Only commit/push/deploy if explicitly asked, per this session's
  instructions or the user mid-session — same as every other session in
  this repo.
- Update `docs/planning/seo/IMPLEMENTATION_ROADMAP.md` checkboxes as you
  go, and its "Baseline measurements" table once Lighthouse numbers exist
  — that table is what Phase 3's "re-check against Phase 1 baseline" task
  depends on.

## Exit criteria for this session

- [ ] Cloudflare AI-crawler block fixed (verify by re-fetching
  `https://scopewise.assessiq.in/robots.txt` and confirming
  `Google-Extended`/`GPTBot`/`ClaudeBot` are no longer `Disallow: /`)
- [ ] Homepage returns real server-rendered content — verify with
  `curl https://scopewise.assessiq.in/ | grep -i "redirecting"` returning
  nothing, not with a browser (browsers execute the client redirect,
  hiding the problem)
- [ ] `/product`, `/pricing`, `/about`, `/contact` live and returning 200
- [ ] Sitemap live at `/sitemap.xml`, submitted in GSC
- [ ] GSC shows the domain verified
- [ ] GA4 installed and confirmed firing on the primary CTA
- [ ] Lighthouse baseline recorded in `IMPLEMENTATION_ROADMAP.md`
- [ ] `tsc --noEmit` clean, full backend suite still green
- [ ] `docs/planning/seo/IMPLEMENTATION_ROADMAP.md` Phase 1 checkboxes
  updated to reflect what's actually done

State plainly at the end which items are done vs. still open — don't
claim Phase 1 complete if, say, GSC verification is pending DNS
propagation or a decision-maker's sign-off on homepage copy. A half-done
Phase 1 clearly labeled is better than an overclaimed "done."
