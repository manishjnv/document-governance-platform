# UI redesign build plan — calm-light app (from the 2026-09-12 design canvas)

## §0 Status & changelog

| Date | Status |
|---|---|
| 2026-09-13 | Plan written after the owner's review of the canvas (no change requests). Nothing built yet. |
| 2026-09-13 | **Phase 0 built and pushed** (`daae552` tokens + fonts + scope, `eb7b44a` shell + `useResize` + primitives, `a0f8d79` login). Not deployed yet: the VPS deploy needs the owner to run the standard loop (auto-mode permission gate). Judgement calls: active nav is the soft tint per §2.4 (the canvas CSS `.nav a.on` is solid; plan wins); the collapse toggle is a ghost row inside the rail above `Log out`; the accessibility test gate is not runnable (no jest runner in the repo, see the file header), so the gates are `tsc` + `check_app_labels.py` + Playwright screenshots; harness PNGs were skipped (the DC runtime is not on disk), builders worked from the design modules' CSS instead; Tier 2 (`or.mjs dsf`) returned 403 (key limit), so Opus wrote the two scripts directly. Badge `tone` shipped without the hover tint the stock variants carry (RCA #28). |
| 2026-09-13 | **Phases 1-4 built and pushed, Phase 5 partly done.** 23 commits `daae552`..`6de58dd` (one per screen). Shared primitives `components/app/` (Chip, KpiTile, PageHeader, EmptyState, Skeleton, AlertBanner, ConfirmDialog, SeverityBar, useResize) + `.tbl`/`.tbl.cards` rules in `globals.css`; shadcn `table.tsx` now carries structure only (RCA #29). Every `window.confirm` (dashboard delete, connection delete, tool attestation) is a `ConfirmDialog`; the three resize implementations are one hook (sidebar, results split with an `origin()` offset, mitre sheets, finding drawer). Gates: `tsc` clean; label check per screen: every miss is a design sample-data string already absent before the restyle (Dashboard 1 dynamic, Results 4 data-driven area names, MitreList 8, MitreNew 24, MitreConnections 1, MitreDetail 38, CodeReviewList 1, CodeReviewNew 5, CodeReviewDetail 24, Admin 1 = the People no-match state, which needs a filter variable and was not built); Playwright at 1440/390 on every route: no page overflow (import page fixed, RCA #30), theme absent on `/`. **Not done:** VPS deploy (permission gate in auto mode; owner runs the standard loop), the Haiku live smoke and Lighthouse (need the deploy), screenshots with real data (no API locally; detail pages verified through their error/empty states only). Design deviations reported by builders: MitreNew keeps one card with dividers instead of three; Admin has no org email or runs-granted field to show. |
| 2026-09-13 | **Deployed** (VPS build of `06bd700`, both hosts). Live smoke (Haiku): 15/15 routes 200 on scopewise.assessiq.in (its scopesense.in 200s were a false positive — that host is not cut over yet, RCA #31), `app-theme` on app pages and login only (absent on `/`, Inter there), IBM Plex served from `/_next/static/media` with zero Google font requests, API healthy. Owner ran Lighthouse (Chrome DevTools, mobile, slow 4G) on `/dashboard`: performance 68, accessibility 100, best practices 100, SEO 63 (app page, crawlers blocked by design). Accessibility gate holds; the performance cost is the dashboard JS bundle (2.3 s execution, 610 ms blocking), not fonts or CSS; run timed out on API polling so numbers are pessimistic. Still open: real-data screenshot pass on the three detail pages, Admin People no-match state. Tooling added the same day: `apps/web/tests/ui_sweep.py` (page-overflow gate + screenshots), `docs/design/references/README.md`, the user-level `ui-design-workflow` skill (project-agnostic; ScopeWise values in CLAUDE.md), a Desktop copy for Claude Design web. |

Design source of truth: https://claude.ai/code/artifact/9f120be7-d49e-4651-8ea3-a103269b5e24 (v4) and
its generator in `docs/design/complete-app-2026-09-12/` (`dc.py` = tokens + primitives, `screens/*.py` =
per-screen structure, labels, states and interactions, `labels/*.json` = every string the screen must
keep). Kickoff prompt: `docs/phases/prompts/UI_REDESIGN_PHASE_0_PROMPT.md`.

## 1. Goal and rules

Restyle every authenticated screen of `apps/web` to the canvas, page by page, with **no behaviour
change**: same routes, same API calls, same state logic, same labels, same aria. The marketing site
(`/`, `/product/*`, `/blog`, `/compare`, ...) is untouched and keeps Inter.

Non-negotiables:
- Restyle in place. `dashboard`, `results`, `mitre/[id]`, `mitre/new` are 900-1150 lines of data
  logic; markup and classes change, hooks and handlers do not. Extract a component only when the
  design introduces a primitive shared by two or more screens (list in §3).
- Every string in `docs/design/complete-app-2026-09-12/labels/<Stem>.json` must still be in the
  page (that list was generated from the code, so nothing is lost either way). A grep-based check
  runs per phase (§6).
- `npx tsc --noEmit` clean and `tests/accessibility.test.tsx` green before every commit.
- One commit per screen; deploy at the end of each phase (standard VPS loop in `CLAUDE.md`).
- No new dependencies. Tailwind 3.4, shadcn primitives already installed, lucide icons, CSS only
  for motion (one ease, 160-450 ms). No dark mode (unwired today; the design is light only).

## 2. Phase 0 — theme, fonts, shell (one deploy; the whole app changes look at once)

1. **Fonts.** `app/layout.tsx`: add `IBM_Plex_Sans` (400/500/600) and `IBM_Plex_Mono` (400/500) from
   `next/font/google` as `--font-plex` / `--font-plex-mono`, alongside Inter. Tailwind
   `fontFamily.app` = `var(--font-plex)`, `fontFamily.mono` = `var(--font-plex-mono)`.
2. **Tokens.** New `app/app-theme.css` generated from the `TOKENS` dict in `dc.py` by
   `scripts/generate_app_theme.py` (hex to HSL for the shadcn variables, plus the new semantic ones),
   scoped under `.app-theme`:
   - shadcn overrides: `--background` paper `#FAF9F6`, `--card` `#FFFFFF`, `--foreground` ink
     `#14181F`, `--muted-foreground` ink2 `#3B4453`, `--border` `#E6E3DD`, `--input` `#D5D1C9`,
     `--primary` and `--ring` `#2457B8`, `--accent` `#E8EFFB`, `--destructive` `#A32D25`,
     `--radius` `0.5rem` (controls 8 px; cards use `rounded-[10px]`).
   - new: `--ink-3 #5E6877`, severity pairs (`--sev-crit #A32D25 / #FBE7E4`, `--sev-high
     #9C4A0C / #FCEEDF`, `--sev-med #705708 / #FAF1D2`, `--sev-low #2E6A42 / #E3F1E7`, `--sev-info
     #1F5C85 / #E3EEF7`), `--ok #2A6F46`, `--violet #4F3691`, `--ease cubic-bezier(.22,.61,.36,1)`.
   - Tailwind `colors.ink3`, `colors.sev.{crit,high,med,low,info}` plus `.soft` variants,
     `colors.ok`, `colors.violet`; `transitionTimingFunction.app`.
   The generator is the single source: editing a colour in `dc.py` and re-running the script updates
   both the canvas and the app.
3. **Scope.** The `AppShell` root and the login page root get `className="app-theme font-app"`.
   Because `body` paints `bg-background`, the shell root keeps its own `bg-background` so the paper
   colour applies only inside the app. Marketing keeps the old variables (they stay on `:root`).
4. **AppShell** (`components/AppShell.tsx`): sidebar per the `Main` and `Dashboard` artboards. Active
   item is an accent-soft tint with accent text (not solid primary), 8 px radius, collapse toggle
   inside the rail, and the grip uses the `useSheetResize` contract (pointer capture, ArrowLeft and
   ArrowRight move 40 px, `role=separator`, persisted) so the three resize implementations become
   one hook (`components/app/useResize.ts`, moved from `app/mitre/components/useSheetResize.tsx` and
   re-exported there). Mobile top bar and sheet nav restyled. `Log out` stays.
5. **Login** (`app/login/page.tsx`): card layout per the `Login` artboard; every step and message kept.
6. **shadcn primitives** touched once: `button.tsx` (heights 36 / 30 / 44 for `default` / `sm` /
   `lg`, keep `icon`), `badge.tsx` (add `tone` variants crit, high, med, low, info, ok, neutral,
   violet, demo, pro), `card.tsx` (10 px radius, hairline border, no shadow), `sheet.tsx` (grip
   slot), `tooltip.tsx` (ink background, 12 px, 280 px max width, 160 ms). Everything else inherits
   through the variables.

Exit: the whole app is in the new type, colour and spacing after one deploy; per-page structure is
still old. This is acceptable to ship because every page already consumes the tokens.

## 3. Shared primitives (built in the phase that first needs them, under `components/app/`)

| Primitive | Replaces today | First used |
|---|---|---|
| `Chip` (tone, dot, tooltip) | ad-hoc badge classes in 9 files, four copies of the Demo badge | Phase 1 |
| `KpiTile` (label, value, sub, tone, tooltip, onClick) | dashboard stats strip, MITRE ExecutiveBand tiles, CodeReview ReviewBand, Admin KPIs | Phase 1 |
| `PageHeader` (title, meta line, actions, back link) | per-page header markup | Phase 1 |
| `DataTable` styling (`.tbl`: 11 px uppercase headers, 13 px cells, tabular numerals, `td[data-th]` becomes card rows under 760 px) | per-page density overrides; the findings table's card rows become the pattern for all | Phase 1 |
| `EmptyState`, `Skeleton` | five different empty blocks; no skeletons on MITRE list, detail, connections | Phase 1 |
| `ConfirmDialog` (destructive) | `window.confirm` in dashboard delete, connection delete, tool attestation | Phase 1 |
| `AlertBanner` (error, dismissible warning, ok, info suggestion) | five inline patterns | Phase 1 |
| `useResize` | sidebar mouse-only, results split mouse-only, `useSheetResize` | Phase 0 |
| `SeverityBar` (stacked proportions) | code review list and detail bars, versions diff | Phase 3 |

Rule: a primitive is added only when the second consumer arrives; the first consumer may inline.

## 4. Phases 1-4 — screens (each row is one builder and one commit)

| Phase | Screen (route) | Design module | Notes |
|---|---|---|---|
| 1 SOW | Dashboard `/dashboard` | `screens/dashboard.py` | project bands, version expanders, inline type and project editors, search mode, suggestion banner, request-access dialog, delete via `ConfirmDialog`, phone card rows |
| 1 | Upload `/upload` | `upload.py` | dropzone states, project chip, seven error messages |
| 1 | Project detail `/projects/[id]` | `project_detail.py` | adds an empty state |
| 1 | Versions diff `/versions/diff` | `versions_diff.py` | three columns stack on phone |
| 1 | Results `/results/[reviewId]` | `results.py` | split pane with `useResize`, sticky document pane, severity tiles as filters, section-jump highlight. Largest risk; last in the phase |
| 2 MITRE | List `/mitre` | `mitre_list.py` | skeleton, rename, archive, sparkline |
| 2 | New `/mitre/new` | `mitre_new.py` | source tabs, dropzones, parse-preview tiles, column wizard, gated form |
| 2 | Connections `/mitre/connections` | `mitre_connections.py` | delete via `ConfirmDialog`, card rows |
| 2 | Detail `/mitre/[assessmentId]` | `mitre_detail.py` | the 11 existing components restyled one by one (ExecutiveBand, UploadSummaryCard, CoverageHeatmap, GapsRoadmap, AssumptionsNA, CompareView, DrillDownPanel, RuleListPanel, TechniqueDrawer, StateBadge, CoverageSparkline); matrix inside an `overflow-x:auto` scroller; attestation confirm via `ConfirmDialog`. Read `MITRE_MODULE_REFERENCE.md` first. Two builders: page + band + summary + tabs, and heatmap + sheets |
| 3 Code | List `/codereview` | `codereview_list.py` | cards, kebab, rename and delete dialogs |
| 3 | New `/codereview/new` | `codereview_new.py` | two cards, copy button, file row |
| 3 | Detail `/codereview/[reviewId]` + `FindingDrawer` | `codereview_detail.py` | ReviewBand becomes `KpiTile`, SeverityStrip becomes `Chip`, FindingsTable header and cells, ChainsTab keeps its graph, drawer 576 px with grip. Read `CODE_REVIEW_MODULE_REFERENCE.md` first |
| 4 Admin | Admin `/admin` | `admin.py` | KPIs, org table with tier select and runs input, people search, feeds, AI usage; phone card rows; People empty and no-match states |
| 4 | Cross-cutting | `Main` artboard | `install-prompt.tsx`, the `service-worker-register.tsx` bar, `RequestAccessForm` restyle, skip-link colour |

Deploy after each phase. Phase 5 is verification (§6) and the final deploy.

## 5. Builder contract (every builder prompt carries this)

- Files: the page and component paths above, `components/app/*` it may use, nothing else.
- Spec: the design module's `BODY`, `VALS` and `CLICKS`, and the artboard PNG from the harness
  (`python harness.py --screens <Stem> --out <dir>` and `--phone`); the token names in §2.
- Keep: every handler, fetch, state variable, `aria-*`, `data-testid`, and every string in
  `labels/<Stem>.json`. Replace `window.confirm` only where §3 says so.
- Deliver: unified diff, a change log under 200 words, and the output of `npx tsc --noEmit` and the
  label check (§6). Screens over about 600 lines: write in two Edit passes, never one Write.
- Opus reviews the diff only (Phase 3 of the playbook); a second round at most; abort and rethink
  if the same class of defect returns.

## 6. Verification per phase

1. `cd apps/web && npx tsc --noEmit` and the accessibility test (`tests/accessibility.test.tsx`)
   clean.
2. Label check: `python docs/design/complete-app-2026-09-12/check_app_labels.py <Stem> <tsx paths>`
   (new, about 40 lines: same normalisation as `check_labels.py`, greps the TSX sources for every
   string in `labels/<Stem>.json`; exits 1 on a miss).
3. Visual: dev-server screenshot at 1440 and 390 next to the artboard PNG, reviewed by Opus.
   Mismatches that are not in the labels list are judgement calls; log them in §0.
4. Deploy, then a Haiku live smoke: every authenticated route returns 200 with the shell, the
   `app-theme` class is present on app pages and absent on `/`, fonts load from
   `/_next/static/media` (no Google request at runtime), Lighthouse mobile on `/login` and
   `/dashboard` not below today's (accessibility stays 100).
5. RCA entry for any bug fixed on the way (`docs/RCA_LOG.md`), progress index, handoff footer.

## 7. Effort and routing (cheapest tier that fits, per the global playbook)

| Phase | Builders | Opus | Wall time |
|---|---|---|---|
| 0 | Tier 2 (`or.mjs dsf`) for `generate_app_theme.py` and `check_app_labels.py` (dev tooling, not load-bearing); 1 Sonnet for shell + login + primitives | diff review, token script check | half a day |
| 1 | 5 Sonnet in two waves (4, then Results alone) | review x5, primitives | 1 day |
| 2 | 5 Sonnet (Detail split in two) | review x5 | 1 day |
| 3 | 3 Sonnet | review x3 | half a day |
| 4 + 5 | 2 Sonnet, 1 Haiku smoke | review, Lighthouse, docs | half a day |

Page restyles stay on Sonnet: they edit load-bearing UI files with data logic, which the playbook
keeps off the OpenRouter tiers. At most 4 concurrent builders (account session limit); none touch
`apps/api`; no codex:rescue needed (no auth or security logic changes) unless a builder touches
token handling in `AppShell`, in which case a Sonnet adversarial pass on that diff.

## 8. Risks

- **Token scoping leaks into marketing**: `.app-theme` must wrap only app roots; the smoke checks
  that `/` has no `app-theme` class and still renders Inter.
- **Font cost**: two extra families add about 120 KB; subset to latin, weights 400/500/600 only;
  preload handled by `next/font`. Check Lighthouse (§6.4).
- **Mixed look between phases**: Phase 0 makes it acceptable; the order SOW, MITRE, Code, Admin
  follows traffic.
- **Large-page regressions**: no logic edits; diffs reviewed line by line; the label check and the
  accessibility test are the guard rails; a screen that cannot be restyled without touching logic is
  reported, not forced.
- **Tooltips**: use the shadcn `Tooltip` (portal), never CSS pseudo-element tooltips (RCA #27).
