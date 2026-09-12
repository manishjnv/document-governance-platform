# Session handoff — 2026-09-12: Homepage branding + SEO plan implemented (steps 1-6)

**Headline:** the public marketing site now presents ScopeWise as a
three-product platform (SOW & RFP Review · MITRE ATT&CK Coverage · Code
Security Review) per `docs/planning/HOMEPAGE_BRANDING_SEO_PLAN.md`. Ten
code commits on master, **committed but not pushed and not deployed**. Local
`next build` green, `tsc --noEmit` clean, Lighthouse 12 SEO/Accessibility/
Best-practices = 100/100/100 on `/`, the three product pages and `/about`.
No apps/api change, so the backend suite baseline (973/7) is untouched.

## Commits in order (all on master, local only)

| Commit | Step | What |
|---|---|---|
| `2608b7d` | 1 | Privacy page, footer link, sitemap entry (pending work from 08-20) |
| `8d5fdb6` | 2 | `--muted-foreground` 215 22% 32% (8.4:1 on white, 7.7:1 on the muted band); Inter via `next/font/google` (`display: swap`, latin, `--font-inter` in tailwind `sans`); `public/og-default.png` from `scripts/generate_og_image.py`; `summary_large_image`; robots disallows `/mitre` `/codereview` `/admin` `/login` `/api`, `/pricing` crawlable; sitemap real lastmod per page / blog date |
| `bb1ac3f` | 3 | New homepage: hero, three product cards (`data-product` attr for GA4), how-it-works, three sourced stat tiles, trust band, audiences, latest-3 blog strip, final CTA; JSON-LD Organization (logo/sameAs/contactPoint) + WebSite + 3 SoftwareApplication, no offers |
| `eeb7aec` | 4 | `/product` → `/product/sow-review` (308 via next.config `redirects`) with Risk-by-Area, projects, OCR, audit-footer, 29/29 labeled-set note; new `/product/mitre-coverage` and `/product/code-security-review` (FAQPage + SoftwareApplication + BreadcrumbList; Visa attribution + non-affiliation line verbatim) |
| `71ef549` | 5 | `MarketingNav` client component: Radix Products dropdown (aria-expanded / aria-haspopup, Enter opens, first item focused) + mobile menu button/panel; 4-column footer (2-up on phones); `/terms`; `/pricing` noindex removed, copy covers three products; sitemap entries |
| `3f555e7` | 6 | `/solutions/for-security-consultancies`, `/solutions/for-appsec-consultants` (FAQPage + BreadcrumbList); BlogPosting gains url/mainEntityOfPage/image/dateModified/publisher (`updatedDate?` field on `BlogPost`); DefinedTerm `inDefinedTermSet` is a DefinedTermSet object; two pre-existing "leverage" rewordings |
| `3ebd27d` | 6 | Glossary "highest-leverage" reword that missed the previous commit |
| `68ec0bd` | 3/4 | Statistic wording aligned to sources: WorldCC "9% of annual revenue", Bright Defense "$7,000–$35,000 internal pentest" (Blaze dropped: its range is $10k–$50k cloud) |
| `0384a46` | 3 | Homepage `<title>` = "ScopeWise: risk reviews for contracts, detections and code" (58 chars; the root segment does not receive the layout title template) |
| (docs) | exit | Plan §7 ticks, progress index, this handoff, kickoff prompt |

`ee19ff9` (MITRE demo assessments) landed on master from another session
mid-way; it is not part of this work.

## Verification (against `next start` of the local build)

- Lighthouse 12.8.2 desktop, `--only-categories=seo,accessibility,best-practices`:
  `/` 100/100/100 · `/product/sow-review` 100/100/100 · `/product/mitre-coverage`
  100/100/100 · `/product/code-security-review` 100/100/100 · `/about` 100/100/100.
  Lighthouse 13.x under Node 20 errors on the `canonical` audit (`URL.parse is
  not a function`) and reports SEO as null — use `npx lighthouse@12.8.2` until
  Node ≥ 22.
- JSON-LD: every block on `/`, three product pages, two new solution pages,
  a blog post, a glossary term and a use-case page parses and carries the
  required fields (structural check with Playwright; Google Rich Results Test
  not run — do it once deployed). Only warning: BlogPosting `author` is still
  an Organization (named author pending, see Open).
- `robots.txt` shows the eleven disallows and no `/pricing`; `/product` → 308
  → `/product/sow-review`; `sitemap.xml` 42 URLs, every new page present,
  lastmod constant per page (8 dated 2026-09-12, rest 07-20 / 08-01 / 08-20).
- Playwright 1440px and 390px full-page screenshots of `/` and each product
  page: `scrollWidth == innerWidth` at 390 on all four (no horizontal
  overflow). Mobile menu: `aria-expanded` toggles, 6 links in the panel.
- Contrast (computed): token on white 8.38:1, on `bg-muted/30` 7.66:1,
  on the primary tint 7.81:1; footer uses the same token (≥ 4.5:1 met).
- Copy gates before each commit: `EDGP` = 0 hits in the marketing tree;
  banned AI-tell regex from `apps/api/tests/test_mitre_wording.py` = 0 hits
  (three pre-existing hits reworded); forbidden-claim grep (SOC 2, SSO, PWA,
  WCAG, certified, testimonial, trusted by, hours saved, Elastic) = 0 hits.
- Gotcha hit twice: after `next build`, a `next start` left running from the
  previous build keeps serving the old chunk names, so every static chunk
  returns 400, nothing hydrates and Lighthouse best-practices drops. Kill the
  listener on the port (`Get-NetTCPConnection -LocalPort 3123`) before
  restarting.

## Statistics on the site and their sources

| Where | Statement | Source | URL |
|---|---|---|---|
| `/` stat tile | ~9% of annual revenue lost to poor contract management | WorldCC / IACCM, "The Cost of a Contract" | https://www.worldcc.com/resource/the-cost-of-a-contract-iaccm-research-report.html |
| `/` tile, `/product/mitre-coverage` | SIEMs detect 21% of ATT&CK techniques; telemetry exists for 90%+ | CardinalOps, 2025 State of SIEM Detection Risk (press release) | https://www.prnewswire.com/news-releases/enterprise-siems-miss-79-of-mitre-attck-techniques-used-by-adversaries-according-to-cardinalops-5th-annual-report-302473779.html |
| `/` tile, `/product/code-security-review` | Manual internal penetration test $7,000–$35,000 | Bright Defense, penetration testing pricing guide | https://www.brightdefense.com/resources/penetration-testing-pricing/ |
| `/product/code-security-review` | Breach cost $4.99M global, $11.5M US | IBM Cost of a Data Breach Report 2026 | https://www.ibm.com/reports/data-breach (figures confirmed on https://databreachcost.com/report/2026) |
| `/product/code-security-review` | NodeGoat: 88 → 29 findings, 6 chains, ≈$4, 103 min, 63 files, 30–120 min for a small repo | ScopeWise golden fixture | `docs/sample/CodeReview_Sample/real/nodegoat/README.md`, `CODE_REVIEW_MODULE_REFERENCE.md` §9 |
| `/product/mitre-coverage` | ATT&CK v19.1, 858 Enterprise techniques / 15 tactics; 63% fewer AI calls with zero false positives | Pinned dataset + Phase 6 test | `MITRE_MODULE_REFERENCE.md` (data table), `IMPLEMENTATION_PROGRESS.md` Phase 6; https://attack.mitre.org/ |
| `/product/sow-review` | 29 of 29 ground-truth findings, zero rule-engine false positives, labeled set | Accuracy baseline | `docs/planning/ACCURACY_BASELINE_2026_07_22.md` |

## Open / next

1. **Push + deploy on the user's say-so** (standard VPS loop; no migration).
   Docker build needs network for `next/font/google` to fetch Inter.
2. **Blog `Person` author**: user must supply name + title; then replace the
   `TODO(author)` block in `resources/blog/[slug]/page.tsx`, add Person schema
   and the "Scope" name rationale on `/about`.
3. Step 7 (four blog posts, one per pillar) and step 8 (`/compare/*`, legal
   sign-off) are separate sessions.
4. Product screenshots (NodeGoat + ACME only) and per-pillar OG images.
5. Once live: Google Rich Results Test on the product pages, GSC URL
   inspection, Lighthouse against the VPS (font request + Cloudflare).

## Agent utilization

- Opus: plan/doc reads, steps 1-2 hands-on, diff review of every page, verification scripts, docs
- Sonnet: 7 page builds in two parallel waves (homepage, MITRE, code review, SOW move, nav/footer/terms, 2 solution pages) · reworked: N (US spelling and two source-wording fixes applied by Opus)
- Haiku: statistic source-URL verification (WebFetch) · reworked: N
- codex:rescue: n/a — no security/auth/classifier change (marketing site only)
- Tier 2/4 OpenRouter: n/a — excluded by the kickoff prompt
