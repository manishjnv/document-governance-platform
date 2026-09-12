# Session handoff — 2026-09-12: Core Web Vitals re-check + /resources/templates lead magnet

**Headline:** the homepage rebuild did not regress the font or images; the
regression was Google Tag Manager loaded `afterInteractive`, which doubled
mobile LCP on every marketing page. One-word fix (`lazyOnload`) restores the
July baseline. The last open Phase 3 technical item, `/resources/templates`,
ships as a gated three-file download with no new tables, services or
dependencies. Two commits, local only, **not pushed, not deployed**.

## Part A — measurements

Method: Lighthouse 12.8.2 (`--only-categories=performance`, default mobile
throttling and `--preset=desktop`), five live pages, then the same build
locally with `NEXT_PUBLIC_GA_MEASUREMENT_ID` set so gtag is present, before
and after the fix. Lab numbers, not field data; INP is not reported by
Lighthouse lab runs (n/a throughout).

### Live before (2026-09-12, SHA `4ddfd9f`)

| Page | Form | Perf | FCP | LCP | TBT | CLS |
|---|---|---|---|---|---|---|
| `/` | mobile | 71 | 2.85s | 4.82s | 304ms | 0.003 |
| `/` | desktop | 96 | – | 1.23s | 104ms | 0.000 |
| `/product/sow-review` | mobile | 59 | 3.17s | 5.60s | 528ms | 0.029 |
| `/product/sow-review` | desktop | 83 | – | 2.14s | 150ms | 0.000 |
| `/product/mitre-coverage` | mobile | 57 | 2.97s | 5.16s | 758ms | 0.000 |
| `/product/mitre-coverage` | desktop | 80 | – | 2.51s | 91ms | 0.000 |
| `/resources/blog` | mobile | 57 | 3.25s | 5.71s | 585ms | 0.000 |
| `/resources/blog` | desktop | 87 | – | 2.02s | 59ms | 0.000 |
| blog post (MITRE coverage) | mobile | 58 | 2.77s | 4.76s | 880ms | 0.000 |
| blog post (MITRE coverage) | desktop | 94 | – | 1.55s | 58ms | 0.000 |

Phase 1 baseline (2026-07-20, roadmap table): homepage Perf 79 / LCP 2.9s /
TBT 650ms; `/product` Perf 89 / LCP 2.5s; CLS 0. So mobile LCP had roughly
doubled.

### Diagnosis

- LCP element on every page is the lead paragraph (text). Its time is
  almost entirely **render delay** (4.4–5.1s); TTFB 450ms, no image, no
  load delay. `render-blocking-resources` and `font-display` audits pass;
  the Inter file is latin-subset, 49KB, preloaded by `next/font`.
- `third-party-summary`: Google Tag Manager blocked the main thread
  820–990ms; `bootup-time` 2.4–2.7s with gtag first; 175KB, ~145KB unused.
- Local build **without** gtag: `/` mobile Perf 91, LCP 2.92s — identical to
  the July baseline. Local build **with** gtag `afterInteractive`: Perf 59,
  LCP 4.33s. That isolates the cause.
- Fix order from the brief: hero image (none exists), font (already subset +
  preloaded, nothing to change), **defer GA4 → applied**, unused client
  components (`ServiceWorkerRegister`, `InstallPrompt`, `CtaClickTracker`
  in the root layout are small; left alone since the target was met).

### Local before / after (same build, gtag present, mobile)

| Page | Before: Perf / FCP / LCP / TBT | After (`lazyOnload`): Perf / FCP / LCP / TBT / CLS |
|---|---|---|
| `/` | 59 / 2.50s / 4.33s / 1116ms | **81** / 1.32s / **2.74s** / 595ms / 0.000 |
| `/product/sow-review` | 53 / 2.72s / 4.70s / 1407ms | **79** / 1.29s / **2.71s** / 687ms / 0.029 |
| `/product/mitre-coverage` | – | 82 / 1.29s / 2.72s / 573ms / 0.000 |
| `/resources/blog` | – | 78 / 1.44s / 3.02s / 476ms / 0.119* |
| blog post (MITRE coverage) | – | 78 / 1.31s / 2.58s / 774ms / 0.000 |
| `/resources/templates` (new) | – | 88 / 1.29s / 2.56s / 382ms / 0.018 |

\* the blog index shift is attributed by Lighthouse to "Web font loaded" on
the long post list (lab artifact of the swap on a text-heavy page; the same
page measured 0.000 live). Not a regression; `display: swap` +
`adjustFontFallback` already minimise it. Revisit only if CrUX shows it.

What changed: `apps/web/app/layout.tsx`, both GA `<Script>` tags
`afterInteractive` → `lazyOnload`. GA still fires the page view; it now
waits for `load` instead of competing with hydration. Re-measure live after
deploy; expected mobile Perf ~80 on every marketing page.

## Part B — /resources/templates

- `apps/web/app/resources/templates/page.tsx` (server) + `TemplatesGate.tsx`
  (client). Three cards: SOW review checklist (PDF), RFP evaluation criteria
  worksheet (XLSX), MITRE environment inventory template (XLSX, the existing
  `public/templates/mitre-environment-template.xlsx`). While locked, no
  download `href` exists in the DOM. Form: name + work email + hidden
  honeypot (`website`, uncontrolled, read from `FormData` at submit so a bot
  that sets `input.value` directly is still caught; silent unlock without a
  POST). Real submit POSTs `{name, email, message, source: 'templates'}` to
  the existing `/api/v1/contact`; success reveals the links and remembers
  the unlock in `localStorage` (try/catch). Existing global
  `RateLimitMiddleware` applies.
- `apps/api/app/routers/contact.py`: the Pydantic model silently dropped
  unknown fields, so `source` would never have reached the email. Added one
  optional field (`source: str | None`, max 50) and a `Source:` line in the
  email body. Existing callers unaffected (`contact` default). Only apps/api
  change.
- Files: `scripts/generate_templates.py` (reportlab + openpyxl, both already
  installed) writes `public/templates/sow-review-checklist.pdf` (the 10-point
  checklist from the blog post, guidance-not-legal-advice footer) and
  `rfp-evaluation-criteria-worksheet.xlsx` (Read Me, Requirements,
  Evaluation Factors with weights summing to 100 and formula-computed
  weighted scores, Submission & Award). Regenerate with the script.
- Privacy page: one sentence under "What we collect" about the form.
  Footer Resources column + sitemap entry (`2026-09-12`).
- Verified with Playwright: locked DOM has zero download links; honeypot set
  via `input.value` → no POST, links shown; real submit → one POST with
  `source: 'templates'`, three links, all three files 200 with correct
  content types; unlock persists across reload; Tab from Name goes to Work
  email, never the honeypot. Lighthouse desktop on the page: Accessibility
  100, SEO 100; mobile Perf 88.

## Commits (local only)

| Commit | What |
|---|---|
| (A) | `layout.tsx`: GA4 scripts `lazyOnload` |
| (B) | templates page + gate, generator + two files, privacy sentence, footer + sitemap, `contact.py` optional `source` |
| (docs) | roadmap ticks, progress entry, this handoff |

## Open / next

1. Push + deploy on the user's say-so, then re-run the live Lighthouse
   table (expect mobile Perf ~80) and update the roadmap baseline table.
2. Send one real submission from the live templates page and confirm the
   email arrives with `Source: templates`.
3. Optional: scope `ServiceWorkerRegister` / `InstallPrompt` to the app
   shell instead of the root layout if a later measurement wants the last
   ~10 points of mobile TBT.

## Agent utilization

- Opus: measurements, diagnosis, GA fix, generator script, API field, privacy/footer/sitemap wiring, Playwright verification, docs
- Sonnet: templates page + gate component · reworked: Y (honeypot was a controlled input, bypassable by setting `input.value`; `&amp;` inside JS strings)
- Haiku: n/a
- codex:rescue: n/a — public form posts to an existing rate-limited endpoint; no auth or classifier change
