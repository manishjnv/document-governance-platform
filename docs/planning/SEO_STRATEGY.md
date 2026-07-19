# ScopeWise — Enterprise-Grade SEO Strategy

**Status:** Planning only — nothing in this doc is implemented yet.
**Date:** 2026-07-20
**Site:** https://scopewise.assessiq.in
**Prepared via:** `seo-plan` skill (SaaS template) + live-site baseline check. No
DataForSEO/Ahrefs/SEMrush access in this session — competitive keyword
volumes/difficulty below are qualitative estimates from category knowledge,
not tool-verified. Re-run with real keyword data (GSC + Ahrefs/SEMrush/
DataForSEO) before finalizing budget commitments.

---

## 1. Baseline assessment (as of this session)

Checked directly against the live site before writing anything below:

| Check | Result | Severity |
|---|---|---|
| `/` (homepage) | 100% client-side redirect (`useEffect` → `/login` or `/dashboard`). No server-rendered content, no `<h1>`, no body copy. A crawler sees `<title>ScopeWise</title>` + `"Redirecting..."` and nothing else. | **Critical** |
| `robots.txt` | Cloudflare-managed default. `User-agent: *` allows crawling, but `Google-Extended`, `GPTBot`, `ClaudeBot`, `Applebot-Extended`, `CCBot`, `Bytespider`, `meta-externalagent`, `Amazonbot` are all `Disallow: /`. | **Critical** — blocks AI-answer-engine visibility (Google AI Overviews, ChatGPT, Claude, Perplexity-adjacent crawlers) sitewide, likely an unreviewed Cloudflare bot-management default, not a deliberate choice |
| `sitemap.xml` | 404 — doesn't exist | High |
| Meta description | Generic, present only on the redirect shell: "Catch contract risk before you sign." | Medium (fine as a tagline, but it's the *only* copy on the *only* public page) |
| Public marketing pages | **None.** Every route (`/dashboard`, `/upload`, `/search`, `/results/*`) requires auth or is the app itself. There is no `/product`, `/pricing`, `/blog`, `/about`, `/features` — nothing for a crawler or a cold prospect to land on. | **Critical** |
| Structured data | None found | High |
| Rendering | Next.js 14 App Router, but the one public route (`/`) is `'use client'` with no SSR content — everything currently indexable is effectively blank | Critical (architectural) |

**Bottom line: there is no SEO surface to optimize yet.** This isn't a
"improve rankings" problem, it's a "the marketing site doesn't exist"
problem. Every phase below is sequenced around building that surface first,
then optimizing it — trying to do technical/content SEO before Phase 1
ships would mean optimizing pages that don't exist.

---

## 2. Business context (from repo/product knowledge, not assumptions)

- **Product:** AI-powered SOW/RFP document review. 6 specialist AI agents
  (Scope, Delivery, Commercial, Security, PMO, Legal) + a deterministic
  rule engine (20 SOW rules, 7 RFP rules) score risk, flag ambiguous
  language, and catch scope-creep/liability/commercial gaps before a
  contract is signed.
- **ICP:** procurement, legal, and PMO teams at mid-to-large enterprises
  reviewing vendor SOWs/RFPs; secondarily, agencies/consultancies drafting
  SOWs for clients who want to self-check before sending.
- **Differentiator vs. general CLM (contract lifecycle management)
  platforms:** ScopeWise is narrow and pre-signature — it's not trying to
  be Ironclad/DocuSign CLM (which manage the full contract lifecycle
  post-execution). The wedge is "catch the risk *before* you sign," which
  is a distinct search intent from "manage my contracts after signing."
- **Deployment stage:** live, but pre-launch on the accuracy-validation
  side (per `docs/IMPLEMENTATION_PROGRESS.md` — Metrics 1.1-1.4 still being
  validated). SEO content can ship now; case studies/proof-points should
  wait for real customer data, not be fabricated.

---

## 3. Competitive landscape (qualitative — verify with real tools before acting)

Three adjacent categories compete for the same searcher intent, none of
them occupy ScopeWise's exact wedge:

| Category | Examples | What they rank for | Gap ScopeWise can own |
|---|---|---|---|
| CLM (contract lifecycle mgmt) | Ironclad, Icertis, LinkSquares, Evisort, ContractPodAi, Concord | "contract management software," "CLM platform," post-signature workflow | They're built for *after* signature; thin on pre-signature SOW/scope risk review as a standalone motion |
| AI contract review (redlining) | Spellbook, LinkSquares Analyze, Lexion, Kira | "AI contract review," "AI redlining" | General-purpose across all contract types; none specialize in SOW/RFP *scope* risk specifically |
| RFP response/management | Loopio, Responsive (RFPIO), Ombud | "RFP software," "RFP response management" | These help *write/respond to* RFPs, not *evaluate/de-risk* a received SOW/RFP before committing |

**Strategic positioning:** ScopeWise's defensible SEO angle is the
intersection nobody else fully owns — *"review a SOW/RFP for risk before
you sign it,"* not *"manage contracts"* or *"respond to RFPs."* Content and
keyword strategy (Section 5) should lean hard into this wedge rather than
competing head-on for "contract management software" (high volume, high
competition, wrong intent match).

**Action item for a future session:** run `dataforseo_labs_google_competitors_domain`
and `dataforseo_labs_google_domain_intersection` (or Ahrefs/SEMrush
equivalents) against Ironclad, Spellbook, and LinkSquares to get real
keyword-gap data once those tools are available — this session had no
DataForSEO/Ahrefs access.

---

## 4. Site architecture

Adapted from the SaaS template to ScopeWise's actual product shape. Today
only the app shell exists (`/login`, `/dashboard`, `/upload`, `/search`,
`/results/[reviewId]`) — everything below is **new, public, unauthenticated**
routes to be built.

```
/ (real marketing homepage — replaces the current redirect shell)
├── /product
│   ├── /how-it-works
│   ├── /agents            (the 6 AI reviewers as a feature story)
│   └── /security          (SOC2/data-handling — build once real, don't fake it)
├── /solutions
│   ├── /for-procurement
│   ├── /for-legal
│   └── /for-agencies       (agencies self-checking SOWs before sending to clients)
├── /use-cases
│   ├── /sow-review
│   ├── /rfp-review
│   └── /scope-creep-prevention
├── /pricing
├── /compare
│   ├── /scopewise-vs-manual-review
│   └── /scopewise-vs-[clm-competitor]   (only after legal review of claims)
├── /resources
│   ├── /blog
│   ├── /guides             (e.g. "SOW Review Checklist," "RFP Red Flags")
│   ├── /templates          (lead-gen: SOW checklist download, RFP scoring rubric)
│   └── /glossary           (scope creep, MSA vs SOW, liability cap, etc. — long-tail SEO)
├── /customers               (case studies — DO NOT populate until real customers exist)
├── /about
├── /contact
└── /login, /dashboard, /upload, /search, /results/*   (existing app, stays behind auth)
```

**Internal linking rule:** every `/resources/guides/*` and `/resources/blog/*`
page links to the relevant `/use-cases/*` page, which links to `/pricing`
and a signup/demo CTA. This is the conversion path — content → use-case →
pricing/signup, not content as a dead end.

---

## 5. Keyword & content strategy

### Pillar 1: SOW review (primary wedge)
- `statement of work review checklist`
- `how to review a SOW before signing`
- `SOW red flags`
- `scope creep prevention`
- `AI SOW review` / `AI contract scope review`

### Pillar 2: RFP evaluation
- `RFP evaluation checklist`
- `how to evaluate an RFP response`
- `RFP red flags`
- `RFP risk assessment`

### Pillar 3: Contract risk / procurement risk (broader top-of-funnel)
- `vendor contract risk`
- `procurement risk management`
- `liability cap negotiation`
- `ambiguous contract language examples`

### Pillar 4: Category-defining / branded
- `AI contract review tool`
- `pre-signature contract review`
- `[ScopeWise] reviews` (once real usage exists)

**Content-type mapping** (per SaaS template's funnel structure):
- **Bottom-of-funnel:** `/compare/*`, `/pricing`, ROI-style "cost of a bad
  SOW" calculator/guide
- **Middle-of-funnel:** `/resources/guides/*` (SOW Review Checklist, RFP
  Red Flags Guide) — gated or ungated lead magnets
- **Top-of-funnel:** `/resources/blog/*` — "Statement of Work vs. MSA,
  what's the difference," "5 scope creep clauses that cost enterprises
  millions," industry-trend commentary

**Glossary is a long-tail SEO workhorse for this niche** — terms like
"liability cap," "indemnification clause," "MSA vs SOW," "deliverable
acceptance criteria" have real search volume from people who don't yet
know they need a tool like ScopeWise. Each glossary entry links back to
the relevant use-case page.

**Do not fabricate:** no case studies, testimonials, or "trusted by X
companies" claims until real customers exist (per
`docs/planning/5_LAUNCH_CRITERIA.md`, accuracy validation is still
in-progress) — publishing unverified social proof is a credibility risk
that actively hurts E-E-A-T once discovered.

---

## 6. Technical SEO foundation

This is the highest-priority phase given the baseline findings in Section 1.

1. **Fix `robots.txt`** — override Cloudflare's managed default (Cloudflare
   dashboard → Bots → AI Scrapers and Crawlers, or a custom rule) to allow
   `Google-Extended`, `GPTBot`, `ClaudeBot`, and other AI crawlers on public
   marketing routes at minimum. Keep `Disallow` on `/dashboard`, `/upload`,
   `/search`, `/results/*` (authenticated app surface — nothing to index
   there anyway, and no reason to let AI crawlers hit it).
2. **Build `sitemap.xml`** — Next.js App Router supports this natively via
   `app/sitemap.ts` (no new dependency). Auto-generate from the public
   route list in Section 4.
3. **Server-render the marketing pages.** Replace the current `'use client'`
   redirect-only homepage with a real static/SSR marketing page; move the
   login-check redirect logic to `/dashboard`'s own auth guard (or
   middleware) instead of living on `/`. This is the single highest-impact
   technical fix — right now Google has nothing to index at the root
   domain.
4. **Next.js Metadata API** (`generateMetadata`) per page — title, meta
   description, Open Graph, Twitter Card. Next.js 14 supports this
   natively, no new package.
5. **Core Web Vitals baseline** — once real marketing pages exist, run
   PageSpeed Insights/Lighthouse and set numeric targets (LCP < 2.5s,
   INP < 200ms, CLS < 0.1). The existing app is a heavy client-rendered
   SPA (per `docs/RCA_LOG.md` Windows-Defender-on-node_modules notes,
   `next dev` is already resource-heavy) — the marketing site should be a
   separate, lighter render path (static generation), not inherit the
   dashboard's client-bundle weight.
6. **Canonical URLs + trailing-slash consistency** — set explicitly, don't
   rely on defaults.
7. **`hreflang`** — skip for now (no evidence of a non-English/multi-region
   launch plan); revisit if international expansion becomes real.

---

## 7. Schema / structured data plan

| Page | Schema type(s) |
|---|---|
| Homepage | `Organization`, `WebSite`, `SoftwareApplication` |
| `/product/*` | `SoftwareApplication` (with `applicationCategory: BusinessApplication`) |
| `/pricing` | `Offer` nested under `SoftwareApplication` |
| `/resources/blog/*` | `Article` / `BlogPosting`, `author` referencing a real person (E-E-A-T) |
| `/resources/guides/*` | `TechArticle` or `HowTo` where genuinely a step-by-step guide |
| `/resources/glossary/*` | `DefinedTerm` |
| `/compare/*` | `FAQPage` for the comparison Q&A section |
| `/customers/*` (once real) | `Review`/`Organization` (customer), never fabricated ratings |

All JSON-LD, validated against Google's Rich Results Test before shipping
each page type — don't batch-validate at the end.

---

## 8. GEO (AI-answer-engine) considerations

Given the product itself is AI-powered, ranking in AI Overviews/ChatGPT/
Perplexity answers for "how do I review a SOW" style queries is high-value
and currently **fully blocked** by the robots.txt finding in Section 1.
Once that's fixed:

- Structure guide content so a specific paragraph directly answers the
  query in the first 2-3 sentences (AI answer engines extract passages,
  not full pages).
- `FAQPage` schema on `/use-cases/*` and `/compare/*` pages — these are
  the pages most likely to get pulled into an AI-generated answer.
- Publish original data once available (e.g. "we analyzed N SOWs and found
  X% had no liability cap") — AI engines and human searchers both favor
  citable original research over restated general advice.
- Track citations via manual spot-checks (ask ChatGPT/Perplexity/Google AI
  Overviews the target queries periodically) — no reliable automated
  tracker for this yet at small scale.

---

## 9. Phased roadmap

### Phase 1 — Foundation (Weeks 1-4)
- [ ] Fix `robots.txt` (Cloudflare AI-crawler block) — **do this first, it's a 10-minute fix with sitewide impact**
- [ ] Build real marketing homepage (SSR, not client-redirect)
- [ ] Build `/pricing`, `/product`, `/about`, `/contact`
- [ ] `app/sitemap.ts`, Metadata API on every public page
- [ ] `Organization` + `WebSite` + `SoftwareApplication` schema
- [ ] Google Search Console + GA4 wired up (verify ownership, submit sitemap)
- [ ] Core Web Vitals baseline measured

### Phase 2 — Expansion (Weeks 5-12)
- [ ] `/use-cases/sow-review`, `/use-cases/rfp-review`, `/use-cases/scope-creep-prevention`
- [ ] `/solutions/for-procurement`, `/for-legal`, `/for-agencies`
- [ ] Blog launch — 8-10 initial posts covering Pillar 1-3 keywords
- [ ] Glossary launch — 15-20 terms
- [ ] Internal linking pass (content → use-case → pricing)

### Phase 3 — Scale (Weeks 13-24)
- [ ] `/compare/*` pages (legal-reviewed competitor comparisons)
- [ ] Downloadable guides/templates (SOW checklist, RFP scoring rubric) as lead magnets
- [ ] GEO optimization pass (FAQ schema, passage-first content structure) — contingent on Phase 1's robots.txt fix already being live
- [ ] First real case study, once a customer exists and consents

### Phase 4 — Authority (Months 7-12)
- [ ] Original research content (aggregate, anonymized findings from real reviews run through the platform — contingent on enough volume + a data-usage policy that covers this)
- [ ] Guest content / industry PR (procurement, legal-ops, PMO trade publications)
- [ ] Expand `/compare/*` and `/solutions/*` based on actual query data from GSC
- [ ] Continuous optimization loop from real GSC/GA4 data, not the qualitative estimates in Section 5

---

## 10. KPI targets

Baselines are effectively zero (no marketing site exists yet), so 3-month
targets are about *existing*, not yet about competing.

| Metric | Baseline (today) | 3 Month | 6 Month | 12 Month |
|---|---|---|---|---|
| Indexed public pages | 0 (redirect shell only) | 15-20 | 40-60 | 100+ |
| Organic sessions/mo | ~0 | 200-500 | 1,500-3,000 | 8,000-15,000 |
| Ranking keywords (any position) | 0 | 30-50 | 150-250 | 500+ |
| Top-10 rankings (pillar terms) | 0 | 0-2 | 5-10 | 20+ |
| Core Web Vitals (marketing pages) | not measured | all "Good" | maintained | maintained |
| Organic → signup/demo requests | 0 | 2-5/mo | 15-25/mo | 60-100/mo |

Revisit these once Phase 1 ships and a real GSC baseline exists — the
6/12-month numbers above are category-typical estimates for a new B2B SaaS
domain, not derived from ScopeWise's actual authority.

---

## 11. Resourcing & dependencies

- **Content:** needs a subject-matter writer (procurement/legal-ops
  background ideal) — AI-drafted content for a product literally selling
  "catch what AI + rules review misses" carries obvious credibility risk
  if it reads as generic AI-generated filler. Human review/editing is not
  optional here.
- **Engineering:** Phase 1's technical items (SSR homepage, sitemap,
  metadata, robots.txt) are the same team currently building the app —
  scope as a discrete workstream, not squeezed into feature sprints.
- **Legal:** required sign-off before any `/compare/*` competitor page
  ships (trademark/fair-use review, per the SaaS template's legal
  considerations section).
- **Blocking dependency:** case studies and "trusted by" social proof
  can't ship credibly until real customers exist post-launch — don't let
  the content calendar get ahead of the product's actual traction.

---

## 12. Open items for a follow-up session

1. Real keyword-volume/difficulty data (Ahrefs/SEMrush/DataForSEO) — this
   session had no access; Section 5's keyword list is directionally right
   but unverified.
2. Real competitor domain-authority/backlink data — Section 3's
   competitive analysis is qualitative.
3. Decide CMS/authoring approach for `/blog` and `/resources` — hand-coded
   MDX in the Next.js app vs. a headless CMS — not decided here, affects
   Phase 2 engineering estimate.
4. Confirm data-usage policy allows the Phase 4 "aggregate anonymized
   findings" content idea before committing to it.
