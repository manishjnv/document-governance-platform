# Session handoff — 2026-09-13 — Complete app design canvas finished

**Headline:** all 15 authenticated screens (30 artboards, desktop + phone) pass the harness and
the label check and are published as Version 4 of
https://claude.ai/code/artifact/9f120be7-d49e-4651-8ea3-a103269b5e24. Design only; no `apps/web`
change. Next: owner review pass on the live canvas.

## Commits

| SHA | What |
|---|---|
| `8fc5e0d` | Results, MITRE detail, Code Review detail pass at both sizes; tooltips no longer widen pages; harness page-width check + `desktop_only` step flag |
| (this) | Docs: README status, progress index, resume prompt stubbed, RCA #27, this handoff |

## What was wrong and how it was fixed (detail in RCA #27 and the commit message)

- MITRE detail: a builder had dodged the overflow check with an inert `.ov` class; replaced by a
  real scroller and a harness that ignores scroller content. Sheets and the run picker are closed
  between scripted steps (they intercepted later clicks, on phone especially).
- Code Review detail: graph node labels were holes inside SVG `<text>` (drawn as nothing); now
  static. Row click retargeted to the title cell because the CWE link cell stops propagation.
- Hidden CSS tooltips added up to 90 px of page scroll on three screens; `display:none` until hover.

## Open

Owner review of the live canvas; then the build plan (page by page under `apps/web`, README lists
what the design unifies). Everything else pending is unchanged from the 2026-09-12 handoffs.

## Agent utilization

- Opus (main): diagnosis with Playwright probes, all fixes, full sweep, reseed, publish, docs.
- Sonnet: n/a — the three WIP modules from yesterday's builders were finished in-session (small targeted edits).
- Haiku: n/a.
- codex:rescue: n/a — no product code changed.
