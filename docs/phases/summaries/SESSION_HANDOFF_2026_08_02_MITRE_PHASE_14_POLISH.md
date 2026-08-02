# Session handoff — MITRE Phase 14 polish pass (2026-08-02, evening)

**Headline:** five user-feedback refinements after walking the deployed
Phase-14 UI, all shipped and DEPLOYED (prod at `4f93523`). Frontend-heavy
+ one XLSX rework; **no backend logic or number changes**, no migrations.
Suite stays **800 passed / 7 skipped**; `tsc --noEmit` clean.

## What the user asked for → what shipped

### 1. "Make the side popout flexible to move around / take more space by mouse"

`apps/web/app/mitre/components/useSheetResize.tsx` (new) — a shared hook
giving every right-side sheet a **drag handle on its left edge**:

- Drag with the mouse to any width between 360px and 95% of the viewport.
- The chosen width is remembered (`localStorage: mitre-sheet-width`) and
  shared by all three panels — TechniqueDrawer, DrillDownPanel,
  RuleListPanel — so the workspace feels consistent.
- Keyboard accessible: the handle is a focusable separator; ←/→ resize in
  40px steps.
- Phones are unaffected: the stored desktop width is clamped with
  `min(Npx, 100vw)`, so the sheet stays full-width on small screens.

### 2. "Ensure the entire mitre module is mobile friendly"

Audited every Phase-14 addition for fixed widths / overflow:

- Past-runs dropdown: `max-w-[calc(100vw-1.5rem)]` viewport clamp
  (was a fixed `w-80` that could clip on 390px screens).
- Assessment-header button row now wraps (`flex-wrap`) — four buttons no
  longer risk horizontal overflow on phones.
- All three sheets remain `w-full` on mobile (resize cannot shrink them).
- Pre-existing mobile guarantees (heatmap/table `overflow-x-auto`,
  wizard grids `sm:`-responsive, panels full-width) re-checked; the
  earlier 390px zero-overflow verification still holds for new surfaces.

### 3. "Summary tab of the Excel report more visually appealing + executive summary"

`apps/api/app/mitre/report.py` — the Summary sheet is now a sectioned,
styled page instead of a flat metric list (numbers unchanged):

- **Branded title band** (merged, brand-blue fill, white 14pt) with the
  project name + assessment name and the ATT&CK version/run date line.
- **EXECUTIVE SUMMARY section**: the run's narrative executive summary
  (AI or template), followed by the plain-words context line ("Of the 908
  techniques that apply… Is 2.1% bad? Probably not…").
- **KEY NUMBERS**: Coverage % value cell filled traffic-light
  (green ≥50 / amber ≥15 / red), state counts filled with their legend
  colors, per-matrix % rows color-filled, "What it means" column kept.
- **TOP 5 THINGS TO FIX FIRST**: rank + technique + name, effort cell
  filled by feasibility bucket, full recommendation text.
- **ABOUT THIS ASSESSMENT**: 14d metadata, ATT&CK version, narrative
  provenance, thresholds.
- Blue section-header rows separate the blocks; structure goldens
  (Coverage % present, Strict % gone) still pass unchanged.

### 4. "Heatmap shows only T-numbers — add short meaningful context, tooltip with smooth transition, solid background, no extra area per TTP" (screenshot #2)

`CoverageHeatmap.tsx`:

- Cells now render **"T0809 Data Destruction"** — ID bold + name
  truncated — in exactly the same cell footprint (names come free from
  the 14b read-time enrichment).
- **One delegated custom tooltip** serves all ~900 cells (a Radix
  tooltip per cell would be wasteful — the original design note): solid
  `bg-popover` background, border + shadow, 150ms fade/zoom entry, 120ms
  hover intent delay, viewport-clamped, shows "ID — Name", the
  plain-words state (or the verbatim N/A reason), and the click hint.
  Works on keyboard focus too; native `title` removed.
- Drawer nits from screenshot #1: ICS techniques no longer show
  "Applies to: None" (the dataset's literal "None"/PRE pseudo-platforms
  are hidden), and "This is **a** Inhibit…" became "an" (a/an by vowel).

### 5. "Reduce gaps-table row width ~50%, remove gutter/border/extra space, more meaningful Priority/Strength/Feasibility, less robotic color boxes" + "Assumptions & N/A looks like a 30-year-old html page" (screenshots #3/#4)

`GapsRoadmap.tsx`:

- Rows ~50% tighter: `px-2 py-1.5` cells, `h-8` compact headers,
  technique ID + name on one line.
- The pastel pill soup is gone — replaced with **small colored dots +
  plain text that says something**:
  - Priority: `● P1 · Critical` / `● P2 · High` / `● P3 · Medium`
    (violet `● Threat` when the threat profile matches).
  - Strength: `● 70 · Moderate`.
  - Feasibility: `● Build now (via Windows Event Logs)` /
    `● Onboard logs first` / `● New capability`.
  - Full explanations stay on hover; header definitions kept.

`AssumptionsNA.tsx`:

- Assumptions: two-column grid of compact accent-bordered cards instead
  of a full-width left-aligned list.
- N/A appendix: the four groups are now **cards in a two-column grid**,
  and within each card entries are **aggregated by reason** — 37
  identical "deprecated in ATT&CK v19.1" table rows collapse into one
  line with 37 technique chips. Every chip is clickable and opens the
  14a drawer; the group count still opens the 14b drill-down panel.

### 6. Follow-up fixes from live testing (deployed `4d579c2`)

- **"Page fluctuates on hover over TTPs"** (`9eabcd1`): the delegated
  tooltip mounted as the *first child* of the heatmap's `space-y-6`
  container, so every show/hide toggled the legend's sibling
  `margin-top` and shifted the page 24px. Moved to the last child
  (position:fixed — order is visually irrelevant).
- **"Happens when moving from one TTP to another"** (`4d579c2`):
  cell-to-cell movement unmounted and re-animated the tooltip on every
  transition. Now hover-intent: the mounted tooltip glides to the next
  cell instantly (`transition-[left,top]`), hide is delayed 120ms so
  the gap between adjacent cells never unmounts it, and the entry
  animation plays only on first appearance.
- **Collapsible matrices + legend filter** (`4d579c2`): Enterprise /
  ICS-OT / Mobile section headers collapse on click (chevron,
  aria-expanded); the legend's Covered / Partial / Not covered / N/A
  entries are now toggleable in-place filters (multi-select, dimmed
  inactive states, "Show all" reset) that filter the heatmap cells
  without leaving the page.

## Commits (all pushed, deployed at `4d579c2`)

| Commit | Contents |
| --- | --- |
| `6051af6` | Resizable panels (useSheetResize), heatmap ID+Name cells + delegated tooltip, drawer None/PRE + a/an fixes, mobile guards |
| `bdde5f5` | XLSX Summary redesign + executive-summary section |
| `4f93523` | Gaps-table density + dot badges; Assumptions & N/A card redesign |
| `9eabcd1` | Fix: hover page-jump (tooltip out of the space-y margin flow) |
| `4d579c2` | Smooth cell-to-cell tooltip; collapsible matrices; legend state filter |
| `35f5d40` | Report tables professional grid: bordered cells, brand-blue header rows, zebra striping; gap/top-5 entries as bordered cards; cover metadata stays borderless (CSS only, prod PDF render re-verified) |
| `a9534b5` | Report readability + space pass: no light-grey fonts (body #1f2937, muted/footer/TOC darkened to slate); tags visually distinct — filled state pills (green/amber/red/grey), P1/P2/P3 badges filled rose/amber/sky, stronger violet AI/threat badges; N/A appendix aggregated one-row-per-reason with technique lists; assumptions in two CSS columns; register + rule-mappings appendix tables compact (10px); gap/fix cards tightened. Prod render re-verified (aggregation + badges asserted in-container) |

## Verification

- `npx tsc --noEmit` clean after each step.
- Backend suite **800 passed / 7 skipped** after the XLSX rework (only
  backend change of the pass); frontend-only commits verified by tsc.
- Deploy loop run (`git pull → build → up -d` with GIT_SHA), all
  `scopewise-*` containers healthy; smoke: /login 200, /mitre 200, API
  401 unauth. Sample-kit regeneration re-run earlier confirms the
  redesigned Summary sheet renders with the executive section, key
  numbers, and top-5 rows populated.

## Next action

None pending — Phase 14 + polish fully deployed. The next natural check
is a real logged-in walkthrough on a phone plus regenerating the kit's
`result/` exports from prod. Open optional backlog unchanged
(Splunk/Elastic connectors, connections CRUD UI, deferred-UX list).
Tests pass: Y. Open questions: none.

## Agent utilization

- Opus (main): all five refinements end-to-end (hot cache, small
  interlocking UI diffs — delegation overhead would exceed the work)
- Sonnet / Haiku: n/a — no mechanical fan-out or bulk sweeps arose
- codex:rescue: n/a — presentation-only changes; no security-adjacent
  surface touched
