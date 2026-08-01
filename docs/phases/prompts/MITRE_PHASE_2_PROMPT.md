# Kickoff prompt — MITRE Assessment Phase 2 (LLM tagging + narrative + gap ranking)

Self-contained kickoff prompt. Paste everything below the line into a
fresh session (target model: Fable 5 main session).

---

Implement **Phase 2** of the MITRE ATT&CK coverage-assessment feature for
ScopeWise. `docs/planning/MITRE_ASSESSMENT_PLAN.md` (§7 pipeline stages
3/6/7, §13 Phase 2) is the authoritative design — do not re-litigate
decisions recorded there.

## Context

ScopeWise: AI SOW/RFP review platform (FastAPI `apps/api`, Next.js
`apps/web`). The MITRE module is a new isolated feature: customer uploads
a SIEM use-case dump + environment workbook + intake, gets a
deterministic ATT&CK coverage/gap assessment. **Numbers are pure Python;
LLM contributes only tagging and narrative — that LLM part is this
phase.**

**Status:** Phases 0+1 COMPLETE, independently verified 2026-08-01.
Baseline: **622 passed, 6 skipped** (per root CLAUDE.md; includes 39
mitre tests). Working, on disk (uncommitted unless the user has since
committed — check `git log`/`git status` at start):

- `app/mitre/data/attack.json` (pinned ATT&CK v19.1) +
  `technique_priorities.json` (40 curated techniques, tiers 1–3).
- `app/mitre/{attack_data,applicability,coverage}.py` — pure logic.
  `compute_coverage` accepts threshold kwargs (wired to `mitre_settings`
  org tunables: confidence_covered=0.7, confidence_partial_floor=0.4,
  partial_credit=0.5, count_disabled_as_coverage=false).
- `app/mitre/{ingest,service,router}.py` — migration 029 applied to
  edgp_dev + edgp_test (NOT prod), full tagged-only E2E works: create →
  parse preview → run (fire-and-forget task, 30-min stale guard) →
  results. Untagged rows currently get `mapping_status='unmapped'`;
  pdf/docx dumps currently 422 with a "next release" message. Both are
  what THIS phase replaces.

**Phase 1 quirks you inherit (all deliberate, in the handoff doc):**
mitre module uses **tz-aware UTC datetimes** (house naive-`utcnow()`
misbehaves on timestamptz in +05:30 sessions — keep aware UTC in all new
mitre code); ICS techniques carry `platforms=["None"]` (applicability
already handles it); audit rows use `resource_type="organization"`
(closed DB CHECK; proper enum extension deferred to Phase 5).

**Roadmap:** P0 ✅ P1 ✅ → **P2 (THIS): MitreTaggingAgent +
MitreNarrativeAgent + deterministic gap ranking/roadmap + pdf/docx
extraction + assumptions assembly** → P3 frontend → P4 reports + trend →
P5 sign-off + deploy.

**Isolation contract for Phase 2:** edit ONLY files under
`apps/api/app/mitre/`, add new test files, and append to
`docs/planning/PROMPT_ENGINEERING_GUIDE.md` (changelog). **Zero
pre-existing code files change this phase.** Never register the new
agents in `ReviewOrchestrator.agents` (a 7th registered agent silently
corrupts every review's status math); never touch the 6 persona classes;
never hand-edit the auto-generated `prompts/` mirror (its generator only
covers the 6 review agents — MITRE prompts are documented in the guide
only).

## Read first (one parallel burst), then state your plan in a few lines

1. `docs/planning/PROMPT_ENGINEERING_GUIDE.md` — **mandatory before
   writing any prompt** (root CLAUDE.md rule); your two new prompts get
   changelog entries there.
2. `app/ai/agent.py` — the `ConflictDetector` subclass precedent (inherit
   the OpenRouter client, GLM-5.2 → DeepSeek → MiniMax → Qwen fallback
   chain, unparseable-JSON-advances-chain, `asyncio.to_thread`,
   `_model_used` stamping, `_parse_response`), plus
   `_CONFIDENCE_CALIBRATION`.
3. `docs/planning/AI_MODEL_ROUTING.md` — why the chain is ordered as it
   is; max_tokens history (8000, do not lower).
4. Current `app/mitre/{service,ingest,coverage}.py` signatures and
   `data/technique_priorities.json`.
5. Plan §7 (stages 3, 6, 7) + §13 Phase 2;
   `docs/phases/summaries/SESSION_HANDOFF_2026_08_01_MITRE_PHASE_0_1.md`.

**Gate:** `technique_priorities.json` has been awaiting user review since
Phase 0. At session start, ask the user once whether it is approved (it
gets baked into gap ranking this phase). If approved, proceed; if they
request changes, apply them first; if no answer is available, proceed but
flag prominently in your final report.

## Deliverables

### 1. `app/mitre/agents.py` — `MitreTaggingAgent`

`ReviewAgent` subclass (ConflictDetector pattern — inherits client,
fallback chain, JSON parsing; registered nowhere). Two prompt modes:

- **Tagging mode** (structured rows): input batches of **~25 rules**
  (name + description + detection-logic excerpt capped ~500 chars each);
  output JSON `[{row_ref, technique_ids: [], confidence: 0-1,
  rationale}]`; append `_CONFIDENCE_CALIBRATION` so confidence semantics
  match the product. Returned IDs MUST be validated through
  `attack_data.resolve()` — models emit revoked/hallucinated IDs; remap
  revoked, drop invalid (count in assumptions).
- **Extraction mode** (pdf/docx dumps — this replaces Phase 1's 422):
  `parse_document()` text (OCR fallback + 30-page cap inherited) split
  into ~8–10K-char chunks; output structured use-case entries
  `[{name, description, technique_ids, confidence}]`; every extracted
  row is marked lower-fidelity in assumptions ("rules extracted from
  unstructured PDF — row-level completeness not guaranteed"). The
  xlsx/xls/csv structured path stays byte-identical.

Failure discipline: per-batch `asyncio.wait_for` (60s, one retry at 120s
— house pattern) then degrade that batch to `unmapped` + assumption; a
failed batch must NEVER fail the assessment. Exception: zero
customer-tagged rows AND every tagging batch failed → status `failed`
with a plain-English error (an all-unmapped "assessment" would be
misleading). Batches run sequentially (rate-limit courtesy); rows tagged
by the customer are never re-tagged (customer truth wins). Stamp models
used into `params` for the audit trail.

### 2. Deterministic gap ranking + roadmap bucketing (`app/mitre/ranking.py`, pure)

Uncovered (and partial) applicable techniques ranked by: priority tier
from `technique_priorities.json` → detection feasibility (does the
customer's Log Sources sheet map onto the technique's ATT&CK
`data_sources`? already-onboarded source = cheapest win) → tactic order.
Roadmap buckets by dependency: **short (0–3 mo)** = required log source
already onboarded (name the exact techniques + the log source to build
on); **mid (3–9 mo)** = source obtainable from tooling they already own
(Security Tooling sheet); **long (9–18 mo)** = needs new capability.
Pure functions, plain dicts, golden-case tests. Output feeds both the
summary JSONB and the narrative agent.

### 3. `MitreNarrativeAgent`

One LLM call. Input: the computed JSON only (rollups, ranked gaps with
feasibility, roadmap buckets, N/A summary, industry/region from intake).
Output: `{executive_summary, gap_recommendations: {technique_id: text},
roadmap_prose: {short, mid, long}}`. **Hard requirements in the prompt:**
plain, simple English (short sentences, no unexplained jargon); it may
rephrase but NEVER introduces or alters numbers — report templates print
numbers exclusively from the computed summary. On failure/timeout:
degrade to deterministic template text so the assessment still completes
(ConflictDetector-style degrade).

### 4. Wire into `service.py`

Pipeline order (stages already stubbed): tag-validate → **AI-tag
untagged rows** → applicability → coverage → **rank + bucket** →
**narrative** → persist. Assumptions assembly finalized: AI-tagging
stats (N rows AI-tagged, N dropped <0.4, N invalid IDs), extraction
fidelity, missing workbook sheets, column-map echo, "narrative
AI-generated / template-fallback" flag.

### 5. Prompt documentation

Append a changelog entry to `docs/planning/PROMPT_ENGINEERING_GUIDE.md`
for both prompts: rationale, calibration-rubric reuse, and the
never-introduce-numbers rule for the narrative agent.

### 6. Tests — `tests/test_mitre_agents.py`, `tests/test_mitre_ranking.py`

Mocked LLM exactly as existing agent tests do (no OpenRouter key → test
adapter). Cover: batch success; one-batch-fails → those rows unmapped +
assumption, assessment still completes; garbage JSON advances the model
chain; invalid/revoked AI IDs dropped/remapped + counted;
all-batches-fail + zero customer tags → failed status with message;
narrative degrade to template; extraction mode happy path; ranking
tie-breaks and roadmap bucketing golden cases (source onboarded vs
owned-tooling vs new-capability).

### 7. Live smoke (manual, after tests pass)

Requires `OPENROUTER_API_KEY` in the local env. One real run of an
untagged (or mixed) dump through create→run→results on the dev server;
report: mapped/unmapped counts, spot-check 5 AI mappings by hand, models
actually used, approximate cost. If no key is available locally, say so
explicitly and mark the smoke **pending** — do not fake or skip silently.

## Acceptance (run, don't assume)

- `cd apps/api && python -m pytest tests/test_mitre_agents.py tests/test_mitre_ranking.py -q` green; all mitre files together still green.
- Full suite: **622 + new tests passed, 6 skipped, 0 failures** (Docker
  Desktop + edgp-postgres up; 269 collection errors = Docker down).
- `git status`: changes confined to `app/mitre/*`, new test files,
  PROMPT_ENGINEERING_GUIDE.md, and session docs.
- Smoke evidence in the report, or an explicit "pending: no key".

## Wrap-up

Do NOT commit/push unless the user explicitly says so. Report: files
created/changed, test output, smoke results (or pending), deviations
with reasons, and the priorities-file approval status. Update
`docs/IMPLEMENTATION_PROGRESS.md`'s MITRE entry (Phase 2 done, Phase 3
frontend next per plan §13) and add/extend the session handoff in
`docs/phases/summaries/`.
