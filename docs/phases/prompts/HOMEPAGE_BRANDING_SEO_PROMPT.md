# Kickoff prompt — implement the homepage branding + SEO plan

Copy everything below the line into a fresh Claude Code session opened at
`E:\code\DocumentGovernancePlatform`.

---

Implement `docs/planning/HOMEPAGE_BRANDING_SEO_PLAN.md` for the ScopeWise
marketing site (`apps/web`). Read that file fully first, then `CLAUDE.md`,
then `docs/planning/SEO_STRATEGY.md` header and
`docs/planning/seo/IMPLEMENTATION_ROADMAP.md` (Phases 1–2 are done; do not
redo them). Also read `docs/planning/CODE_REVIEW_MODULE_REFERENCE.md` §0–§1
and `docs/planning/MITRE_ASSESSMENT_PLAN.md` §2 so the product copy matches
what actually ships. Do not browse the app code beyond `apps/web` and those
docs; the plan already contains the audit.

## Decisions already made (do not re-open)

- Platform-umbrella positioning: hero sells one idea, three equal product
  cards (SOW & RFP Review · MITRE ATT&CK Coverage · Code Security Review).
- Pricing stays quote-based but `/pricing` becomes indexed and linked in nav.
- Darker body text via the single `--muted-foreground` token in
  `apps/web/app/globals.css` (`215 16% 47%` → `215 22% 32%`). No per-page
  colour edits.
- Tagline: "Evidence-based risk reviews. Contracts, detections, code."
- Reuse existing page content and components wherever the plan says so
  (6-agent grid, 3-step how-it-works, use-case/solution page template with
  its `FAQPage` JSON-LD, `MarketingHeader`/`MarketingFooter`,
  `CtaClickTracker`, per-page `metadata` pattern).

## Work in this order, one commit per step, do NOT push or deploy

1. Commit the already-finished `apps/web/app/privacy/page.tsx` and the
   one-line footer link in `apps/web/components/MarketingFooter.tsx`. Add
   `/privacy` to `sitemap.ts`. (Leave `marketplace/`,
   `scripts/generate_sentinel_workbook.py`, the two `acme_*_v2.xlsx` files
   and `scripts/generate_uploadsample.py` untouched and uncommitted; they
   belong to a different piece of work.)
2. Tokens and technical SEO, zero copy changes: darker
   `--muted-foreground`; load Inter via `next/font/google` with
   `display: swap` in `apps/web/app/layout.tsx` (or remove Inter from
   `tailwind.config.ts`, pick one and say which); add
   `apps/web/public/og-default.png` (1200×630, wordmark + tagline, generate
   with a script, no stock imagery) and set `openGraph.images` +
   `twitter.card: 'summary_large_image'` in root metadata; `robots.ts`
   disallow `/mitre`, `/codereview`, `/admin`, `/login`, `/api`, remove
   `/pricing`; `sitemap.ts` real `lastModified` per entry (constant per page
   or blog post date, never `new Date()`).
3. New homepage `apps/web/app/page.tsx` exactly per plan §3 (hero, three
   cards, how-it-works, three sourced stat tiles from §5, trust band, who
   it is for, resources strip with latest 3 posts, final CTA). JSON-LD:
   Organization with `logo`/`sameAs`/`contactPoint`, WebSite, three
   `SoftwareApplication` nodes, no `offers`.
4. Product pages: move `/product` to `/product/sow-review` with a permanent
   redirect in `next.config`; create `/product/mitre-coverage` and
   `/product/code-security-review` per plan §4, each with `FAQPage` +
   `SoftwareApplication` + `BreadcrumbList` JSON-LD and the FAQ questions
   listed there. The Code Security Review page must carry verbatim: "Built
   on Visa's open-source Vulnerability Agentic Harness (Apache-2.0).
   ScopeWise is not affiliated with or endorsed by Visa, Inc."
5. Header with a Products dropdown (accessible: keyboard + `aria-expanded`),
   Solutions, Resources, Pricing, Sign in; footer with product/company/
   resources columns that stack on mobile; new `/terms` page; remove the
   `noindex` from `/pricing`.
6. Two new solution pages (`/solutions/for-security-consultancies`,
   `/solutions/for-appsec-consultants`) on the existing template; blog
   `BlogPosting` gets a `Person` author (ask me for the name and title
   before writing it, do not invent one), `dateModified`, `image`;
   glossary `inDefinedTermSet` becomes a `DefinedTermSet` object.
7. Stop there. Blog posts and `/compare/*` are separate sessions.

## Hard constraints

- Copy rules in plan §2 and §5 are binding. Only the statistics in the §5
  table may be quoted, each with its source named on the page. Never invent
  hours saved, customer names, logos, testimonials, SOC 2, PWA, SSO,
  WCAG conformance, certified or SME-validated severity, or server-side
  scanning. Grep the marketing tree for "EDGP" and for the banned AI-tell
  phrases in `apps/api/tests/test_mitre_wording.py` before each commit.
- Product screenshots: only from the NodeGoat golden fixture
  (`docs/sample/CodeReview_Sample/real/nodegoat/`) and the ACME MITRE sample
  (`docs/sample/MITRE_Sample/UploadSample/`). Never anything under
  `docs/sample/project/`.
- Every body-text sample must reach 7:1 contrast; footer 4.5:1 minimum.
- `cd apps/web && npx tsc --noEmit` clean before every commit. Run a local
  `next build` after steps 3 and 5. If `next dev`/`build` hangs at
  "Starting...", it is Windows Defender scanning `node_modules`; see the
  Testing section of `CLAUDE.md`.
- Delegation per the global playbook: Sonnet subagents for the page
  builds (one page per agent, give each the exact plan section, file
  paths, the copy rules, and require a unified diff + change log); Haiku for
  grep sweeps; you review every diff yourself before committing. No
  OpenRouter tiers for this work (public copy is fine, but the pages are
  load-bearing for the brand).
- Do not touch `apps/api`, `docs/planning/*_REFERENCE.md`, or anything
  under `apps/web/app/{mitre,codereview,dashboard,admin,upload,results,
  projects,versions,search}`.

## Verification before you report done

- Lighthouse SEO ≥ 95 and Accessibility ≥ 95 on `/`, the three product
  pages and `/about` (run against the local build, paste the scores).
- Rich Results Test or `schema-dts`-style validation passes for every
  JSON-LD block; paste any warning.
- `robots.txt` output shows the new disallows and no `/pricing`;
  `sitemap.xml` lists every new page with a real lastmod.
- Screenshots at 1440px and 390px of `/` and each product page (Playwright
  is already in the repo); no horizontal overflow at 390px.
- Table of every statistic used on the site with its source URL.

## Session exit

Update `docs/IMPLEMENTATION_PROGRESS.md` (new dated entry, replace the
"plan only" wording), tick completed steps in
`docs/planning/HOMEPAGE_BRANDING_SEO_PLAN.md` §7, write
`docs/phases/summaries/SESSION_HANDOFF_<date>_HOMEPAGE_BRANDING.md` with the
commit list and the 4-line agent-utilization footer. List commits made,
tests/type-check status, and the one next action (push + deploy on my say-so).
