# Kickoff prompt — MITRE Assessment Phase 3 (frontend)

Self-contained kickoff prompt. Paste everything below the line into a
fresh session (target model: Fable 5 main session).

---

Implement **Phase 3** of the MITRE ATT&CK coverage-assessment feature for
ScopeWise: the frontend. `docs/planning/MITRE_ASSESSMENT_PLAN.md` (§2
intake spec, §9 frontend + UI principles, §13 Phase 3) is the
authoritative design — do not re-litigate decisions recorded there.

## Context

ScopeWise: AI SOW/RFP review platform (FastAPI `apps/api`, Next.js 14
app-router `apps/web`, live at scopewise.assessiq.in). The MITRE module
backend is COMPLETE through Phase 2 — verified, committed, and deployed
to production 2026-08-01: full pipeline (upload → parse preview → run →
AI tagging with degrade discipline → applicability → coverage → gap
ranking → narrative → results) behind `/api/v1/mitre/*`, JWT-authed,
org-scoped. Suite baseline: **636 passed, 6 skipped** (per root
CLAUDE.md). There is currently NO UI for any of it — that is this phase.

**Roadmap:** P0 ✅ P1 ✅ P2 ✅ → **P3 (THIS): /mitre pages + nav +
templates** → P4 reports (PDF/XLSX) + trend compare UI → P5 hardening +
final deploy. NOT in this phase: report download buttons, compare/trend
UI (both Phase 4), any backend change.

**Isolation contract for Phase 3:** new files under
`apps/web/app/mitre/` and `apps/web/public/templates/`, plus EXACTLY ONE
shared-file edit: one entry in the `NAV_ITEMS` array of
`apps/web/components/AppShell.tsx` (label "MITRE Assessment", a sparse
lucide icon, e.g. `Target` or `Crosshair`). **Zero backend changes** —
if an API gap blocks you, stop and report it rather than patching
`apps/api`. No new npm dependencies.

## Read first (one parallel burst), then state your plan in a few lines

1. `docs/planning/MITRE_ASSESSMENT_PLAN.md` §2 (intake fields, scope-
   exclusions semantics, on-screen privacy notice copy) and §9 (pages +
   the locked UI principles).
2. `docs/phases/summaries/SESSION_HANDOFF_2026_08_01_MITRE_PHASE_0_1.md`
   — its Phase 2 section documents the exact summary-JSONB shape you
   will render (gaps, roadmap, narrative with `generated_by` flag,
   technique_results, assumptions, N/A list) plus a UI-copy note about
   Sysmon network telemetry.
3. `apps/api/app/mitre/router.py` — the actual endpoint request/response
   shapes (source of truth; don't guess).
4. House patterns to replicate verbatim: `apps/web/app/upload/page.tsx`
   (drag-drop, client validation, FormData POST, auth guard),
   `apps/web/app/results/[reviewId]/page.tsx` (typed interfaces, tiles,
   filterable rows), `apps/web/app/admin/page.tsx` (visibility-aware
   60s polling — the only polling precedent; StatTile to copy locally),
   `apps/web/components/AppShell.tsx` (NAV_ITEMS), `lib/utils.ts` cn().

## UI principles (locked with the user — apply to every screen)

Full-screen flexible layout (results stretch to the viewport, no
max-width straitjacket); minimal borders — separate panels with spacing
and subtle background shifts, consistent gutter between content and
container edges; compact, professional, data-dense (no oversized hero
cards, no AI-generated look); **modular components** — each panel is its
own file under `apps/web/app/mitre/components/`, data via props only;
**tooltips everywhere data needs context** (shadcn Tooltip, smooth
~150ms fade/scale) — every %, state badge, confidence value, and N/A
reason gets a plain-English hover explanation; all copy in simple,
human-readable English (e.g. "techniques we can't see yet because no
log source covers them").

## Deliverables

1. **`/mitre` (list page)** — org's assessments: name, status badge,
   created date, headline coverage %, per-domain mini-bars,
   attack_version; "New assessment" CTA; empty-state that explains the
   feature in two sentences. (Trend arrows come in Phase 4 with the
   compare endpoint — skip.)
2. **`/mitre/new` (wizard, single page)** — in order: the §2 privacy
   notice shown BEFORE any file is chosen; use-case dump drop
   (xlsx/xls/csv/pdf/docx) + environment workbook drop (xlsx), client
   validation mirroring server rules (50MB, extensions), template
   download links; slim intake form: industry + region dropdowns,
   "count disabled rules as coverage?" toggle default No,
   scope-exclusions editor (rows of what + reason, both required per
   row); submit → POST create → render the parse preview inline
   (row count, detected columns/sheets, tagged/untagged/invalid split,
   warnings — this is the user's chance to catch a bad column map) →
   "Run assessment" → POST run → redirect to results.
3. **`/mitre/[assessmentId]` (results)** —
   - While `running`: progress state + the admin-page polling pattern
     (shorter interval, ~5s, visibility-aware); `failed` shows
     error_message plainly with a re-run hint.
   - Executive band: overall strict % (weighted % in its tooltip),
     per-domain tiles, covered/partial/not-covered/N-A counts, top-5
     gaps, attack_version + run date.
   - Coverage tab: per-domain tactic-column heatmap (CSS grid — NO new
     charting dependency), cells colored by state; click → technique
     drawer (state, tactic(s), mapped use cases with confidence +
     source customer/ai, N/A reason if any).
   - Gaps & Roadmap tab: ranked gap table (technique, tactic, priority
     tier, feasibility, plain-English recommendation from the
     narrative) + short/mid/long roadmap sections with
     `narrative.generated_by` surfaced ("AI-written" vs "template"
     badge).
   - Assumptions & N/A tab: assumptions list; N/A table grouped
     derived-domain / derived-platform / customer-declared (verbatim
     reasons).
   - NO PDF/XLSX/compare buttons (Phase 4).
4. **Templates** in `apps/web/public/templates/`:
   `scopewise-mitre-use-cases.xlsx` (columns: Use Case Name, MITRE
   Technique IDs, Detection Logic, Description, Log Source, Status; one
   example row) and `scopewise-mitre-environment.xlsx` (sheets: Assets,
   Log Sources, Security Tooling, Crown Jewels; a few example rows
   each). Generate once with a throwaway openpyxl script (scratchpad),
   check in the xlsx files only. Header names must be ones
   `apps/api/app/mitre/ingest.py`'s synonym lists detect — verify
   against that file.
5. **Nav entry** — the one AppShell.tsx line.

House rules: every page `'use client'`, AppShell-wrapped, inline axios
with `Authorization: Bearer ${localStorage.getItem('access_token')}` and
redirect-to-/login guard replicated verbatim; NO shared API client, NO
token-refresh logic; API base `${process.env.NEXT_PUBLIC_API_URL}`.
Windows note: if `next dev`/`next build` hangs at "Starting...", it's
Defender scanning node_modules — see root CLAUDE.md, don't debug it as
code.

## Acceptance (run, don't assume)

- `cd apps/web && npx tsc --noEmit` — clean.
- `git status`: only `apps/web/app/mitre/*`, `apps/web/public/templates/*`,
  the single AppShell.tsx edit, and session docs. Zero `apps/api` changes.
- Backend suite untouched → still 636/6 if run.
- Manual browser click-through against the local dev stack: seed an
  assessment with a **customer-tagged** template xlsx (avoids LLM —
  the OpenRouter key may still be over its daily cap) and walk
  new → preview → run → poll → all three results tabs → drawer →
  tooltips. Report what you actually clicked and saw, including
  mobile-width behavior (pages must not overflow horizontally).

## Wrap-up

Do NOT commit/push/deploy unless the user explicitly says so. Report:
files created, the AppShell diff verbatim, tsc output, click-through
narrative, deviations with reasons. Update
`docs/IMPLEMENTATION_PROGRESS.md`'s MITRE entry (Phase 3 done, Phase 4
next) and extend the session handoff.
