# Session log — 2026-09-12 — one conversation, six work phases (marketing site, content, CWV, calibration prep, wrap-up, free model)

This is the consolidated record of a single long Claude Code conversation
that ran from the homepage-branding kickoff through the evening deploy. The
per-phase handoffs already in this folder hold the detail; this file is the
index, the decisions, the gotchas and the exact end state, so a future
session never has to reconstruct the day from git alone.

**End state:** `origin/master` = `7ededbc`; VPS runs **`8ae053b`**; working
tree clean. Live: https://scopewise.assessiq.in (scopesense.in staged, NS hold).

## Phases and their handoffs

| # | Phase | Kickoff | Handoff | Commits (first…last) | Deployed |
|---|---|---|---|---|---|
| 1 | Homepage branding + SEO (plan §7 steps 1-6) | `docs/phases/prompts/HOMEPAGE_BRANDING_SEO_PROMPT.md` | `SESSION_HANDOFF_2026_09_12_HOMEPAGE_BRANDING.md` | `2608b7d`…`4d9c7ed` | yes (same day) |
| 2 | Content phase (4 pillar posts, /compare page, LICENSE) | `docs/phases/prompts/CONTENT_PHASE_BLOG_COMPARE_PROMPT.md` | `SESSION_HANDOFF_2026_09_12_CONTENT_PHASE.md` | `b48b510`…`313d44b` | yes |
| 3 | Housekeeping commits, posts published, push + deploy | pending-work runbook session 1 | `SESSION_HANDOFF_2026_09_12_DEPLOY_CONTENT.md` | `d0e27ae`, `b2a6a1e`, `ad8e19a`, `4ddfd9f`, `fab4da8`, `644ab3b` | yes (`4ddfd9f`) |
| 4 | Core Web Vitals re-check + /resources/templates | inline prompt | `SESSION_HANDOFF_2026_09_12_CWV_TEMPLATES.md` | `6375816`, `44a5b38`, `69d128a` | yes (later) |
| 5 | Legal severity calibration pack (scripts only; harvest blocked) | inline prompt | `docs/planning/severity_calibration/README.md` | `fbbdf9e` | n/a |
| 6 | Wrap-up: admin tier toggle, deploy, landing polish, free model | `docs/phases/prompts/PENDING_WORK_RUNBOOK_2026_09_12.md` | `SESSION_HANDOFF_2026_09_12_WRAPUP.md` (+ two addenda) | `22c88a9`, `fdfaba3`, `db30589`, `29dbd8c`\*, `482e31b`, `d5c2a25`, `8ae053b`, `7ededbc` | yes (`8ae053b`) |

\* `29dbd8c`, `f19ae4b` (competitor compare pages) and `a080b99` were made by a
parallel session working in the same tree; this conversation's screenshot
files went into `29dbd8c`. Other parallel-session commits the same day:
`5ed1053`…`4ae0c0b` (code review hardening), `329d10b`/`a6a5bdb`/`6e3aef6`
(run-entitlement gate + pricing unlink), `e83f435`/`0648c2a` (scopesense.in),
`ee19ff9` (MITRE demo assessments), `29bd6ef` (design hero views).

## What changed, by area

**Marketing site (`apps/web`)** — platform-umbrella homepage with three
product cards and sourced stat tiles; `/product/sow-review` (308 from
`/product`), `/product/mitre-coverage`, `/product/code-security-review`;
`/solutions/for-security-consultancies`, `/solutions/for-appsec-consultants`;
`/compare/scopewise-vs-manual-review`; `/resources/templates` (gated
downloads); `/terms`; `/privacy` committed; header with Products and
Resources dropdowns (Radix, `aria-expanded`) and a mobile panel; four-column
footer; Inter via `next/font`; darker `--muted-foreground` (215 22% 32%,
8.4:1); OG images (default + per pillar, no host name); real product
screenshots (MITRE heatmap, code review drawer, SOW results) as 960px WebP
served `unoptimized`; GA4 deferred to `lazyOnload`; blog gains `pillar`,
filter chips, product-page related links, BlogPosting image/dateModified/
publisher; glossary `DefinedTermSet`; four MITRE/Code Review/SOW-vs-RFP
posts published; `/about` name rationale; `/pricing` kept but unlinked and
noindexed (owner decision, parallel session).

**API (`apps/api`)** — `contact.py` optional `source` field;
`dependencies.require_platform_admin()`; `GET /api/v1/admin/orgs` and
`PATCH /api/v1/admin/orgs/{org_id}/tier` (audited); `tests/test_admin_tier.py`.
No migrations (039 remains latest). Run-entitlement gate itself came from a
parallel session (`329d10b`).

**Deploy/config** — `docker-compose.vps.yml` now passes `OPENROUTER_MODEL`
and `OPENROUTER_FALLBACK_MODELS`; VPS `.env` sets
`nvidia/nemotron-3.5-lightning:free` + `nvidia/nemotron-3-ultra-550b-a55b:free`
(backup `.env.bak.<ts>` on the VPS). Top-level `LICENSE` (Foxfiber Retail
LLP, Apache-2.0 vendor carve-out). `scripts/generate_og_image.py`,
`scripts/generate_templates.py`, `scripts/severity_calibration_run.py`,
`scripts/severity_calibration_ingest.py`, `scripts/generate_sentinel_workbook.py`
(Phase A workbook committed, untested live), `scripts/generate_uploadsample.py`
v2 pair.

## Decisions taken by the owner in this conversation

| Decision | Effect |
|---|---|
| Blog author is "ScopeWise Team"; schema author stays Organization | no Person schema; `/about` Person schema dropped from the plan |
| LICENSE copyright holder: Foxfiber Retail LLP | `LICENSE` at repo root |
| Prod organisation tiers: none set to pro for now | all nine orgs `free`; owner enables from `/admin` per request |
| Key limit is the owner's to raise before the next review run | not treated as an outage; memory corrected |
| Run prod on the free OpenRouter model meanwhile | `8ae053b`; accuracy unmeasured |
| Push/deploy authorised for the wrap-up and the free-model change | done as listed |

## Verification record (all in the per-phase handoffs; headline numbers)

- Lighthouse 12.8.2 (Lighthouse 13 breaks on Node 20): SEO/A11y/Best-practices
  100/100/100 on `/`, three product pages, `/about` after phase 1; A11y 100 on
  blog index, compare page, templates page; after screenshots, mobile perf `/`
  79 (July baseline 79) and `/product/mitre-coverage` 78, desktop 100.
- CWV root cause: gtag `afterInteractive` doubled mobile LCP (4.8–5.7s live);
  `lazyOnload` restored 2.7s. Font and OG image were not the cause.
- Live smokes: 20/20 (`4ddfd9f`), 18/18 (`22c88a9`), 10/10 (`29dbd8c`);
  `8ae053b` spot-checked (both containers on the free model, SOW WebP 200).
- Statistics on the site: only plan §5 numbers, each with its source; two
  wordings corrected to match sources (WorldCC "annual revenue"; Bright
  Defense $7,000–$35,000). Source URL table in the homepage-branding handoff.
- Backend suite not run solo this conversation (edgp_test single-runner rule;
  another session ran it: 985/7 per the hardening handoff).

## Gotchas learned (worth knowing before repeating any of this)

1. A `next start` left running from a previous build serves stale chunk names
   → every static chunk 400s, nothing hydrates. Kill the listener first.
2. Bash heredocs here eat backslashes in embedded Python (`\'`, `\\`) — use
   the Edit/Write tools for anything with escapes.
3. `next/image` optimizer in the standalone image has no `sharp` → returns
   originals for every `w=`; pre-size and use `unoptimized`.
4. Local capture: Chromium resolves `localhost` → `::1`, uvicorn binds IPv4
   (`--host-resolver-rules=MAP localhost 127.0.0.1`); CORS default is
   `http://localhost:3000` only; set the token via `add_init_script`, not on
   `/login` (its redirect races); the docs upload endpoint needs `org_id`,
   `project_name` and an explicit DOCX content type.
5. Docker Desktop's engine died twice mid-session; capture right after
   `docker start`.
6. OpenRouter per-key limit blocks paid models only; `:free` models still
   answer (most old `:free` slugs are retired — list via `/api/v1/models`).
7. The API entry module is `apps/api/main.py`, not `app.main`; the prod
   container has no wget (use `python -c` + urllib); the worker container
   lacks `JWT_SECRET_KEY` in compose (warning only; it mints no tokens).
8. Never trust the local shell's `OPENROUTER_API_KEY` — it is the personal
   $2 tooling key; there is no `apps/api/.env` locally, so `settings` picks
   the shell key. Inject the VPS key per-process.

## Open items (owner unless stated)

1. Raise the OpenRouter key limit (or keep the free model after judging one
   fresh prod review). Then: severity-calibration harvest (Claude, two
   commands in `docs/planning/severity_calibration/README.md`), and consider
   restoring the measured paid chain.
2. Send the calibration pack to a contracts lawyer once generated.
3. GSC: resubmit the sitemap; request indexing for the three product pages,
   then compare index, templates, four posts (~10/day).
4. Sentinel workbook first live test (needs the owner's workspace; iteration
   loop ready — blind spots listed in `marketplace/sentinel/README.md`).
5. Enable orgs to `pro` from `/admin` as requests arrive (two arrived by email
   on 2026-09-12 per the parallel session).
6. Add `JWT_SECRET_KEY` to the worker service in `docker-compose.vps.yml`.
7. scopesense.in NS switch at the registrar when the hold lifts, then the
   cut-over script.
8. `product_card_click` GA4 event (5-line change) if per-pillar attribution
   is wanted; Lighthouse against live once the PageSpeed quota resets.

## Agent utilization (whole conversation)

- Opus: plan/doc reads, all diff reviews, steps 1-2 of phase 1 hands-on, deploys (`4ddfd9f`, `22c88a9`, `8ae053b`), verification scripts, screenshot pipeline, docs
- Sonnet: 7 page builds (phase 1) · 4 posts + compare page + templates gate (phases 2/4) · admin backend + frontend (phase 6) · 2 adversarial takeovers (entitlement-era tier toggle: accept) · reworked: 3 of 16 (US spelling, honeypot made uncontrolled, `&amp;` in JS strings)
- Haiku: statistic source-URL check · three live smoke tables · reworked: N
- codex:rescue: n/a — companion MCP broken all day; Sonnet takeover used for the one security-adjacent change
