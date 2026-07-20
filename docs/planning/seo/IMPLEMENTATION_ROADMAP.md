# ScopeWise — SEO Implementation Roadmap (Task-Level)

**Companion to:** `docs/planning/SEO_STRATEGY.md` Section 9 (phase summary).
This is the engineering/content task breakdown for execution — each item
is small enough to be a single ticket.

---

## Phase 1 — Foundation (Weeks 1-4)

### Engineering
- [x] **Fix Cloudflare robots.txt AI-crawler block** — done 2026-07-20.
  Root cause wasn't a simple dashboard toggle: Cloudflare's zone-level
  `bot_management.ai_bots_protection` was set to `block`, disabled via
  the Cloudflare API. That in turn revealed `is_robots_txt_managed: true`
  was the thing actually serving (and overriding-at-the-edge) robots.txt
  for the whole zone — disabling it caused a 404 until `app/robots.ts`
  (below) was added same-session. **Caveat:** `ai_bots_protection` is
  zone-wide (covers `assessiq.in` too, no per-subdomain scoping in
  Cloudflare's classic Bot Management) — confirmed the main `assessiq.in`
  site's own robots.txt is unaffected (it's served natively from its own
  origin, never depended on Cloudflare's managed layer), but its
  bot-management-level AI-crawler blocking is now off too as a side
  effect. Flagged to the user; revisit with a hostname-scoped
  Configuration/Transform Rule if that needs restoring for the main site.
- [x] Replace `apps/web/app/page.tsx`'s client-redirect-only homepage with
  a real SSR marketing page — done 2026-07-20. `/dashboard` already had
  its own auth guard (redirects to `/login` if no token) from before this
  session, so no logic needed moving there; the homepage now carries zero
  auth/redirect logic at all, just static marketing content.
- [x] Build `/product`, `/pricing`, `/about`, `/contact` — done 2026-07-20
  (static Server Components, shared `MarketingHeader`/`MarketingFooter`).
  `/pricing` is "contact us" pricing for now, per the plan. No fake social
  proof/testimonials anywhere, per the main strategy doc's Section 5 rule
  (accuracy validation is still in progress, see
  `docs/IMPLEMENTATION_PROGRESS.md`).
- [x] `app/sitemap.ts` — done 2026-07-20 (lists `/`, `/product`,
  `/pricing`, `/about`, `/contact`; matches what `app/robots.ts` already
  referenced).
- [x] `app/robots.ts` — done 2026-07-20 (Next.js native, allows `/`,
  disallows the authenticated app routes, required once Cloudflare
  stopped serving its own managed version, see item above)
- [x] `generateMetadata` on every public page — done 2026-07-20 (per-page
  `export const metadata`, plus a title template + metadataBase in the
  root layout for absolute OG URLs).
- [x] `Organization` + `WebSite` + `SoftwareApplication` JSON-LD on
  homepage — done 2026-07-20 (inline `<script type="application/ld+json">`
  in `app/page.tsx`).
- [ ] Google Search Console: verify domain ownership, submit sitemap —
  **needs a human with GSC access to `scopewise.assessiq.in`**, can't be
  done from a coding session. Once deployed: Search Console → Add
  property → `scopewise.assessiq.in` → verify (DNS TXT record via
  Cloudflare, or HTML file upload) → Sitemaps → submit
  `https://scopewise.assessiq.in/sitemap.xml`.
- [ ] GA4: install, verify events fire on key CTAs — **needs a human to
  create a GA4 property** and give the code session the Measurement ID.
  Once you have one: add `NEXT_PUBLIC_GA_MEASUREMENT_ID` to `.env`, wire
  Next.js's `@next/third-parties` `GoogleAnalytics` component (or a plain
  gtag.js script) into `app/layout.tsx`, and fire an event on the
  homepage's two "Get started" CTAs (`/login` links) — a future session
  can wire the code once the Measurement ID exists.
- [ ] Lighthouse/PageSpeed Insights baseline run on the new marketing
  pages — blocked until deployed to the live site (local Next.js dev
  builds hit the Windows-Defender-on-`.next` issue noted in `CLAUDE.md`,
  so this needs to run against the deployed VPS, not local).

### Content
- [x] Homepage copy — done 2026-07-20 (value prop, three-step "how it
  works," six-agent grid, no fabricated social proof).
- [x] `/product` copy — done 2026-07-20 (plain-language explanation of
  the 6 agents + rule engine + versioning/fix-verification, sourced from
  `docs/planning/4_AI_AGENT_SPECS.md`'s agent descriptions).
- [x] `/pricing` copy — done 2026-07-20 ("contact us" pricing, feature
  list, CTA to `/contact`).

**Phase 1 exit criteria:** homepage returns real HTML to a crawler
(verified 2026-07-20 -- see deploy note below) — done. GSC verification +
sitemap submission and Lighthouse baseline are the two items still open,
both blocked on human dashboard access, not on code.

---

## Phase 2 — Expansion (Weeks 5-12)

### Engineering
- [x] `/use-cases/sow-review`, `/use-cases/rfp-review`,
  `/use-cases/scope-creep-prevention` — done 2026-07-20. Static Server
  Components (not a dynamic `[slug]` template — 3 fixed pages didn't
  justify one), each with `FAQPage` JSON-LD and internal links to
  `/pricing` + matching `/solutions/for-*` per `SITE_STRUCTURE.md`'s
  matrix.
- [x] `/solutions/for-procurement`, `/for-legal`, `/for-agencies` — done
  2026-07-20. Same static-page pattern, linking back to `/pricing` +
  matching `/use-cases/*`.
- [x] `/resources/glossary/[term]` route + `DefinedTerm` schema — done
  2026-07-20. Dynamic route (`generateStaticParams` + `generateMetadata`)
  backed by `apps/web/app/resources/glossary/data.ts`; `/resources/glossary`
  index page added too.
- [x] Internal linking pass per `SITE_STRUCTURE.md`'s matrix — done
  2026-07-20. Homepage → use-cases row added; `/product` → `/use-cases/sow-review`
  + `/pricing`; nav/footer updated with Use Cases/Solutions/Glossary links;
  every new page links to `/pricing` and its counterpart page.
- [ ] Decide CMS/authoring approach for `/resources/blog` and
  `/resources/guides` (hand-coded MDX vs. headless CMS) — **blocking
  decision, make this in week 5, not mid-phase**. Still open — no blog
  content shipped this pass, deliberately (see content note below).
- [ ] `Article`/`BlogPosting` schema on blog posts, with a real `author`
  object (E-E-A-T) — blocked on the CMS decision above, no blog exists
  yet.

### Content (see `CONTENT_CALENDAR.md` for the full list)
- [x] `/use-cases/sow-review`, `/use-cases/rfp-review`,
  `/use-cases/scope-creep-prevention` — done 2026-07-20, grounded in
  `docs/planning/4_AI_AGENT_SPECS.md`, no fabricated stats/testimonials.
- [x] `/solutions/for-procurement`, `/for-legal`, `/for-agencies` — done
  2026-07-20, same grounding rule.
- [x] Glossary terms, first 5 (liability cap, indemnification, scope
  creep, MSA, SOW) — done 2026-07-20, 150-300+ words each per
  `CONTENT_CALENDAR.md`'s target.
- [ ] Blog posts #1-8 (Month 1-2 batch) — **not done this pass**. These
  require the CMS/authoring decision above plus a named human reviewer
  per `CONTENT_CALENDAR.md`'s editorial rule (E-E-A-T) — not something a
  coding session can complete unilaterally.

**Phase 2 exit criteria:** 15-20 pages indexed in GSC; first organic
sessions appear in GA4 (even if low volume). 9 new pages + glossary index
shipped this pass (12 URLs total including glossary terms) — GSC/GA4
verification itself is still blocked on human dashboard access per Phase 1.

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
