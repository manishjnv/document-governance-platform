# Kickoff prompt — content phase: pillar blog posts, comparison page, licence loose ends

Run AFTER `HOMEPAGE_BRANDING_SEO_PROMPT.md` has landed (the product landing
pages at `/product/mitre-coverage` and `/product/code-security-review` must
exist, since every post below links to one of them). Copy everything below
the line into a fresh Claude Code session opened at
`E:\code\DocumentGovernancePlatform`.

---

## Context you need before touching anything

Read in this order: `CLAUDE.md`; `docs/planning/HOMEPAGE_BRANDING_SEO_PLAN.md`
§2 (brand voice), §5 (the only statistics we may quote and the do-not-claim
list) and §6 (keyword map, content cadence, technical SEO rules);
`docs/planning/seo/CONTENT_CALENDAR.md` (rows 17–18 and the "What NOT to do"
section); `docs/planning/seo/IMPLEMENTATION_ROADMAP.md` Phase 3;
`docs/planning/PROMPT_ENGINEERING_GUIDE.md` §"Division of labor" (why the
rule engine vs agents split exists, so the AI post is accurate);
`docs/planning/MITRE_MODULE_REFERENCE.md` §1, §6, §7, §11 (invariants,
coverage states, tagging ladder, exports); `docs/planning/
CODE_REVIEW_MODULE_REFERENCE.md` §0, §1, §5, §9 (what the module is and is
not, exports, NodeGoat golden numbers); `apps/api/app/codereview/kit/
README.md`. Skim the last session handoff in `docs/phases/summaries/` so you
know what the homepage session changed.

State of the site when this runs: umbrella homepage, three product landing
pages under `/product/*`, five solution pages, 8 SOW-only blog posts in
`apps/web/app/resources/blog/data.ts` (hand-coded TypeScript, no CMS, by
design), 15 glossary terms, `/pricing` indexed, `/privacy` and `/terms`
live, blog `BlogPosting` schema already emits a `Person` author,
`dateModified` and `image` (done in the homepage session). MITRE and Code
Security Review have **zero** blog posts. No `/compare/*` page exists.

Blog data shape (`apps/web/app/resources/blog/data.ts`): `BlogPost` with
`slug`, `title`, `dek`, `publishedDate`, optional `updatedDate`, `author`,
`body: BlogSection[]` (heading + one prose paragraph each),
`relatedUseCase` (a narrow string-literal union of the three SOW use-case
paths), optional `pendingReview` (true blocks indexing and sitemap inclusion).

## Goal

Ship the first authority content for the two newer products, the one
comparison page that needs no legal review, and close two licence-review
loose ends. Everything is committed locally; nothing is pushed or deployed
until I say so.

## Work in this order, one commit per step

1. **Widen the blog model, no copy yet.** In `data.ts` change
   `relatedUseCase` to accept a product page too (`'/product/sow-review' |
   '/product/mitre-coverage' | '/product/code-security-review'` in addition
   to the three use-case paths) and add an optional `pillar: 'sow' | 'mitre'
   | 'codereview'` used by the blog index for a filter chip row. Update
   `[slug]/page.tsx` to render the related link label from the path. Blog
   index gets the filter chips and the `Person` author byline. `tsc` clean.

2. **Four posts, one per pillar plus one cross-pillar, written as
   `pendingReview: true`** (noindex until I approve, per the editorial-gate
   rule in memory). Each post: 900–1400 words, 5–7 sections, one `heading`
   per section, prose paragraphs only (the renderer has no lists), a
   concrete worked example, and one sentence at the end pointing to the
   related product page. Author = the `Person` name/title I gave the homepage
   session (read it from the existing posts; do not invent a new one).
   - `how-much-mitre-attack-does-your-siem-cover` — pillar `mitre`. Hook on
     the CardinalOps 2025 finding (~21% average coverage, telemetry for
     90%+), explain coverage states covered / partial / not covered / not
     applicable, why N/A must leave the denominator with a printed reason,
     why "two numbers, never one" (your rules vs tool-native overlay), and
     why coverage is presence not efficacy (detection strength is separate).
     Related: `/product/mitre-coverage`. Target: "MITRE ATT&CK coverage
     assessment", "SIEM detection coverage percentage".
   - `reading-an-attack-navigator-layer` — pillar `mitre`. What a Navigator
     layer JSON is (format 4.5), how to read colour, score and the
     `enabled:false` comment convention for N/A, how to compare two layers
     across runs, common misreadings (sub-technique rollup, revoked
     techniques). Related: `/product/mitre-coverage`. Target: "ATT&CK
     Navigator layer", "detection gap analysis".
   - `what-a-code-security-review-deliverable-should-contain` — pillar
     `codereview`. Why raw SAST/agentic scanner output is not a deliverable;
     the decision order a finding should be written in (what is wrong, why
     it matters, how to fix, how it is exploited, preconditions); exploit
     chains and "fewest fixes that break every chain"; tracker columns
     (owner, status, target date); the honest caveats: LLM-driven SAST is
     non-deterministic, findings are triage candidates, never DAST. Use the
     NodeGoat golden numbers (88 raw → 29 findings, 6 chains, ≈$4, 103 min)
     and name the scanner with the exact attribution + non-affiliation line
     from the plan. Related: `/product/code-security-review`. Target: "code
     security review report", "AI code security review".
   - `sow-vs-rfp-review-what-changes` — pillar `sow`, bridges to the umbrella.
     What differs when the document is an RFP (FAR Part 15 evaluation-
     criteria structure, 7 RFP rules vs 20 SOW rules, per-agent RFP prompt
     branches), what stays the same (evidence per finding, risk by area).
     Close with one paragraph on why the same evidence-first discipline is
     what the MITRE and code modules do. Related: `/use-cases/rfp-review`.
   Every statistic must come from plan §5 and name its source inline. No
   customer names, no hours-saved claims, no "industry standard".

3. **`/compare/scopewise-vs-manual-review`** (content-calendar row 17;
   explicitly no legal gate because it names no competitor). New route
   `apps/web/app/compare/scopewise-vs-manual-review/page.tsx` using the
   solution-page template pattern: H1 "ScopeWise vs manual SOW review,
   side by side", a comparison table (dimensions: time to first read,
   consistency across reviewers, evidence traceability, re-review after
   redlines, what it costs, what it cannot do), an honest "where a human
   still wins" section (severity judgement is not SME-validated, legal
   advice, negotiation), FAQ block with `FAQPage` JSON-LD, `BreadcrumbList`,
   CTA. Add to sitemap, header Resources dropdown and footer. Do NOT create
   any `/compare/[competitor]` page; legal sign-off is required first.

4. **Licence loose ends from the 2026-09-12 review.** Add a top-level
   `LICENSE` to the repo stating proprietary, all rights reserved, Foxfiber
   Retail LLP (check `docs/` and `package.json` for the exact legal entity
   name and ask me if unclear), with a one-paragraph note that
   `apps/api/app/codereview/kit/vendor/` contains Apache-2.0 third-party
   code under its own licence. Add the "not affiliated with or endorsed by
   Visa, Inc." sentence to `apps/web/app/codereview/page.tsx` (the authed
   landing) beneath the existing kit description, matching the wording on
   the public product page. Confirm `GET /api/v1/codereview/kit.zip` still
   ships `vendor/LICENSE` and `vendor/NOTICE` (it does today via the
   `vendor/` copy loop in `apps/api/app/codereview/kit.py`; just verify, do
   not change).

5. **Stop.** Do not start `/compare/[competitor]`, `/resources/templates`,
   case studies, or any new product feature.

## Hard constraints

- Brand voice per plan §2: plain language, no AI-tell phrases (grep new copy
  against the banned list in `apps/api/tests/test_mitre_wording.py`), no
  em-dash pairs used as a tic, every number sourced.
- Reuse existing components and the existing page templates. No new
  dependencies, no CMS, no MDX.
- `cd apps/web && npx tsc --noEmit` clean before every commit; `next build`
  after step 3. Defender note in `CLAUDE.md` Testing section if the build
  hangs.
- Do not touch `apps/api` except the two files in step 4, and do not touch
  `docs/planning/*_REFERENCE.md`. Never `git add docs/` wholesale.
- Delegation: one Sonnet subagent per blog post with the exact brief above,
  the plan §2/§5 text pasted in, the `BlogPost` type, and "return the full
  TypeScript object literal + a 100-word summary of sources used". Review
  every post yourself for forbidden claims before it lands. Haiku for the
  banned-phrase and "EDGP" grep sweeps.

## Verification before you report done

- All four posts render at `/resources/blog/<slug>`, show `noindex` in the
  HTML head, and are absent from `sitemap.xml` (pendingReview gate works).
- `/compare/scopewise-vs-manual-review` renders, is in `sitemap.xml`,
  `FAQPage` + `BreadcrumbList` validate with no warnings.
- Blog index filter chips work with keyboard; Lighthouse Accessibility ≥ 95
  on the index and one post.
- A table of every statistic used in the new content with its source URL.
- Word count per post.

## Session exit

New dated entry in `docs/IMPLEMENTATION_PROGRESS.md`; tick the compare row
in `docs/planning/seo/IMPLEMENTATION_ROADMAP.md` Phase 3 and rows 17 in
`CONTENT_CALENDAR.md`; handoff summary
`docs/phases/summaries/SESSION_HANDOFF_<date>_CONTENT_PHASE.md` with commit
list and the 4-line agent-utilization footer. Tell me: commits made,
type-check/build status, and that the four posts are waiting on my
read-through before `pendingReview` is flipped (that flip is a separate,
explicit instruction from me).
