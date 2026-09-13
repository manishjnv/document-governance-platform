# Session handoff — 2026-09-13 — Complete app design canvas finished

**Headline:** all 15 authenticated screens (30 artboards, desktop + phone) pass the harness and
the label check and are published as Version 4 of
https://claude.ai/code/artifact/9f120be7-d49e-4651-8ea3-a103269b5e24. Design only; no `apps/web`
change. Owner reviewed the canvas the same day with no change requests; this session then wrote
the build plan, and a separate session built and deployed it (see below).

## Commits

| SHA | What |
|---|---|
| `8fc5e0d` | Results, MITRE detail, Code Review detail pass at both sizes; tooltips no longer widen pages; harness page-width check + `desktop_only` step flag |
| `62441b8` | Docs: README status, progress index, resume prompt stubbed, RCA #27, this handoff |
| `1b218aa` | Docs: `docs/planning/UI_REDESIGN_BUILD_PLAN.md` (five phases, restyle in place, tokens generated from `dc.py`, cheapest-tier routing) + `UI_REDESIGN_PHASE_0_PROMPT.md` |

## What was wrong and how it was fixed (detail in RCA #27 and the commit message)

- MITRE detail: a builder had dodged the overflow check with an inert `.ov` class; replaced by a
  real scroller and a harness that ignores scroller content. Sheets and the run picker are closed
  between scripted steps (they intercepted later clicks, on phone especially).
- Code Review detail: graph node labels were holes inside SVG `<text>` (drawn as nothing); now
  static. Row click retargeted to the title cell because the CWE link cell stops propagation.
- Hidden CSS tooltips added up to 90 px of page scroll on three screens; `display:none` until hover.

## Open

The plan was executed the same day by another session: Phases 0-4 built, deployed on both hosts,
RCA #28-30, handoff `SESSION_HANDOFF_2026_09_13_UI_REDESIGN.md`, status in the plan's §0. Still
open there: real-data screenshot pass on the three detail pages, Admin People no-match state.
Everything else pending is unchanged from the 2026-09-12 handoffs.

## Agent utilization

- Opus (main): diagnosis with Playwright probes, all fixes, full sweep, reseed, publish, docs.
- Sonnet: n/a — the three WIP modules from yesterday's builders were finished in-session (small targeted edits).
- Haiku: n/a.
- codex:rescue: n/a — no product code changed.
