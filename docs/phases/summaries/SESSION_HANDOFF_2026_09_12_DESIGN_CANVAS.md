# Session handoff — 2026-09-12 (night) — Complete app design canvas

**Headline:** the complete-app redesign is a working interactive canvas for 12 of 15
authenticated screens (desktop + phone), verified by an automated harness and a
label-completeness check, committed under `docs/design/complete-app-2026-09-12/`. Three
screens (SOW review results, MITRE assessment results, Code Security Review detail) exist as
modules but still fail checks and are not on the published canvas yet. Design only: no
`apps/web` change.

Canvas: https://claude.ai/code/artifact/9f120be7-d49e-4651-8ea3-a103269b5e24

## Decisions (owner)

- Typeface IBM Plex Sans / Plex Mono, no serif; ink `#14181F`; colour only for meaning.
- Scope: every screen a signed-in user can reach today; API-only features and unwired
  components out of scope (listed in the README).
- Every screen interactive; states via a `view` tweak (default/loading/empty/error/gated).
- Plan approved: `C:\Users\manis\.claude\plans\now-reivew-scopewire-complate-synthetic-gizmo.md`
  (also summarised in the README).

## What is done (all pass harness at 1440 and 390: mounted, no `{{` leak, no console errors,
no horizontal overflow, every scripted interaction asserts real state)

| Stem | Screen | Commit |
|---|---|---|
| Main | design system sheet (type, colour + contrast, buttons, chips, inputs, dropzone, alerts, table, KPI, sheet, dialog, tabs, tooltip, empty, skeleton, app bars) | `0318b77` |
| CodeReviewList | Code Security Reviews list | `0318b77` |
| Dashboard | SOW Review dashboard (grouped project table, search mode, inline editors, suggestion banner, request-access + delete dialogs) | `ebd14b2` |
| Login, Upload, ProjectDetail, VersionsDiff | | `32dfd4f` |
| MitreList, MitreConnections | | `b64c18c` |
| MitreNew | intake wizard, parse preview, column wizard, gated state | `c77a8c0` |
| Admin | KPIs, organisations tier/run-allowance, people, feeds, AI usage | `4178fc9` |
| CodeReviewNew | scanner kit + upload cards | this commit (WIP commit) |

## Not finished (modules committed as work in progress; not on the canvas)

| Stem | Module | Last harness result | What is left |
|---|---|---|---|
| Results | `screens/results.py` (27 KB) | mounts, no leak/errors; **overflow** (document pane `aside.card.docpane` and `.secitem` rows extend to 1518px, the split pane is not width-constrained); severity-tile and clear-filter clicks fail | constrain the split pane (`min-width:0`, percentage widths), fix filter handlers, rerun `harness.py --screens Results` desktop + phone |
| MitreDetail | `screens/mitre_detail.py` (112 KB) | mounts, no leak/errors; **overflow** (matrix grid not inside an `overflow-x:auto` wrapper, elements at 1762px); cell → TechniqueDrawer click and "tagged by you" chip click fail; 2 labels missing (Navigator tooltip, hide-sub-techniques tooltip) | wrap the matrix, fix the two click targets, add the two tooltip strings |
| CodeReviewDetail | `screens/codereview_detail.py` (76 KB) | mounts, no errors; **`{{` placeholder leak** somewhere in the rendered HTML; graph node click, row → drawer, drawer Next fail | find the unreplaced hole (grep the generated `CodeReviewDetail.dc.html` for `{{` after render), fix the three interactions |

Three Sonnet builders may still have been editing these files when the session ended; the
on-disk state at commit time is what is committed. Tomorrow: run the loop per screen
(`python gen.py --only <Stem> && python check_labels.py && python harness.py --screens <Stem>
--out <scratch> [--phone]`), then the full sweep, reseed with all 15, republish.

## How the toolchain works (read before touching it)

- `dc.py`: tokens (calm light), inline icons, AppShell, primitives (`btn`, `chip`, `kpi`,
  `tabs/panel`, `sheet`, `dialog`, `kebab`, `dth/dcell` div tables, `dropzone/filerow`,
  `states`, `alert`, `request_access_form`), `screen()` assembler. `logic.js`: runtime helper
  methods (`shellVals`, `tabVals`, `sheetVals/openSheet/closeSheet`, `dlgVals/openDlg`,
  `menuVals`, `lbVals`, `sortVals`, `dropVals`, `renameVals`, `runBusy`, `setIn`).
- `gen.py` auto-discovers `screens/*.py` (`STEM, PAGE, TITLE, ORDER, DATA, BODY, VALS,
  CLICKS, build`), writes `<Stem>.dc.html` + `<Stem>Phone.dc.html`, `canvas.json`,
  `clicks.json`; skips a module that fails to import unless requested with `--only`.
- `check_labels.py`: every string in `labels.json` + `labels/<Stem>.json` must appear in the
  artboard (normalised); shell labels only where `aria-label="Sidebar"` exists.
- `harness.py`: renders artboards **standalone** with the real Design Components runtime
  (React, ReactDOM, support.js extracted from the design skill payload; set `DC_RUNTIME` to the
  folder holding `reactUmd.js`, `reactDomUmd.js`, `supportJs.js`; extraction script
  `extract_runtime.py` lived in the session scratchpad — recreate it from the memory note
  `design-canvas-toolchain` if the scratchpad is gone). The Claude Design editor does not mount
  artboards reliably headless; do not verify through it.
- Publishing: seed with the design skill helper (`seed-canvas.mjs --template … --artboard …
  --canvas …`), `--check`, then republish the same file path with `contract "0.1.31"` and the
  same favicon to keep the URL.

## Gotchas hit today (so nobody repeats them)

- Eight parallel Sonnet builders hit the account's 5-hour session limit at once (reset 21:00
  IST); rerun in waves of ≤4. One builder died on the 64k output cap writing a 100 KB module in
  one response: tell builders to write big modules in two `Write` calls.
- Holes render as text; icon swaps need two `<sc-if>` branches. `translateX(0)` serialises as
  `translateX(0px)`. `<sc-for>` inside `<tbody>` is parser-unsafe (use div tables). `.rise`
  on remounting elements looks invisible in screenshots. Chip text colours were darkened to
  ≥5.2:1 on tints.
- Observer sessions sent conflicting specs twice (static Inter HTML + a `globals.css` edit);
  declined; tree verified clean each time.

## Agent utilization

- Opus (main): plan, framework (dc.py, logic.js, gen.py, harness, label check, inventories, contract), Dashboard and Admin screens, integration, verification, docs.
- Sonnet: Login/Upload/ProjectDetail/VersionsDiff (reworked: N) · MitreList+MitreConnections (N) · MitreNew (N) · CodeReviewNew+Detail (WIP) · Results (WIP) · MitreDetail (WIP) · Admin (died on output cap, rebuilt by Opus) · architecture plan agent (N) · market research earlier in the day (N).
- Haiku: n/a — inventories needed judgement (Explore agents used).
- codex:rescue: n/a — no product code changed.
