# Session handoff — 2026-09-12: Content phase (pillar posts, first /compare page, licence)

**Headline:** first authority content for the two newer products plus the
one comparison page that needs no legal review. Seven commits on master,
**committed but not pushed and not deployed**. The four blog posts are
`pendingReview: true` (noindex, follow; excluded from the sitemap) and
**await the user's read-through**; flipping that flag is a separate
explicit instruction. Earlier in the same session the homepage-branding
work (`2608b7d`…`4d9c7ed`) was pushed and deployed to the VPS and
smoke-tested live (all new routes 200, `/product` 308, 42 sitemap URLs,
OG image served).

## Commits in order (all on master, local only)

| Commit | Step | What |
|---|---|---|
| `b48b510` | 1 | `BlogPost` gains `pillar` and product-page `relatedUseCase` targets (`RelatedPath`, `RELATED_LABELS`, `PILLAR_LABELS`); post page derives the related-link label from the path; `BlogList` client component with keyboard-accessible pillar chips (`aria-pressed`, `role=group`) and the byline; existing 8 posts tagged `sow` |
| `56b2e70` | 2 | Four posts appended to `blog/data.ts`, all `pendingReview: true` (see table) |
| `d09ce33` | 3 | `/compare/scopewise-vs-manual-review` (solution template, comparison table with `sr-only` caption and `scope=col`, "where a human still wins", 29/29 note, FAQ) with FAQPage + BreadcrumbList; header Resources becomes a dropdown (Blog, Glossary, compare page) via a shared `NavDropdown`; mobile panel gains a Resources block; footer + sitemap entries |
| `59e8f00` | 4 | Top-level `LICENSE`: proprietary, Foxfiber Retail LLP (user's choice), Apache-2.0 carve-out for `kit/vendor/`; Visa non-affiliation sentence beneath the kit description on `apps/web/app/codereview/page.tsx`; `kit.py` verified (not changed): `build_kit_zip()` copies every file in `kit/vendor/`, so LICENSE, NOTICE and THIRD_PARTY_LICENSES.md ship in kit.zip |
| `23f5af3` | 4 | Blog inline body links underlined (axe `link-in-text-block`) |
| (docs) | exit | Progress entry, roadmap + calendar ticks, this handoff |

## The four posts (all `pendingReview: true`)

| Slug | Pillar | Words (content fields) | Related link | Statistics used |
|---|---|---|---|---|
| `how-much-mitre-attack-does-your-siem-cover` | mitre | 981 | `/product/mitre-coverage` | CardinalOps 21% / 90%+; ATT&CK v19.1, 858 techniques / 15 tactics; hypothetical worked example clearly labelled |
| `reading-an-attack-navigator-layer` | mitre | 1013 | `/product/mitre-coverage` | layer format 4.5; ATT&CK v19.1; hypothetical example |
| `what-a-code-security-review-deliverable-should-contain` | codereview | 1024 | `/product/code-security-review` | NodeGoat 88 → 29, 6 chains, ≈$4, 103 min, 63 files; Bright Defense $7,000–$35,000; Visa attribution + non-affiliation sentence verbatim |
| `sow-vs-rfp-review-what-changes` | sow | 952 | `/use-cases/rfp-review` | 7 RFP rules / 20 SOW rules; six agents; FAR Part 15 named |

Author string is "ScopeWise Team" (what every existing post uses). The
kickoff prompt assumed BlogPosting already emits a `Person` author; it does
not — the schema author is still the Organization until a real name and
title are supplied (see the homepage-branding handoff, open item 2).

## Verification (local `next build` + `next start`)

- `tsc --noEmit` clean before every commit; `next build` green after step 3
  (64 static pages; the `themeColor` warning is the pre-existing root
  metadata, unchanged).
- Each post: HTTP 200, `<meta name="robots" content="noindex, follow">`,
  one h1, BlogPosting JSON-LD with `dateModified`, absent from
  `sitemap.xml` (43 URLs; compare page present).
- Compare page: FAQPage (4 Question/Answer items) + BreadcrumbList (2
  positioned items) parse with all required fields; no `robots` meta;
  `scrollWidth == innerWidth` at 390px.
- Resources dropdown: `aria-expanded` false → true on Enter, items Blog /
  Glossary / ScopeWise vs manual review.
- Blog chips: Tab, Tab, Enter selects "MITRE ATT&CK Coverage",
  `aria-pressed` moves, list 12 → 2 posts.
- Lighthouse 12.8.2 desktop: `/resources/blog` SEO 100 / A11y 100;
  `/compare/scopewise-vs-manual-review` 100 / 100; the MITRE post A11y 96
  → the only failing audit (links by colour) fixed in `23f5af3`; its SEO 66
  is the intended noindex.
- Copy gates: banned AI-tell regex + "EDGP" + forbidden-claim grep = 0 hits
  across the four posts, compare page, nav and BlogList.

## Statistics used this session and their sources

| Statement | Source | URL |
|---|---|---|
| SIEMs detect ~21% of ATT&CK techniques; telemetry exists for 90%+ | CardinalOps, 2025 State of SIEM Detection Risk | https://www.prnewswire.com/news-releases/enterprise-siems-miss-79-of-mitre-attck-techniques-used-by-adversaries-according-to-cardinalops-5th-annual-report-302473779.html |
| ATT&CK v19.1, 858 Enterprise techniques / 15 tactics | pinned dataset (`MITRE_MODULE_REFERENCE.md`) | https://attack.mitre.org/ |
| Navigator layer format 4.5 | `apps/api/app/mitre/navigator.py` | https://github.com/mitre-attack/attack-navigator |
| NodeGoat 88 → 29 findings, 6 chains, ≈$4, 103 min, 63 files | ScopeWise golden fixture README | `docs/sample/CodeReview_Sample/real/nodegoat/README.md` |
| Manual internal pentest $7,000–$35,000 | Bright Defense pricing guide | https://www.brightdefense.com/resources/penetration-testing-pricing/ |
| 7 RFP rules / 20 SOW rules; six agents; 30-second agent cap | `apps/api/app/rules/builtin.py`, `SEO_STRATEGY.md` §2, use-case FAQ | repo |
| 29 of 29 ground-truth findings, zero rule-engine false positives | `docs/planning/ACCURACY_BASELINE_2026_07_22.md` | repo |
| FAR Part 15 as RFP structure | `docs/planning/SCORING_METHODOLOGY.md` | https://www.acquisition.gov/far/part-15 |

## Open / next

1. User reads the four posts at `/resources/blog/<slug>` (local build or
   after deploy; they render while noindexed). On approval, remove
   `pendingReview: true` from each in `blog/data.ts` — they enter the
   sitemap automatically. Separate explicit instruction.
2. Push + deploy on the user's say-so (no migration; no apps/api runtime
   change — only the LICENSE and a web page).
3. Named `Person` author + title for BlogPosting and `/about` still pending.
4. `/compare/[competitor]` stays blocked on legal sign-off;
   `/resources/templates` and case studies untouched by design.

## Agent utilization

- Opus: deploy, plan/doc reads, step 1 and step 4 hands-on, nav/footer/sitemap wiring, review of every post and the compare page, verification scripts, docs
- Sonnet: 4 blog posts + compare page in one parallel wave · reworked: N (one unescaped apostrophe fixed by Opus)
- Haiku: n/a — grep sweeps were single commands, cheaper to run inline
- codex:rescue: n/a — no security/auth/classifier change
