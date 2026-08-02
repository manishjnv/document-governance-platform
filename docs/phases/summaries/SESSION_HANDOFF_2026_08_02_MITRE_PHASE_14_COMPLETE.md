# Session handoff — MITRE Phase 14 COMPLETE (14a–14g), 2026-08-02

**Headline:** the entire UX-clarity phase shipped in one session — all
seven sub-phases of `docs/planning/MITRE_UX_CLARITY_PLAN.md` implemented,
tested, committed one-per-sub-phase, and deployed to prod. **No
migrations** anywhere in Phase 14 (metadata + archive flags ride existing
JSONB). Full backend suite **781 → 800 passed / 7 skipped**; `npx tsc
--noEmit` clean throughout.

## Commits (in order)

| Commit | Sub-phase | Delivered |
| --- | --- | --- |
| `98c82b0` | 14a | Drawer four plain-language blocks; curated `technique_plain_language.json` (57) + `tactic_lines.json` (21); pure `plain_language.py` (describe / sketch / golden-tested `derive_why`); `GET .../techniques/{tid}/explain` |
| `eea44e3` | 14b | Every number clickable: DrillDownPanel + RuleListPanel behind tiles, heatmap headers, N/A counts, rule chips, wizard preview tiles; names enriched into GET; headline subtitle + "is this % bad?" popover; microcopy fixes |
| `4a2325f` | 14c | XLSX polish: Read Me sheet, color fills, register Name/plain-words/Why, numeric sort, feasibility-grouped gaps, Summary explanations |
| `36415d2` | 14d | Project metadata (params.intake), files[] in GET, wizard inputs, header line, UploadSummaryCard; **also lands the 14g parser** (additive per-entry environment `interpretations`) |
| `c15ab34` | 14e | PDF redesign: cover + TOC (`target-counter` page numbers), ≤2-page executive (scorecard, top-5 fixes, effort-to-impact, trend vs previous run), stacked bars, heatmap grids, feasibility-grouped gap register with why/sketch/via/AI badge, evidence appendix, running header |
| `c64b324` | 14f | Past-runs dropdown (delta + Compare shortcut), list search/filter/sparkline/project names, inline rename + soft archive via `PATCH /assessments/{id}` (JSONB flag, no deletes; archived stays in Compare) |
| `bee1f8f` | 14g | Evidence trail: explain `expected_telemetry` + `in_scope_because`; rule-panel mapping journey (source/confidence/rationale verbatim); XLSX How-We-Read-Your-Files sheet; threat-profile-matches chip |

Earlier the same session: 14a deployed standalone (`db0726b`), sample kit
+ Phase 14 plan docs committed (`58384f6`, `5ae5b27`).

## Design decisions worth remembering

- The plan's "~150 curated techniques" was an overestimate — the
  deterministic rule (priorities ∪ threat profiles) yields **57**, and the
  dataset has **21** tactic shortnames (not 12, thanks to v19's enterprise
  stealth/defense-impairment split). Tests enforce both rules, so the
  files can't drift.
- `plain_language.derive_why` is the single why-phrase source for the
  drawer, the XLSX Why column, and the PDF gap register — one derivation,
  three surfaces.
- 14g's only backend addition is the additive `interpretations` output of
  `parse_environment_file` (+ persistence in `params.environment_lists`);
  everything else surfaces already-persisted provenance. Pre-14g
  assessments degrade gracefully (empty evidence lists).
- Rename/archive is a `params` JSONB flag + the existing `name` column —
  the "two nullable columns" option was not needed.

## Verification

- Full suite **800 passed / 7 skipped** (solo on edgp_test, checked
  pg_stat_activity first). `tsc --noEmit` clean.
- Deployed to VPS (standard loop, no migrations) and smoke-tested:
  containers healthy, /login + /mitre 200, API 401 unauth.
- The prod-only WeasyPrint render test remains the 7th skip locally; the
  new template renders via the same lazy-import path (verified live in
  the post-deploy smoke below).

## Next action

Phase 14 closes the planned UX work. Open (optional, on request only):
Splunk/Elastic connectors, connections CRUD UI, deferred-UX list at the
bottom of `MITRE_UX_CLARITY_PLAN.md`. Tests pass: Y. Open questions:
none.

## Agent utilization

- Opus (main): all seven sub-phases end-to-end (design, curated content,
  code, tests, docs, deploy) — hot-cache self-execution; no mechanical
  N-file rollout arose to delegate
- Sonnet: n/a — no delegable mechanical work
- Haiku: n/a — no bulk sweeps
- codex:rescue: n/a — presentation/UX phase on org-scoped read paths +
  one audited housekeeping PATCH reusing existing RBAC helpers; not
  security/auth/classifier-adjacent (scale-rigor note per playbook)
