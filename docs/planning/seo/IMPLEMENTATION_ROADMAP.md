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
- [x] Google Search Console: sitemap submitted 2026-07-20 to the
  existing `assessiq.in` **Domain property** (covers all subdomains via
  DNS verification, no separate `scopewise.assessiq.in` property needed).
  Submitted sitemap showed "Couldn't fetch" with a blank "Last read" —
  Google hadn't attempted the crawl yet as of submission time; site-side
  everything checks out (200, valid XML, correct robots.txt, verified
  even with a spoofed Googlebot UA). Waiting on Google's next crawl pass
  to confirm "Success" — not a code issue.
- [x] GA4 installed — done 2026-07-20. Measurement ID `G-BS21BGYW3B`
  wired via a plain `next/script` gtag.js snippet in `app/layout.tsx`
  (no `@next/third-parties` dependency added, per the lazy-dependency
  rule — a few lines of `next/script` covers it). Threaded through as a
  build arg: `Dockerfile.prod` → `docker-compose.vps.yml` →
  `NEXT_PUBLIC_GA_MEASUREMENT_ID` in the VPS `.env`. Confirmed live (ID
  present in page source, gtag script loads). Per-CTA event firing (the
  original ask) not wired yet — only the base pageview/config call.
- [x] Lighthouse baseline run — done 2026-07-20 against the live VPS
  (see Baseline measurements table below): homepage 79, /product 89.

### Content
- [x] Homepage copy — done 2026-07-20 (value prop, three-step "how it
  works," six-agent grid, no fabricated social proof).
- [x] `/product` copy — done 2026-07-20 (plain-language explanation of
  the 6 agents + rule engine + versioning/fix-verification, sourced from
  `docs/planning/4_AI_AGENT_SPECS.md`'s agent descriptions).
- [x] `/pricing` copy — done 2026-07-20 ("contact us" pricing, feature
  list, CTA to `/contact`).

**Phase 1 exit criteria:** homepage returns real HTML to a crawler
(verified 2026-07-20) — done. All engineering + content items done.

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
- [x] CMS/authoring decision for `/resources/blog` — made 2026-07-20:
  hand-coded TypeScript data file + dynamic route (no MDX, no headless
  CMS), same pattern as the glossary system. `/resources/guides` not
  built yet, same decision would apply when it is.
- [x] `BlogPosting` schema on blog posts — done 2026-07-20, `author` is
  `{"@type": "Organization", "name": "ScopeWise"}` rather than a named
  Person (no named individual reviewer assigned yet — see content note
  below).

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
- [x] `FAQPage` schema on `/use-cases/*` — done 2026-07-20 as part of
  Phase 2 (was built ahead of schedule alongside the use-case pages
  themselves). `/compare/*` still open — no `/compare/*` pages exist yet.
- [ ] `FAQPage` schema on `/compare/*` — blocked on `/compare/*` pages
  existing (see Content section below).
- [ ] `/resources/templates` download flow (gated lead magnet — needs a
  form + email capture, check if this reuses any existing
  signup/lead infrastructure or needs new plumbing)
- [ ] Core Web Vitals re-check against Phase 1 baseline; fix regressions

### Content
- [x] Remaining 10 of the 15-term glossary batch — done 2026-07-20 (rfp,
  rfi, deliverable-acceptance-criteria, fixed-price-contract,
  time-and-materials-contract, force-majeure,
  termination-for-convenience, sla, warranty-clause,
  limitation-of-liability). Full 15-term batch from `CONTENT_CALENDAR.md`
  is now done; `sitemap.ts` picks these up automatically (it maps over
  `GLOSSARY_ENTRIES`, no manual edit needed per new term).
- [x] Blog engineering scaffold + 3 of 8 Month 1-2 posts drafted and
  published — done 2026-07-20 (`/resources/blog`, `/resources/blog/[slug]`,
  `BlogPosting` JSON-LD, `author: 'ScopeWise Team'` / Organization schema
  type, no fabricated named reviewer). Indexed + added to `sitemap.ts`
  and footer nav 2026-07-20 after review. Note for the record:
  `CONTENT_CALENDAR.md`'s editorial rule calls for a **named** human
  reviewer with procurement/legal-ops credibility, and these went live
  under a general approval rather than that specific named-reviewer
  process — worth tightening if/when a real reviewer is assigned. Posts
  #4-8 of the Month 1-2 batch (and all of #9-16) not drafted yet.
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

Measured with local `lighthouse` CLI against the live VPS (simulated
throttling, not CrUX field data -- swap for real PSI/CrUX numbers via
`seo-google` once GSC/GA4 access exists).

| Metric | Value | Date measured |
|---|---|---|
| Lighthouse Performance (homepage) | 79 | 2026-07-20 |
| Lighthouse Performance (/product) | 89 | 2026-07-20 |
| LCP (homepage) | 2.9s | 2026-07-20 |
| LCP (/product) | 2.5s | 2026-07-20 |
| TBT (homepage) | 650ms | 2026-07-20 |
| CLS | 0 | 2026-07-20 |
| GSC verified | _pending_ — needs human dashboard access | |
| Sitemap submitted | _pending_ — needs human dashboard access | |
