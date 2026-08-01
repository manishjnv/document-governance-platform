# Session handoff — 2026-08-01: MITRE Phases 0 + 1 + 2 + 3 complete

> Phases 2 and 3 were appended the same day (evening/night sessions) —
> see the dated sections at the bottom. Phases 0-2 are committed and
> deployed to prod; Phase 3 (frontend) is uncommitted working tree.

**Headline:** MITRE ATT&CK coverage assessment Phases 0 (pinned v19.1 data +
pure applicability/coverage logic) and 1 (migration 029, models, ingest,
API, tagged-only end-to-end) are both implemented and verified. Full suite
**622 passed / 6 skipped, 0 failures** (new baseline; was 606). Live
dev-server smoke run of create→run→poll→results produced correct states
and percentages. Nothing committed by this session (user has not asked);
migration 029 is applied to `edgp_dev` + `edgp_test`, NOT prod.

**Commits this session:** none by this session. A parallel session
committed `scripts/build_attack_data.py` mid-flight (`0ae0908`, `ba645bc` —
content matches this session's final version) plus unrelated blog/doc
commits. All other MITRE files are uncommitted working-tree state.

**Tests pass:** Y (622/6; mitre-only: 39 across 4 files).
**Next action:** Phase 2 per `docs/planning/MITRE_ASSESSMENT_PLAN.md` §13 —
MitreTaggingAgent + MitreNarrativeAgent (read
`docs/planning/PROMPT_ENGINEERING_GUIDE.md` first).
**Open questions:** `technique_priorities.json` still pending the user's
10-minute review before Phase 2 bakes it into gap ranking; audit
resource_type decision (below) worth revisiting in Phase 5.

## What exists now

- `scripts/build_attack_data.py` — ATT&CK v19.1 pinned builder
  (enterprise 858 techniques/15 tactics, ics 118/12, mobile 190/14).
- `apps/api/app/mitre/` — `data/attack.json` (0.7 MB, checked in),
  `data/technique_priorities.json` (40 curated techniques, tiers 1–3,
  **pending user review**), `attack_data.py`, `applicability.py`,
  `coverage.py`, `ingest.py`, `service.py`, `router.py`.
- `apps/api/migrations/029_mitre_assessment.sql` — `mitre_assessments`,
  `mitre_files`, `mitre_use_cases`, `mitre_settings`; new tables only,
  zero ALTERs; applied to dev + test, **prod pending Phase 5**.
- Models `MitreAssessment/MitreFile/MitreUseCase` + registry entries.
- Tests: `test_mitre_applicability.py` (14), `test_mitre_coverage.py` (10
  incl. shared fixture), `test_mitre_ingest.py` (10), `test_mitre_api.py`
  (6, real-Postgres E2E incl. org isolation, 409, stale-run guard,
  settings RBAC).
- Shared files touched (the allowed set, both additive): `main.py`
  (+import, +include_router appended last), `app/models/__init__.py`
  (+3 model imports/`__all__` entries).

## Deviations from the Phase 1 prompt (all deliberate, with reasons)

1. **`compute_coverage` gained optional threshold kwargs**
   (`covered_confidence`, `partial_confidence`, `partial_weight`,
   defaulting to the module constants). Without them the
   `mitre_settings` tunables the prompt mandates would be dead knobs.
   Signature is backward-compatible; Phase 0 tests unchanged.
2. **`applicability.py`: "None" platforms exempt from filtering.** Every
   active ICS technique in v19.1 carries platforms `["None"]`; the
   Phase 0 filter would have N/A'd all of ICS whenever ICS was enabled.
   "PRE"/"None" are now treated as environment-independent markers.
3. **Audit rows use `resource_type="organization"`.**
   `audit_logs.resource_type` has a closed DB CHECK
   (document/review/finding/user/organization); extending it requires an
   ALTER (forbidden in Phase 1) plus an `enums.py` edit (outside the
   allowed shared-file set). The `mitre.*` action strings carry the
   semantics. Revisit in Phase 5 if a proper enum value is wanted.
4. **tz-aware timestamps throughout the module** (not the house naive
   `datetime.utcnow()`): naive writes into `timestamptz` get interpreted
   in the +05:30 session timezone, which made the 30-min stale-run guard
   fire instantly. Aware `datetime.now(timezone.utc)` is unambiguous.
5. **No .xls ingest test:** no xls *writer* is installed (xlrd reads
   only), so a fixture can't be built in-test; the xls code path is
   symmetric with xlsx.

## Gotchas for future phases

- ATT&CK v19 restructured defense tampering: T1562.001→T1685,
  T1070.001→T1685.005 (customer tags auto-remap; priorities file uses the
  new IDs). Mobile T1454 is revoked upstream with no successor
  (allowlisted in the build script's validation).
- Tag validation happens at CREATE time (so the parse preview can show
  the tagged/untagged/invalid split); the run pipeline consumes the
  persisted mappings. Phase 2's AI tagging should slot in between create
  and run (or as a run stage) for `unmapped`/`invalid` rows only —
  customer tags are never re-tagged.
- The run task is fire-and-forget `asyncio.create_task` with strong refs
  in `router._RUNNING_TASKS`; container restart kills it — the GET
  stale-run guard (30 min) is the recovery path.
- `mitre_settings` values are JSONB; `service.get_mitre_settings` handles
  asyncpg returning them as JSON strings.
- Cross-org access returns 404 (org-scoped query), not 403 — matches
  no-info-leak preference; tests assert 404.

## Phase 2 (evening session, 2026-08-01) — LLM tagging + narrative + ranking

**Done:** `app/mitre/agents.py` (MitreTaggingAgent with tagging +
extraction prompt modes selected via the `document_type` param;
MitreNarrativeAgent; `_call_with_retry` 60s/120s; `tag_untagged_rows` /
`extract_use_cases_from_text` / `generate_narrative` drivers with
degrade-to-unmapped / degrade-to-template), `app/mitre/ranking.py` (pure
tier → feasibility → tactic ranking; log-source/tooling → ATT&CK
data-component-category keyword bridge; short/mid/long roadmap),
pipeline wiring in `service.py` (extract → AI-tag → applicability →
coverage → rank → narrative → persist; `MitreAssessmentError` for the
all-batches-failed + zero-customer-tags case; `params.models_used`),
`router.py` pdf/docx path (parse text at create + unreadable-text 422;
AI extraction at run time — the Phase 1 "next release" 422 is gone).
Changelog section added to `PROMPT_ENGINEERING_GUIDE.md`. Tests: +14
(`test_mitre_agents.py` 10, `test_mitre_ranking.py` 4; LLM always faked;
`test_mitre_api.py` gained an autouse no-LLM stub so a local key can
never leak into tests). Full suite **636 passed / 6 skipped**.

**Live smoke status: PENDING.** The local OpenRouter key is over its
account spending cap — 403 "Key limit exceeded (total limit)" on all 4
chain models. The smoke run still proved the failure discipline live:
chain walked, one retry, batch degraded to unmapped, narrative fell back
to template, assessment completed with honest assumptions. The
AI-tagging quality spot-check (5 hand-checked mappings, models used,
cost) must be re-run once the cap resets — script pattern:
mixed 2-tagged/6-untagged dump through create → run → results.

**Phase 2 gotchas for Phase 3+:** summary JSONB now carries `gaps`
(ranked list), `roadmap` (short/mid/long buckets of the same gap dicts),
and `narrative` (`generated_by: "ai"|"template"` + `model_used`) — the
frontend should surface the template-fallback flag. `counts` gained
`ai_tagged`. Preview gained `extraction_pending`. The ranking
feasibility bridge is deliberately coarse keyword matching (documented
in-file); Sysmon counts as network telemetry (event 3), which is why a
network-only gap can be "short" for a Sysmon shop.

## Phase 3 (night session, 2026-08-01) — frontend

**Done:** `apps/web/app/mitre/` — `lib.ts` (types mirroring router.py
responses + STATE/FEASIBILITY/TIER display metadata with plain-English
tooltip copy), list page, `/mitre/new` wizard (privacy notice → dual
drag-drop with client validation → intake incl. scope-exclusions editor →
inline parse preview with detected-column chips → run → redirect),
`/mitre/[assessmentId]` results (5s visibility-aware polling, re-run for
failed/pending, executive band, CSS-grid tactic heatmap, technique
drawer on shadcn Sheet, ranked gap table + roadmap with
`narrative.generated_by` badge, assumptions + grouped N/A). Components
under `app/mitre/components/` (props-only): ExecutiveBand,
CoverageHeatmap, TechniqueDrawer, GapsRoadmap, AssumptionsNA,
StateBadge. Templates in `public/templates/` (verified through the real
`ingest.py` parser before check-in). One shared-file edit: the
AppShell.tsx NAV_ITEMS entry (`Target` icon). `tsc --noEmit` clean.

**Browser-verified** (playwright-core in the scratchpad + existing local
chromium — nothing added to the app): full walk on a seeded
customer-tagged assessment (empty list → wizard → preview: 5 rules /
5 tagged → run → completed results), drawer showed the mapped rule with
enabled/source/confidence/log-source, all three tabs rendered, exclusion
reason appeared verbatim in the N/A appendix, list showed the coverage
bar. Mobile 390px: 0px horizontal overflow on list/new/results/all tabs
after fixing one real bug — the roadmap grid needed `grid-cols-1`
(minmax(0,1fr)) so nowrap truncate items can't force page overflow.

**Deviations:** (1) per-domain mini-bars on the LIST page skipped — the
list endpoint only returns headline %s; fetching full technique_results
per row just for mini-bars is wasteful. Extend the list endpoint with
per-domain %s in Phase 4 (it touches summary shape anyway) and add the
bars then. (2) Heatmap cells use click→drawer + native `title` hover
instead of a Radix tooltip per cell (~700 portals would be waste);
shadcn tooltips cover tiles, badges, %s, tier/feasibility chips, and
legend. (3) Local dev CORS note: the API's CORS_ORIGINS default doesn't
include the 3005 dev port — the click-through ran the API with
`CORS_ORIGINS=http://127.0.0.1:3005`. Not a code change; worth knowing
for local UI work.

## Agent utilization

- Opus/Fable (main): everything across Phases 0-2 — recon, design
  judgment, all implementation, tests, smoke runs (kickoff prompts
  target the main session; contracts too interlocked to delegate
  profitably).
- Sonnet: n/a — no delegation this session.
- Haiku: n/a — no bulk sweeps needed.
- codex:rescue: n/a — broken on this account (memory 2026-07-23); the §11
  adversarial sign-off is a Phase 5 gate, not due yet (Sonnet-takeover
  planned there).
