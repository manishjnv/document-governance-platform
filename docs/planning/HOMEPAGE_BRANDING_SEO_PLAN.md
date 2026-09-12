# Homepage branding + SEO guideline plan (2026-09-12)

Positioning and SEO plan for the public marketing site now that ScopeWise has three products (SOW/RFP review, MITRE ATT&CK coverage, Code Security Review). Decisions: platform-umbrella homepage with three equal product cards; pricing stays quote-based. **Amended 2026-09-12: pricing is NOT linked or indexed on prod; the page exists for direct sharing only.** Supersedes the homepage/positioning parts of `SEO_STRATEGY.md`; its Phase 3 items (`/compare/*`, templates, case study) still stand. Steps 1-6 of §7 implemented 2026-09-12 (commits `2608b7d`…`0384a46`, see §7 ticks); steps 7-8 open.


## 1. Audit of what exists today (public surface)

| Finding | Where | Why it matters |
|---|---|---|
| Homepage, header, `/product`, `/pricing`, all use-case and solution pages mention SOW/RFP only | `apps/web/app/page.tsx`, `components/MarketingHeader.tsx` | Two of three products invisible to visitors and search |
| No marketing page for MITRE or Code Review | none exist | Zero organic acquisition for the two newest products; Sentinel workbook funnel (`marketplace/sentinel/`) points at a product with no landing page |
| `/mitre`, `/codereview`, `/admin`, `/login` not in robots disallow | `apps/web/app/robots.ts` | Thin authed shells get crawled and can outrank future landing pages |
| All body copy is `text-muted-foreground` (88 uses); token is `215 16% 47%` | `apps/web/app/globals.css` | Passes WCAG AA barely; reads washed-out. One-token fix darkens the whole site |
| Inter declared in tailwind but never loaded | `tailwind.config.ts`, `layout.tsx` | Site renders in system font; brand inconsistency across machines |
| No OG/Twitter image anywhere; card type `summary` | `layout.tsx` | Every shared link has no preview |
| Header links to 3 pages; blog/glossary/solutions/pricing/contact are footer-only | `MarketingHeader.tsx` | Weak internal linking to the largest content cluster |
| `/pricing` noindex + unlinked (orphan) | `pricing/page.tsx`, `robots.ts` | Decision: index it and link it |
| `/privacy` uncommitted, not in sitemap, footer link uncommitted | `apps/web/app/privacy/`, `MarketingFooter.tsx` | Finished work waiting on a commit |
| Sitemap `lastModified: new Date()` on every URL | `sitemap.ts` | Meaningless lastmod; Google ignores it |
| Blog author = Organization "ScopeWise Team", no `dateModified`/`image` | `resources/blog/[slug]/page.tsx` | E-E-A-T gap the SEO strategy doc itself flags |
| Glossary `inDefinedTermSet` is a string, not an entity | `resources/glossary/[term]/page.tsx` | Minor schema validity |
| `/about` body is 100% muted `text-lg` | `about/page.tsx` | Worst contrast page |
| `/product` has no JSON-LD | `product/page.tsx` | Missing SoftwareApplication/HowTo |
| Existing SEO plan Phases 1–2 done, Phase 3 (`/compare/*`, templates, case study) open | `docs/planning/SEO_STRATEGY.md`, `docs/planning/seo/IMPLEMENTATION_ROADMAP.md` | Reuse, don't rewrite |

Reusable as-is: the 6-agent grid copy, the 3-step how-it-works, use-case and solution pages,
8 blog posts, 15 glossary terms, FAQ block pattern with `FAQPage` JSON-LD (use-cases), privacy
page, the `CtaClickTracker` GA4 wiring, per-page `metadata` pattern.

---

## 2. Brand positioning

**Umbrella promise (hero):** ScopeWise turns the three highest-effort consultancy and
procurement assessments into evidence-based, client-ready reports: contract risk, detection
coverage, and code security.

**Name rationale to state on `/about`:** "Scope" = what is in and out of a contract, a
detection estate, a codebase. Keeps the existing name meaningful across all three.

**Brand voice rules** (put in the doc; enforce in copy review):
- Numbers are deterministic, AI only where honest. Say so; it is the actual architecture
  (MITRE: LLM never emits a number; Code Review: no LLM; SOW: rule engine + agents).
- Every claim traceable to a framework or a stated assumption. Cite PMBOK, ISO 31000,
  NIST SP 800-30, WorldCC most-negotiated terms, FAR Part 15, MITRE ATT&CK v19.1, MITRE
  Evaluations, CWE/CVSS.
- No fabricated logos, testimonials, "trusted by" or case studies until a real customer
  agrees (SEO_STRATEGY §2, IMPLEMENTATION_PROGRESS:1360).
- Plain language, no AI-tell phrases (already machine-enforced for MITRE narrative; apply
  the same banned list to marketing copy).

**Tagline options** (pick one, keep `<title>` template `%s | ScopeWise`):
1. "Evidence-based risk reviews. Contracts, detections, code." (recommended)
2. "Assess the scope. Prove the gaps. Ship the report."
3. Keep "Catch risk before you sign" for the SOW card only, not the site.

**Visual identity changes (design tokens only, no per-page edits):**
- `--muted-foreground` from `215 16% 47%` to `215 22% 32%` (≈ #3F4A5C, contrast ~9:1 on white).
  Keep `--foreground` as is. Footer/legal text may use `215 16% 40%` minimum.
- Load Inter via `next/font/google` in `layout.tsx` (or drop it from tailwind and commit to
  the system stack; pick one, stop declaring a font that never loads).
- Add a static 1200×630 OG image (`apps/web/public/og-default.png`) with wordmark + tagline;
  set `openGraph.images` and `twitter.card: summary_large_image` in root metadata; per-pillar
  OG images later.
- Keep `#0066cc` primary. Introduce one accent per pillar for cards/icons only: SOW blue
  (existing), MITRE purple/teal (already the PPTX deck palette), Code Review a warm amber.
  Body text stays the dark token; accents never carry text.
- Prefer real product screenshots (results page, heatmap, findings drawer) over icon rows,
  per 2026 B2B guidance. Mask any customer data; use the NodeGoat golden scan and the
  ACME sample for MITRE.

---

## 3. Homepage blueprint (`apps/web/app/page.tsx`, full rewrite)

Above the fold: one H1, one sub-head, two CTAs, three product cards visible without scrolling
on desktop.

1. **Hero**
   - H1: "Evidence-based risk reviews for contracts, detections and code"
   - Sub: "ScopeWise reads the SOW, the SIEM rule set or the scanner output, scores the gaps
     against named frameworks, and hands you the client-ready report. Deterministic numbers.
     AI only where it is honest."
   - CTA primary "Start a review" → `/login`; secondary "See the three products" → anchor.
2. **Three product cards** (bento, equal weight, each links to its landing page)
   - **SOW & RFP Review** → `/product/sow-review` (rename current `/product`, keep redirect).
     "Six specialist AI reviewers plus 40 deterministic rules. Risk score, evidence per
     finding, fix-verification on re-review."
   - **MITRE ATT&CK Coverage** → `/product/mitre-coverage`. "Upload your detection rules and
     environment inventory. Get coverage by tactic, ranked gaps, a 90-day roadmap, and the
     PPTX, XLSX and Navigator layer to present it."
   - **Code Security Review** → `/product/code-security-review`. "Run the open-source scanner
     on your side. Upload findings only. Get a plain-language register, exploit chains and
     the fewest fixes that break every chain."
3. **How it works** (reuse the 3-step pattern, generalised): Upload the artefact → Scored,
   evidence-backed review → Client-ready exports (PDF, XLSX, PPTX, Navigator).
4. **Why consultancies use it** (effort and cost, honest framing, see §5 for the numbers we
   may quote): three stat tiles with sourced industry numbers, not our own unmeasured claims.
5. **Trust band**: "Your data" bullets pulled from the privacy page: no raw logs, no source
   code, rule excerpts ≤500 chars sent for tagging, credentials AES-256-GCM, LLM via
   OpenRouter only, nothing used for training.
6. **Who it is for**: Procurement & Legal · Security consultancies & MDR · AppSec
   consultants. Links to `/solutions/*` (existing three) plus two new solution pages (§4).
7. **Resources strip**: latest 3 blog posts + glossary link (fixes internal linking).
8. **Final CTA** + footer.

JSON-LD on `/`: Organization (add `logo`, `sameAs` GitHub, `contactPoint`), WebSite with
`SearchAction` omitted (no public search), and **three** `SoftwareApplication` nodes (one per
product, `offers` omitted since pricing is quote-based).

---

## 4. Product landing pages (new) and nav

### `/product/mitre-coverage`
- H1 "MITRE ATT&CK coverage assessment, from rule export to board deck"
- Problem: SIEMs cover ~21% of ATT&CK techniques on average despite telemetry that could
  cover 90%+ (CardinalOps 2025). Manual mapping of hundreds of rules in a spreadsheet takes
  days and goes stale.
- What you upload / what you never upload (privacy notice text from MITRE_ASSESSMENT_PLAN §2).
- Pipeline in 5 steps (matches PPTX methodology slide): ingest → applicability → tagging
  ladder → coverage + detection strength → ranked gaps and roadmap.
- Outputs grid: PDF exec/detailed, XLSX tracker with Reference KQL, 18-slide PPTX, Navigator
  layer, Sentinel/Splunk live connectors with scheduled re-runs, trend between runs.
- Honest numbers: ATT&CK v19.1, 858 Enterprise techniques / 15 tactics; two numbers never
  one (your rules vs tool-native overlay); coverage is presence not efficacy.
- Sentinel workbook callout (free, in-tenant, funnels to full assessment) once
  `marketplace/sentinel/` ships.
- FAQ block (`FAQPage`): "Do you need my logs?", "Sentinel and Splunk only?", "How is N/A
  decided?", "Is coverage % the same as detection quality?"
- Effort/cost framing: replaces the hand-built spreadsheet + deck the VFQ engagement needed
  before productisation. Do not quote hours saved; no measured figure exists.

### `/product/code-security-review`
- H1 "AI-assisted code security review that never sees your client's code"
- Problem: manual pentest/code review engagements run $10k–$35k and weeks; scanner output is
  not a deliverable.
- How it works: download kit → scan locally on your OpenRouter key with a cost estimate
  first → upload `findings.json` zip → register, drawer, exploit chains, XLSX, PPTX.
- Honest numbers: NodeGoat golden scan 88 raw → 29 verified findings, 6 chains, ≈$4, 103 min.
  "A small repo costs a few dollars and takes 30–120 minutes."
- Attribution + non-affiliation: "Built on Visa's open-source Vulnerability Agentic Harness
  (Apache-2.0). ScopeWise is not affiliated with or endorsed by Visa, Inc."
- Caveats verbatim from the reference: LLM-driven SAST, no published precision/recall,
  findings are triage candidates, never DAST.
- FAQ: "Does my code leave my network?", "What does a scan cost?", "Which languages?", "Can
  the client run it?" (no, v1 is consultant-run).

### `/product/sow-review`
Rename existing `/product` (301). Reuse its content, add: Risk by Area, evidence anchoring,
projects and rollups, OCR, PDF report with audit footer. Keep the "not SME-validated severity"
caveat out of marketing but never claim "certified" or "legal advice".

### Solutions (add two, reuse the existing template with FAQ block)
- `/solutions/for-security-consultancies` (MITRE + Code Review together, MDR/SOC advisory).
- `/solutions/for-appsec-consultants` (Code Review).

### Nav and footer
- Header: Products (dropdown: SOW & RFP Review · MITRE ATT&CK Coverage · Code Security
  Review) · Solutions · Resources (Blog, Glossary) · Pricing · Sign in.
- Footer: three product columns + Company (About, Contact, Privacy, Terms) + Resources.
  Stack on mobile. Footer text uses the darker token.
- Add a `/terms` page (currently missing; privacy exists).

---

## 5. Cost and effort story: what we may say

Use third-party, sourced statistics for the pain; use our own measured, documented numbers
for the product. Never invent "hours saved".

| Claim | Source | Use where |
|---|---|---|
| Poor contract management costs ~9% of annual revenue (source wording; not "contract value") | WorldCC / IACCM "The Cost of a Contract" | SOW card, homepage stat tile |
| Enterprise SIEMs detect ~21% of ATT&CK techniques on average; telemetry exists for 90%+ | CardinalOps 2025 State of SIEM | MITRE page hero, homepage tile |
| Average breach cost $4.99M global, $11.5M US (2026) | IBM Cost of a Data Breach 2026 | MITRE/Code pages |
| Manual internal pentest engagement $7k–$35k (source-checked 2026-09-12: Bright Defense states $7,000–$35,000 internal; Blaze gives $10k–$50k cloud — quote Bright Defense only) | BrightDefense pricing guide | Code Review page |
| 29/29 recall, 0 rule-engine false positives on the labelled SOW set | ACCURACY_BASELINE_2026_07_22.md | SOW page, phrased "on our labelled test set" |
| Deterministic pre-pass cut AI tagging calls 63% with zero false positives | IMPLEMENTATION_PROGRESS Phase 6 | MITRE page |
| NodeGoat: 88 → 29 findings, ≈$4, 103 min | CODE_REVIEW_MODULE_REFERENCE §9 | Code Review page |

**Do not claim:** SOC 2, PWA/offline, SSO, WCAG AA conformance (not audited), legal advice,
SME-validated severity, industry-standard scoring, server-side scanning, Elastic connector,
any customer name (VFQ is under NDA and gitignored), any testimonial.

Effort framing that is safe: "replaces the spreadsheet-and-deck workflow" and "report is
generated, not assembled", with a screenshot of the PPTX/XLSX as proof.

---

## 6. SEO guideline (living section of the doc)

**Architecture:** homepage = umbrella; one landing page per product under `/product/*`;
audience pages under `/solutions/*`; informational content under `/resources/*`; comparison
pages under `/compare/*` (Phase 3 of the existing roadmap, still blocked on legal sign-off).

**Target keywords by page**

| Page | Head term | Long-tail |
|---|---|---|
| `/product/sow-review` | SOW review AI, AI contract review software | statement of work risk assessment, SOW red flags checklist |
| `/product/mitre-coverage` | MITRE ATT&CK coverage assessment tool | detection gap analysis, SIEM coverage MITRE, Sentinel ATT&CK coverage, ATT&CK Navigator layer generator |
| `/product/code-security-review` | AI code security review | agentic SAST report, code review deliverable for consultants, SARIF to report |
| `/solutions/for-security-consultancies` | MDR detection coverage report | SOC maturity assessment deliverable |
| Blog (new) | cost of poor contract management; SIEM detection coverage percentage; what is detection engineering coverage; SARIF explained | one post per pillar per month |
| `/compare/*` (later) | SOWaudit alternative, ATT&CK Navigator alternative, Semgrep vs agentic review | needs legal review first |

**Technical rules**
- `robots.ts`: disallow `/mitre`, `/codereview`, `/admin`, `/login`, `/api`. Remove `/pricing`
  from disallow. Keep AI-crawler allowlist as is.
- `sitemap.ts`: add `/privacy`, `/terms`, `/pricing`, new product and solution pages; give
  each entry a real `lastModified` from a constant per page or the blog post date.
- Metadata: unique title ≤60 chars and description ≤155 chars per page; `alternates.canonical`
  everywhere (already the pattern); OG image on every page; `summary_large_image`.
- Schema: Organization + WebSite on `/`; `SoftwareApplication` per product page;
  `FAQPage` on every page with an FAQ block; `BlogPosting` with a `Person` author,
  `dateModified`, `image`; `DefinedTerm` with a proper `DefinedTermSet` object;
  `BreadcrumbList` on nested pages.
- E-E-A-T: named author with title on every blog post and on `/about` (Person schema);
  methodology page links to SCORING_METHODOLOGY-derived public explanation; reference
  the public GitHub repo on `/about`.
- Contrast: all body text ≥ 7:1 target (AAA) via the token change; verify with Lighthouse
  accessibility and axe; footer ≥ 4.5:1.
- Core Web Vitals: re-run Lighthouse after the font change (Inter adds a request; use
  `display: swap` and subset latin).
- Internal linking: every product page links to its solution pages, its FAQ glossary
  terms, and two blog posts; header exposes Resources.
- Measurement: GA4 events already fire via `CtaClickTracker`; add event names per product
  card click and per pillar CTA so attribution per pillar is visible in GSC/GA4.

**Content cadence:** one post per pillar per month; MITRE and Code Review currently have zero
posts. First four: "How much of MITRE ATT&CK does your SIEM really cover", "Reading a
Navigator layer", "What a code security review deliverable should contain", "SOW vs RFP
review: what changes".

---

## 7. Implementation sequence

1. [x] Commit the pending privacy page + footer link — `2608b7d` (2026-09-12).
2. [x] Token + font + OG image + robots/sitemap fixes — `8d5fdb6`. Inter is loaded via `next/font/google` (display swap, latin); tailwind `sans` reads `--font-inter`.
3. [x] New homepage — `bb1ac3f` (+ `68ec0bd` statistic wording, `0384a46` title).
4. [x] Two new product landing pages + rename `/product` with redirect — `eeb7aec`.
5. [x] Header/footer rework, `/terms`, pricing indexed and linked — `71ef549`. **Reversed `a6a5bdb` (2026-09-12): pricing unlinked, noindex, out of sitemap; page kept for direct sharing.**
6. [x] Two new solution pages, glossary schema fix, BlogPosting image/dateModified/publisher — `3f555e7`, `3ebd27d`. **Decided 2026-09-12:** the author is "ScopeWise Team"; BlogPosting `author` stays the Organization by choice. Only the `/about` name-rationale paragraph remains open.
7. [ ] First four blog posts.
8. [ ] `/compare/*` once legal sign-off exists.

Follow-ups from the implementation session, done 2026-09-12: [x] product screenshots for MITRE (ACME v2 sample) and Code Review (NodeGoat golden fixture) on the homepage cards and product heroes (`29dbd8c`); [ ] SOW results screenshot (needs a review run; OpenRouter key at its limit); [x] per-pillar OG images (`fdfaba3`); [x] `/about` name-rationale paragraph (`db30589`).

Each step is a separate commit; `npx tsc --noEmit` clean before each; Lighthouse + axe after 2
and 3.

---

## 8. Verification (when implemented)

- Lighthouse SEO ≥ 95 and Accessibility ≥ 95 on `/`, each product page, `/about`.
- Rich Results Test passes for every JSON-LD block; no warnings on `FAQPage`/`SoftwareApplication`.
- `curl -I` on `/mitre` and `/codereview` shows they are disallowed in `robots.txt`; sitemap
  lists all new pages; GSC "URL inspection" shows the three product pages indexable.
- Contrast: every `text-muted-foreground` sample ≥ 7:1 via axe.
- Manual read-through: no forbidden claims from §5; VVAH attribution + non-affiliation line
  present on the Code Review page.
- Grep the marketing tree for "EDGP" and for banned AI-tell phrases (reuse the MITRE wording
  test list).

## Output of this planning task

Write the above (sections 1–8) to `docs/planning/HOMEPAGE_BRANDING_SEO_PLAN.md`, add a
pointer line in `docs/IMPLEMENTATION_PROGRESS.md` and in `docs/planning/SEO_STRATEGY.md`
("superseded for homepage/positioning by HOMEPAGE_BRANDING_SEO_PLAN.md"). No app code changes.
