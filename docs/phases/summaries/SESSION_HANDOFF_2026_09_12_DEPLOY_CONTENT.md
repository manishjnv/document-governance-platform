# Session handoff — 2026-09-12: housekeeping commits, posts published, push + deploy

**Headline:** everything from the 2026-09-12 planning, homepage-branding and
content sessions is now on `origin/master` and live at
https://scopewise.assessiq.in. **Deployed SHA `4ddfd9f`.** The four pillar
blog posts are published (`pendingReview` cleared on the user's read-through)
and indexed via the sitemap (47 URLs). No migration (latest is still 039), no
apps/api runtime change beyond LICENSE and one web page. Live smoke: 20/20
checks pass, Lighthouse SEO / Accessibility 100 / 100 on `/` and
`/product/mitre-coverage` against the live URL.

## Commits pushed this session (`4d9c7ed..4ddfd9f`, plus this docs commit)

| Commit | What |
|---|---|
| `b48b510` | Blog model: `pillar`, product-page related links, keyboard filter chips, byline |
| `56b2e70` | Four pillar posts (MITRE coverage, Navigator layer, code review deliverable, SOW vs RFP) |
| `d09ce33` | `/compare/scopewise-vs-manual-review`, Resources dropdown, footer + sitemap links |
| `59e8f00` | `LICENSE` (Foxfiber Retail LLP, Apache-2.0 vendor carve-out); Visa non-affiliation line on `/codereview` |
| `23f5af3` | Blog inline links underlined (axe) |
| `313d44b` | Content-phase docs, roadmap + calendar ticks |
| `d0e27ae` | Sentinel Content Hub Phase A workbook v0 (regenerated, byte-identical) |
| `b2a6a1e` | v2 ACME MITRE sample pair (generator gates pass, content-identical) |
| `ad8e19a` | Content-phase kickoff prompt + pending-work runbook |
| `4ddfd9f` | Publish the four posts (`pendingReview` cleared) — **deployed SHA** |
| (this) | Docs: progress entry + this handoff (docs only, not redeployed) |

The privacy page (`2608b7d`) and plan docs (`4d9c7ed`) from the runbook's
Session 1 had already landed and were deployed earlier in the day.

## Deploy record

- `git push` accepted first time (commits authored as Claude Code; no email-privacy amend needed).
- VPS: `git pull` → `docker compose -f docker-compose.vps.yml --env-file .env build` → `GIT_SHA=4ddfd9f … up -d`. Only `scopewise-web`, `scopewise-api`, `scopewise-worker` recreated; redis/postgres untouched.
- Python 3.11 smoke (memory `prod-python-311-fstring-gotcha`): `python --version` = 3.11.15; `compileall.compile_dir('/app/app', force=True)` ok; `/health` → `{"status":"healthy"}`. (`python -c "import app.main"` from `/` fails with ModuleNotFoundError because the container cwd is not on `sys.path`; the healthy endpoint is the import proof. Next time run it as `docker exec -w /app scopewise-api python -c "import app.main"`.)
- Pre-flight: `tsc --noEmit` clean, `next build` 64 pages, `EDGP` grep 0 hits, every numeric claim in the marketing tree traced to plan §5, a product fact (slide counts, 30-second agent cap) or the blog's labelled hypothetical example.

## Live smoke (Haiku, 2026-09-12)

| Check | Result |
|---|---|
| HTTP 200 + expected `<title>` on `/`, `/product/sow-review`, `/product/mitre-coverage`, `/product/code-security-review`, `/pricing`, `/privacy`, `/terms`, `/compare/scopewise-vs-manual-review`, `/resources/blog` | ✅ all nine |
| `/product` → `/product/sow-review` | ✅ 308 |
| robots.txt disallows `/mitre` `/codereview` `/admin` `/login` `/api`; no `/pricing` | ✅ |
| sitemap.xml: 47 URLs, all 13 new pages/posts present, bare `/product` absent | ✅ |
| `og-default.png` 200 image/png; `og:image` + `twitter:card=summary_large_image` on `/` | ✅ |
| Four new posts: 200, no `noindex` | ✅ |
| Lighthouse 12.8.2 live: `/` SEO 100 / A11y 100; `/product/mitre-coverage` 100 / 100 | ✅ |

## Google Search Console and GA4 — steps for the owner (no dashboard access here)

Property: the existing **`assessiq.in` Domain property** (DNS-verified, covers the subdomain).

1. Sitemaps: Indexing → Sitemaps → the existing entry `https://scopewise.assessiq.in/sitemap.xml` → open it and use **Resubmit** (or remove and re-add the same URL). Expect "Success" with 47 discovered URLs after the next fetch.
2. Request indexing, one URL at a time (URL Inspection bar at the top): `https://scopewise.assessiq.in/product/sow-review`, `…/product/mitre-coverage`, `…/product/code-security-review` → **Test live URL** → confirm "URL is available to Google" and that the canonical shown matches → **Request indexing**. Quota is roughly 10 requests/day; do the three product pages first, then `/compare/scopewise-vs-manual-review`, `/pricing`, and the four blog posts on following days.
3. Also inspect `https://scopewise.assessiq.in/product` once: it should report the 308 redirect target, confirming the old URL consolidates.
4. Watch Indexing → Pages for "Excluded by noindex" on `/mitre`, `/codereview`, `/login` (expected, they are disallowed) and for the three product pages moving to Indexed within ~1–2 weeks.

GA4 (property `G-BS21BGYW3B`): no new event names were added this session. The existing `cta_click` event (fired by `CtaClickTracker` on every `/login` link, parameters `cta_text`, `page_path`) covers the "Start a review" buttons on every new page. The homepage product cards carry `data-product="sow|mitre|codereview"` but nothing reads it yet. To attribute card clicks per pillar, either (a) in GA4 Admin → Events → **Create event** is not enough because the click never fires an event; so (b) add one line to `CtaClickTracker` to also match `a[data-product]` and send `product_card_click` with `product: anchor.dataset.product` — a 5-line change, then mark `product_card_click` as a conversion in Admin → Events. Not done because the kickoff prompt only asked for the steps.

## Open / next

1. `/about` rewrite. Blog author decided 2026-09-12: "ScopeWise Team" with the Organization schema author; no Person schema planned.
2. `product_card_click` GA4 event (see above) when wanted.
3. Product screenshots (NodeGoat + ACME only), per-pillar OG images.
4. `/compare/[competitor]` stays blocked on legal sign-off; next blog batch per `CONTENT_CALENDAR.md`.
5. Sentinel workbook Phase A still untested against a live workspace.

## Agent utilization

- Opus: housekeeping commits, regeneration checks, publish flip, push, VPS deploy, Python 3.11 smoke, docs
- Sonnet: n/a — no page builds this stretch
- Haiku: live smoke test incl. two Lighthouse runs · reworked: N (one false-positive ⚠️ on `&amp;` in a title, dismissed)
- codex:rescue: n/a — no security/auth/classifier change
