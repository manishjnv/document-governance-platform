# Session handoff — 2026-09-12 — Wrap-up: admin tier toggle, compare pages, screenshots, deploy

**Headline:** everything from the day's runbook is live except the items the
owner deferred. Deployed SHA on the VPS: **`29dbd8c`**. Working tree clean.

## Commits since the last deploy (`4ddfd9f`)

| SHA | What | Session |
|---|---|---|
| `5ed1053`…`4ae0c0b` | Code review hardening: single-source highlight words, VVAH 1.3.0 schema fixture, deck one-liner fixes (RCA #22–26), docs consolidated | hardening session |
| `22c88a9` | Admin: organisation tier toggle for the run-entitlement gate (platform-admin PATCH + orgs table on `/admin`) | wrap-up session |
| `f19ae4b` | Marketing: competitor comparison pages (SOWaudit, ATT&CK Navigator, Semgrep) + `/compare` index | this session (worktree branch, ff-merged) |
| `fdfaba3` | Marketing: per-pillar OG images on the three product pages; host name dropped from all OG images | wrap-up session |
| `db30589` | Marketing: `/about` name-rationale paragraph and links to the three products | wrap-up session |
| `29dbd8c` | Marketing: product screenshots on homepage cards and the MITRE and Code Review heroes | this session, finishing the wrap-up session's step 4 |

Earlier the same day (already documented): run-entitlement gate `329d10b`,
pricing unlink `a6a5bdb`, and their handoff
`SESSION_HANDOFF_2026_09_12_ENTITLEMENT_PRICING.md`.

## Deploys this session

1. `f19ae4b` — compare pages. Web + api rebuilt, all containers healthy.
2. `29dbd8c` — screenshots. Web rebuilt, healthy.
Standard loop per `CLAUDE.md`; no migration newer than 039; scopewise-*
containers only.

## Live smoke (after `29dbd8c`)

| Check | Result |
|---|---|
| `/compare`, `/compare/sowaudit-alternative`, `/compare/attack-navigator-alternative`, `/compare/semgrep-alternative` | 200, correct titles |
| sitemap contains 5 compare URLs, 0 pricing | yes |
| `/pricing` | 200, `noindex` meta present, unlinked |
| `/screens/mitre-coverage-heatmap-960.webp`, `/screens/code-review-findings-drawer-960.webp` | 200, 64 KB / 44 KB |
| `/og-default.png`, `/og-sow-review.png`, `/og-mitre-coverage.png`, `/og-code-security-review.png` | 200, 36–38 KB |
| `/`, `/product/mitre-coverage`, `/product/code-security-review`, `/about` | 200; `og:image` absolute on product pages |
| Lighthouse / PageSpeed | **not run**: PageSpeed API daily quota exhausted for this account. Rerun 2026-09-13. Risk is low: images are ≤64 KB, lazy on the homepage, `priority` + fixed dimensions on the two heroes. |

## Comparison pages (`f19ae4b`)

Built on a worktree branch while another session held the main tree, then
fast-forward merged (no overlapping files). Legal sign-off given by the
owner 2026-09-12. Every competitor statement is quoted or paraphrased from
that competitor's own site fetched the same day, cited in a code comment
beside each `ROWS` array and repeated on the page; unknowns read "not
stated publicly". No pricing links; CTAs go to `/login` and `/contact`.
Trademark and non-affiliation line on each page; the exact Visa/VVAH
sentence on the Semgrep page. Nav Resources dropdown and footer collapse
to one "Compare" entry pointing at the index.

## Prod state to remember

- Run-entitlement gate is live. All nine prod orgs are still `free`; only
  the platform admin can run. The `/admin` page now has the tier select;
  the owner has not yet chosen which orgs to enable. Two access requests
  arrived by email (talk2maq, rajendra19sep) per the admin screenshot.
- OpenRouter key limit: deferred by the owner. Reviews and MITRE AI tagging
  fail until raised; deterministic MITRE runs still work.
- The SOW product card has no screenshot (a review run needs the AI key).

## Design deliverable (no code)

Enterprise-grade redesign canvas of the five authenticated screens, one
committed direction plus two low-fi alternates and per-screen critique
notes: https://claude.ai/code/artifact/f3b280f4-455c-49e4-9d4e-33cf9088d7fa
Tokens matched to `globals.css` / `tailwind.config.ts` / `components/ui`
so it can be built page by page. Generator and artboards live in the
session scratchpad only (design content, not repo deliverable).

## Deferred by owner (no action)

OpenRouter key limit and credit top-up · Sentinel workspace and workbook
live test · AI-quota error message in the app · PPTX org branding.

## Still open

- Lighthouse re-check after the screenshots (quota).
- Owner decision: which orgs get `pro` (use `/admin`).
- Severity calibration harvest (blocked on the key).
- Splunk first live pull, Sentinel Phase B, Partner Center, case study,
  monthly blog cadence, kit pricing table, scopesense.in NS hold.

## Agent utilization

- Opus: merge/deploy decisions, diff review of the compare pages and the teammate's step-4 tree, design system extraction and canvas authoring, smoke, docs.
- Sonnet: competitor comparison pages in an isolated worktree (reworked: N).
- Haiku: n/a — smoke run inline (10 URLs).
- codex:rescue: n/a — no security-adjacent change this session; the tier-toggle PATCH was reviewed in the wrap-up session.
