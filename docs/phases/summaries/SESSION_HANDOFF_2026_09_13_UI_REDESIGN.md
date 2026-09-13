# Session handoff - 2026-09-13 - UI redesign Phases 0-4 built

**Headline:** every authenticated screen of `apps/web` is restyled to the calm-light design canvas
in 29 commits (`daae552`..`19344f2`), pushed and **deployed** on scopewise.assessiq.in (Haiku smoke clean there; its scopesense.in 200s were a false positive, see RCA #31 — that host's cut-over is still blocked on Cloudflare zone activation; Lighthouse mobile on `/dashboard` 68/100/100/63, accessibility gate holds). Reference: `docs/planning/UI_REDESIGN_BUILD_PLAN.md` section 0.

## Commits (one per screen or unit)

| Phase | SHAs |
|---|---|
| 0 tokens, fonts, shell, login, primitives | `daae552` `eb7b44a` `a0f8d79` |
| 1 shared `components/app/*`, table primitive, SOW screens | `161e5ac` `4309b19` `cbeb3ef` `3137619` `ee83566` `fcbd3d3` `771edc9` |
| 2 MITRE list, new, connections, detail (2) | `61ac46a` `82938f6` `1a9d9c0` `5cca31c` `3123123` |
| 3 Code Review list, new, detail + drawer, SeverityBar, overflow fix | `cc69401` `3215758` `8a640c6` `e162bc4` `6de58dd` |
| 4 admin, install and update bar, request-access form, skip link | `8c42c9f` `8d03a5a` |
| 5 docs, sweep script + references, deploy notes, CLAUDE.md skill values | `5327a35` `06bd700` `a2dfaf2` `f062cfe` `40d614a` `19344f2` |

Gates: `tsc` clean; per-screen label check (all misses are pre-existing design sample strings);
Playwright 1440/390 on every route, no page overflow, `/` untouched. RCA #28-#30 added.

## Also this session (outside the repo)
User-level skill `~/.claude/skills/ui-design-workflow/SKILL.md` (project-agnostic UI workflow), a global-playbook rule to load it on every UI task, a Desktop copy for Claude Design web, and project memories `ui-redesign-status-2026-09-13` + `feedback-ui-design-workflow-skill`.

## Next action
Deployed and smoke-tested on scopewise.assessiq.in (15/15 routes 200, theme scoping, self-hosted Plex, API healthy). scopesense.in: NOT live — zone pending at Cloudflare, no Caddy block/cert yet; finish per `SCOPESENSE_DOMAIN_CUTOVER.md` once the owner clicks "Check nameservers" in the dashboard. Still open: the Phase 5 real-data
smoke (routes 200, `app-theme` on app pages only, Plex served from `/_next/static/media`,
Lighthouse on `/login` and `/dashboard`). Open: Admin People no-match state (needs a filter variable).

## Agent utilization
- Opus (main): plan and kickoff reads, both tooling scripts (Tier 2 fell back), every diff review, 5 direct fixes (badge hover, table primitive, login sentence, SeverityBar swap, import overflow), screenshots, docs.
- Sonnet: 16 builders (shell+primitives, login, app primitives, 12 screens, cross-cutting) - reworked: N (two follow-up fixes done by Opus after review).
- Haiku: 1 live smoke (route grid on both hosts, theme scoping, fonts, API) - reworked: N (one false positive on the login root, dismissed).
- codex:rescue: n/a - no auth or security logic changed (AppShell token effect untouched).
- Tier 2 (`or.mjs dsf`) - theme + label scripts - reworked: Y (HTTP 403 key limit; Opus wrote them directly).
