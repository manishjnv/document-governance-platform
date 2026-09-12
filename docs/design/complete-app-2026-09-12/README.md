# ScopeWise complete app design — interactive canvas (2026-09-12)

Live canvas: https://claude.ai/code/artifact/9f120be7-d49e-4651-8ea3-a103269b5e24

Design only. Nothing under `apps/web` changed. Every authenticated screen of the app is
redesigned in one calm-light system and rebuilt as a working prototype (tabs, sheets, dialogs,
menus, filters, sorting, inline rename, drag resize) at desktop (1440) and phone (390) size.

## Decisions (owner, 2026-09-12)

- Typeface: IBM Plex Sans everywhere, IBM Plex Mono for ids and code. No serif.
- Text: primary ink `#14181F`, secondary `#3B4453`, labels `#5E6877`; nothing lighter carries content.
- Colour only where it carries meaning: severity (critical/high/medium/low/info), coverage state,
  status, deltas, active navigation. Chip text is ≥ 5.2:1 on its tint; body text ≥ 9:1 on paper.
- Scope: everything a signed-in user can reach today. API-only features and unwired components
  are out of scope (listed below) so nothing is silently dropped.
- Fidelity: every screen interactive; states (loading / empty / error / gated) are switchable
  with the `view` tweak on each artboard instead of extra frames.

## What is on the canvas

Status 2026-09-12 night: **12 of 15 screens published and passing**; `Results`, `MitreDetail`
and `CodeReviewDetail` exist as modules but fail the harness (see the handoff
`docs/phases/summaries/SESSION_HANDOFF_2026_09_12_DESIGN_CANVAS.md`) and are not on the
canvas yet. Resume with `docs/phases/prompts/DESIGN_CANVAS_RESUME_PROMPT.md`.

| Page | Artboards (desktop + phone) | Status |
|---|---|---|
| Shell & system | `Main` — type ramp, colour/contrast, buttons, chips, inputs, dropzone, alerts, table, KPI tiles, sheet, dialog, tabs, tooltip, empty, skeleton, app bars | done |
| SOW & RFP Review | `Dashboard`, `Upload`, `ProjectDetail`, `VersionsDiff` | done |
| SOW & RFP Review | `Results` | module written, overflow + filter clicks failing |
| MITRE ATT&CK Coverage | `MitreList`, `MitreNew`, `MitreConnections` | done |
| MITRE ATT&CK Coverage | `MitreDetail` | module written, matrix overflow + drawer clicks failing, 2 labels |
| Code Security Review | `CodeReviewList`, `CodeReviewNew` | done |
| Code Security Review | `CodeReviewDetail` (with the finding drawer) | module written, placeholder leak + 3 clicks failing |
| Admin & auth | `Admin`, `Login` | done |

Sticky notes on each page list the interactions to try on every screen.

## Completeness

`inventory/*.md` is the verbatim inventory of the live app (every route, control, state, label,
placeholder, tooltip, empty and error copy), produced by a code sweep of `apps/web` on
2026-09-12. `labels.json` + `labels/*.json` hold every string from it per screen;
`check_labels.py` fails if any string is missing from its artboard. `harness.py` renders each
artboard standalone with the real Design Components runtime, checks for placeholder leaks,
runtime errors and horizontal overflow at both sizes, and clicks through every interaction in
`clicks.json` with state assertions.

Unified on purpose (called out in the artboards): one severity ramp instead of three; one
score band set; one resize grip behaviour (drag, ArrowLeft/Right, remembered width) for the
sidebar, the results split and every sheet; a destructive dialog instead of `window.confirm`;
card rows on phone for every table; loading skeletons and empty states where the app has none.

Out of scope (exists in the API or repo but has no screen today): CSV export helper, search
history and saved searches, search filters and pagination, filter templates, text version diff,
duplicate/similar detection, bulk review, analytics/insights, comments, approvals, notifications,
teams, compliance, governance, predictions, knowledge base, offline queue; unwired components
AnalyticsChart, KnowledgeBaseSearch, MultiCriteriaFilter, OrgMemberManagement, SearchFilter,
SearchResults, VersionComparison, sync-status-indicator.

## Files

```
dc.py            tokens, icons, primitives, AppShell, assembler (one self-contained .dc.html per screen)
logic.js         runtime helpers (shell, tabs, sheets, dialogs, menus, sort, dropzones, rename, busy)
screens/*.py     one module per screen: STEM, PAGE, TITLE, ORDER, DATA, BODY, VALS, CLICKS, build()
gen.py           python gen.py [--only Stem]  -> *.dc.html, canvas.json, clicks.json
check_labels.py  completeness check against labels.json + labels/*.json
harness.py       standalone render + interaction check (needs DC_RUNTIME, see below)
inventory/       verbatim inventories: sow.md, mitre.md, codereview_admin_login.md
CONTRACT.md      the builder contract every screen follows
```

Regenerate and verify:

```
set PYTHONUTF8=1
python gen.py && python check_labels.py
set DC_RUNTIME=<folder with reactUmd.js reactDomUmd.js supportJs.js extracted from the design payload>
python harness.py --screens Dashboard,MitreDetail --out <scratch>   (add --phone for 390px)
```

The runtime files are extracted from the design skill's payload (`extract_runtime.py` in the
session scratchpad); they are not committed. Reseed the canvas with the design skill's helper
and republish to the same artifact URL.
