# ScopeWise — SEO Implementation Roadmap (Task-Level)

**Companion to:** `docs/planning/SEO_STRATEGY.md` Section 9 (phase summary).
This is the engineering/content task breakdown for execution — each item
is small enough to be a single ticket.

---

## Phase 1 — Foundation (Weeks 1-4)

### Engineering
- [ ] **Fix Cloudflare robots.txt AI-crawler block** (Bots → AI Scrapers
  and Crawlers dashboard, or a custom Transform Rule) — allow
  `Google-Extended`, `GPTBot`, `ClaudeBot` on public routes. *Do this
  first — 10-minute fix, sitewide impact, zero dependency on anything
  else.*
- [ ] Replace `apps/web/app/page.tsx`'s client-redirect-only homepage with
  a real SSR/static marketing page (move the "logged in → /dashboard"
  redirect logic into `/dashboard`'s own guard instead)
- [ ] Build `/product`, `/pricing`, `/about`, `/contact` (static pages,
  Next.js App Router, no new dependency)
- [ ] `app/sitemap.ts` (Next.js native sitemap generation)
- [ ] `app/robots.ts` (Next.js native robots.txt generation, or confirm
  Cloudflare's edit from item 1 is sufficient and skip this)
- [ ] `generateMetadata` on every public page (title, description, OG,
  Twitter Card — Next.js Metadata API, no new dependency)
- [ ] `Organization` + `WebSite` + `SoftwareApplication` JSON-LD on
  homepage
- [ ] Google Search Console: verify domain ownership, submit sitemap
- [ ] GA4: install, verify events fire on key CTAs (signup/demo click)
- [ ] Lighthouse/PageSpeed Insights baseline run on the new marketing
  pages, record numbers in this doc's "Baseline" section below once done

### Content
- [ ] Homepage copy (value prop, social proof placeholder — no fake
  testimonials, see main strategy doc Section 5)
- [ ] `/product` copy — what the 6 agents + rule engine do, in plain
  language
- [ ] `/pricing` copy (even if "contact us" pricing initially — a page
  must exist)

**Phase 1 exit criteria:** GSC shows the domain verified and sitemap
submitted; Lighthouse score recorded; homepage returns real HTML to a
crawler (verify with `curl` + view-source, not just visually in a browser).

---

## Phase 2 — Expansion (Weeks 5-12)

### Engineering
- [ ] Decide CMS/authoring approach for `/resources/blog` and
  `/resources/guides` (hand-coded MDX vs. headless CMS) — **blocking
  decision, make this in week 5, not mid-phase**
- [ ] `/use-cases/[slug]`, `/solutions/[slug]` route templates
- [ ] `/resources/glossary/[term]` route + `DefinedTerm` schema
- [ ] `Article`/`BlogPosting` schema on blog posts, with a real `author`
  object (E-E-A-T)
- [ ] Internal linking pass per `SITE_STRUCTURE.md`'s matrix

### Content (see `CONTENT_CALENDAR.md` for the full list)
- [ ] `/use-cases/sow-review`, `/use-cases/rfp-review`,
  `/use-cases/scope-creep-prevention`
- [ ] `/solutions/for-procurement`, `/for-legal`, `/for-agencies`
- [ ] Blog posts #1-8 (Month 1-2 batch)
- [ ] Glossary terms, first 5 (liability cap, indemnification, scope
  creep, MSA, SOW)

**Phase 2 exit criteria:** 15-20 pages indexed in GSC; first organic
sessions appear in GA4 (even if low volume).

---

## Phase 3 — Scale (Weeks 13-24)

### Engineering
- [ ] `FAQPage` schema on `/use-cases/*` and `/compare/*`
- [ ] `/resources/templates` download flow (gated lead magnet — needs a
  form + email capture, check if this reuses any existing
  signup/lead infrastructure or needs new plumbing)
- [ ] Core Web Vitals re-check against Phase 1 baseline; fix regressions

### Content
- [ ] Blog posts #9-16 (Month 3-4 batch) + remaining 15 glossary terms
- [ ] `/compare/scopewise-vs-manual-review` (no legal gate needed — not
  naming a competitor)
- [ ] **Legal review** of any `/compare/[competitor]` page before
  drafting starts, not after
- [ ] First real case study, contingent on a real customer existing and
  consenting — see main strategy doc Section 11

**Phase 3 exit criteria:** first `/compare/*` page live; 150-250 keywords
ranking (any position) per GSC.

---

## Phase 4 — Authority (Months 7-12)

- [ ] Original-research content (Content Calendar item #22) — contingent
  on data-usage policy review (main strategy doc Section 12, open item 4)
- [ ] Guest content / trade-publication outreach (procurement, legal-ops,
  PMO publications)
- [ ] Re-prioritize `/solutions/*` and `/compare/*` expansion based on
  actual GSC query data, not the pre-set calendar
- [ ] Backlink outreach informed by the competitor backlink-profile pull
  (see `COMPETITOR_ANALYSIS.md`'s "what to build once real tools are
  available")

**Phase 4 exit criteria:** see KPI table in main strategy doc Section 10.

---

## Baseline measurements (fill in as Phase 1 completes)

| Metric | Value | Date measured |
|---|---|---|
| Lighthouse Performance (homepage) | _pending_ | |
| Lighthouse Performance (pricing) | _pending_ | |
| LCP | _pending_ | |
| INP | _pending_ | |
| CLS | _pending_ | |
| GSC verified | _pending_ | |
| Sitemap submitted | _pending_ | |
