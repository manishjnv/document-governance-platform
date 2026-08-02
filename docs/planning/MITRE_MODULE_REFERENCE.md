# MITRE ATT&CK Coverage Assessment — Module Reference

**Status:** COMPLETE (Phases 0–7), launch-ready, live in production at
`https://scopewise.assessiq.in/mitre`. No known quality gaps — everything
remaining is plan-§14 optional feature work, built only on request.
**Written:** 2026-08-02, after Phase 7. This is the end-to-end reference
for what the module is and how every piece works; the original design
rationale lives in `docs/planning/MITRE_ASSESSMENT_PLAN.md` (read that for
*why*, this for *what exists*).

**Baselines:** backend **687 passed / 7 skipped**, certified at the
Phase 7 gate (`b183f75`; the 7th skip = the PDF-render test on dev boxes
without WeasyPrint's native libs — prod image has them, prod render smoke
PASSED 2026-08-02); `npx tsc --noEmit` clean (re-verified 2026-08-02). Prod state: **deployed through
Phase 7** — `/opt/scopewise` at `b183f75`, migrations 029–032 all applied
to `scopewise_prod` (verified via SSH 2026-08-02: `logic` column present,
`keyword_tagged` in the mapping_status CHECK).

---

## 1. What this module is

A customer uploads their SIEM detection-rule dump (xlsx/xls/csv/pdf/docx,
with or without MITRE technique tags) plus an optional multi-sheet
environment workbook (assets/platforms, log sources, security tooling,
crown jewels) and a slim intake (industry, region, disabled-rules policy,
scope exclusions with mandatory reasons). They get a MITRE ATT&CK
coverage assessment: coverage % overall / per matrix (Enterprise, ICS,
Mobile) / per tactic / per technique, an N/A appendix with explicit
reasons, assumptions, a priority-ranked gap list with exact
build-this-detection recommendations, a short/mid/long-term roadmap,
in-app results with a Navigator-style heatmap, executive+detailed PDF, an
8-sheet XLSX gap register, and trend comparison between any two runs.

**Two design invariants govern everything:**

1. **Numbers are deterministic.** Every percentage, count, state, and N/A
   reason is pure Python against a pinned, bundled ATT&CK dataset. LLMs
   contribute ONLY (a) tagging of rules the customer didn't tag and the
   deterministic pre-pass couldn't, and (b) narrative prose that may
   rephrase but never introduces a number.
2. **Full isolation from the review pipeline.** The module is
   `apps/api/app/mitre/` + `mitre_*` tables + `apps/web/app/mitre/`.
   Shared-file touchpoints across the entire build: `main.py` (+2 lines),
   `app/models/__init__.py` (+3 registrations), `AppShell.tsx` (+1 nav
   entry), and — decided in Phase 5 — `enums.AuditResourceType` +
   `audit_log.py` + migration 030 for a proper `mitre_assessment` audit
   value. Nothing in `app/parser.py`, `app/routers/*`, `app/ai/agent.py`'s
   六-persona surface, or `ReviewOrchestrator` changed; the MITRE agents
   are registered NOWHERE in the orchestrator (a 7th registered agent
   would corrupt every review's status math).

---

## 2. File map

### Backend — `apps/api/app/mitre/`

| File | Role |
| --- | --- |
| `attack_data.py` | Loads the pinned `data/attack.json` once at import (`DEFAULT: AttackIndex`). Lookup helpers, `is_valid_technique_id` (`T\d{4}(\.\d{3})?`), `resolve()` → (canonical_id, `ok\|remapped\|deprecated\|unknown\|malformed`) with revoked→`superseded_by` chain-following, `load_technique_priorities()`. `AttackIndex` is injectable into every pure function (tests use synthetic datasets). |
| `applicability.py` | Pure: environment dict → `{na: {tid: {reason, kind, source}}, assumptions, applicable_domains}`. See §6. |
| `coverage.py` | Pure: use cases + applicability → per-technique states + all rollups. Thresholds are module constants overridable per call (org tunables). See §6. |
| `keyword_tag.py` | Pure, Phase 6: deterministic keyword/alias tagging pre-pass that runs BEFORE the LLM. See §7. |
| `ranking.py` | Pure: coverage results + customer log-sources/tooling → priority-ranked gap list + short/mid/long roadmap buckets. See §6. |
| `agents.py` | `MitreTaggingAgent` (tagging + extraction prompt modes) and `MitreNarrativeAgent` — `ReviewAgent` subclasses (ConflictDetector pattern: inherit the OpenRouter client + GLM-5.2→DeepSeek→MiniMax→Qwen chain + unparseable-JSON-advances-chain). Batch drivers with 60s/120s retry and degrade discipline. See §8. |
| `ingest.py` | Structured file readers: xlsx (openpyxl direct cell access — deliberately NOT `parse_document()`, whose ExcelParser flattens columns), xls (xlrd), csv (stdlib). Header/sheet/platform synonym detection (~90 real-world variants), trust-boundary guards. See §5. |
| `service.py` | Pipeline driver (`run_assessment_pipeline`, fire-and-forget task under a process-wide `Semaphore(3)`), `build_mappings` (customer-tag validation), `compare_assessments` (trend diff), org tunables get/set (`mitre_settings`). |
| `router.py` | All endpoints under `/api/v1/mitre` (§9). Org-scoped, soft-delete-aware, upload trust boundary. |
| `report.py` | HTML report builder + lazy-WeasyPrint `generate_pdf` + 8-sheet XLSX writer with formula-injection guard. All three builders are synchronous and are called via `run_in_threadpool` from the router. See §11. |
| `navigator.py` | Pure, Phase 8: builds one ATT&CK Navigator layer (format 4.5) per applicable domain from STORED technique_results — colors mirror the report palette, N/A → `enabled:false` with the reason as the comment, deterministic (no timestamps, byte-stable). |
| `data/attack.json` | Pinned ATT&CK **v19.1** compact dataset (0.7 MB, checked in — the app NEVER fetches from the internet). Enterprise 858 techniques/15 tactics, ICS 118/12, Mobile 190/14 (counts include revoked/deprecated, which carry flags). |
| `data/technique_priorities.json` | Curated 40-technique priority tier list (tiers 1–3) for gap ranking. Sources cited in-file (Red Canary TDR, CISA #StopRansomware, Picus, DBIR, M-Trends). **User-approved 2026-08-01** (stamped in-file). Enterprise-only in v1. |
| `data/keyword_aliases.json` | Curated tool/command → technique alias map (39 aliases, cited sources) for the Phase 6 pre-pass, e.g. `mimikatz`→T1003.001, `-enc`→T1059.001. |

### Everything else

| Path | Role |
| --- | --- |
| `scripts/build_attack_data.py` | Dev-run-only builder: downloads the pinned `attack-stix-data` bundles, compacts to `attack.json`, validates (sanity floors, revoked-has-successor with a one-entry allowlist for MITRE's own orphan mobile T1454, sub-technique parent integrity). Handles v18+ STIX (data sources via detection-strategy→analytic→data-component chain; Mobile's two matrices unioned). |
| `apps/api/migrations/029_mitre_assessment.sql` | The 4 module tables (§4). New tables only, zero ALTERs. |
| `apps/api/migrations/030_audit_mitre_resource_type.sql` | Widens `audit_logs.resource_type` CHECK with `mitre_assessment`. |
| `apps/api/migrations/031_mitre_keyword_tagged_status.sql` | Adds `keyword_tagged` to the `mapping_status` CHECK. |
| `apps/api/migrations/032_mitre_use_case_logic.sql` | Adds `mitre_use_cases.logic` TEXT (Phase 7). |
| `apps/api/app/models/mitre_{assessment,file,use_case}.py` | ORM models (FK columns only, no relationships — so no existing model file changes). Registered in `app/models/__init__.py`. |
| `apps/web/app/mitre/` | Frontend section: `lib.ts` (types + display metadata), `page.tsx` (list), `new/page.tsx` (wizard), `[assessmentId]/page.tsx` (results), `components/` (ExecutiveBand, CoverageHeatmap, TechniqueDrawer, GapsRoadmap, AssumptionsNA, CompareView, StateBadge — all props-only panels). |
| `apps/web/public/templates/scopewise-mitre-{use-cases,environment}.xlsx` | Downloadable templates, header/sheet names verified against `ingest.py`'s synonym lists. |
| `apps/api/tests/test_mitre_*.py` | 7 test files (§13). |
| `docs/planning/MITRE_ASSESSMENT_PLAN.md` | Original design + decisions (locked 2026-08-01). |
| `docs/planning/PROMPT_ENGINEERING_GUIDE.md` | "2026-08-01 — MITRE module prompts" section: rationale for both prompts. MITRE prompts are documented THERE, not mirrored to `prompts/` (its generator covers only the 6 review personas). |
| `docs/phases/summaries/SESSION_HANDOFF_2026_08_01_MITRE_PHASE_0_1.md` | Per-phase build handoffs with deviations and gotchas. |

---

## 3. End-to-end flow

```text
POST /assessments  (multipart: dump + optional env workbook + intake JSON; sync)
  ├─ trust-boundary guards (§10) → ingest → header/sheet detection
  ├─ customer-tag validation (build_mappings: resolve() remap/drop, provenance)
  ├─ pdf/docx: parse_document() text extracted now; rows AI-extracted at run
  ├─ files stored (org/{org}/mitre/{assessment}/{fname}), rows persisted
  └─ 201 + parse preview (row count, detected columns, tagged/untagged/invalid,
     platforms, warnings) — the user's chance to catch a bad column map

POST /assessments/{id}/run  (202; fire-and-forget asyncio task, Semaphore(3))
  1  extraction (pdf/docx only): MitreTaggingAgent "extraction" mode over
     ~9K-char chunks → use-case rows (lower-fidelity, flagged in assumptions)
  2  keyword pre-pass (keyword_tag.py): exact ATT&CK names + curated aliases
     → mapping_status='keyword_tagged' @ confidence 0.9 — skips the LLM
  3  AI tagging (residue only): batches of 25, confidence-scored; <0.4 stays
     unmapped; customer-tagged rows are NEVER re-tagged
  4  applicability (pure): environment → N/A set with reasons
  5  coverage (pure): states + rollups with the org's thresholds
  6  gap ranking (pure): tier → feasibility → tactic; roadmap buckets
  7  narrative (one LLM call over computed JSON; degrades to template text)
  8  persist technique_results + summary; status=completed; audit + cache bust

GET /assessments/{id}   (frontend polls 5s while running; 30-min stale guard)
GET .../report?format=html|pdf     GET .../export.xlsx
GET .../compare/{other_id}         (trend diff)
```

Failure discipline: a failed tagging batch degrades those rows to unmapped
(+assumption); a failed narrative degrades to deterministic template text;
the ONLY LLM condition that fails an assessment is all-batches-failed AND
zero customer/keyword tags (an all-unmapped "result" would be misleading).
Any pipeline exception lands in `status='failed'` + plain-English
`error_message`. A run interrupted by a container restart is flipped to
`failed` ("interrupted — likely a restart; re-run") by the GET stale-run
guard after 30 minutes.

---

## 4. Data model (migrations 029–032)

All UUID v4 PKs, `org_id` FK → organizations CASCADE, tz-aware timestamps
(**module rule: always `datetime.now(timezone.utc)`, never naive
`utcnow()`** — naive writes into timestamptz get read back skewed on a
+05:30 host and broke the stale-run guard), soft deletes via `deleted_at`.
`updated_at` is application-maintained (no DB trigger on these tables).

- **`mitre_assessments`** — `status` CHECK `pending|running|completed|failed`
  with Review-style invariants (`completed ⇒ completed_at`, `failed ⇒
  error_message`); `attack_version` stamped at create; `params` JSONB
  (intake, detected column map, environment dict, environment_lists,
  parse_assumptions, warnings, extraction_text for pdf/docx,
  `thresholds` + `models_used` stamped at run); `technique_results` JSONB
  (write-once/read-whole array, §5-of-plan rationale); `summary` JSONB
  (shape below); `created_by` SET NULL.
- **`mitre_files`** — `kind` CHECK `use_cases|environment`, `file_type`
  CHECK `xlsx|xls|csv|pdf|docx`, `s3_path`, `parse_status`
  (`parsed|extraction_pending`), `row_count`.
- **`mitre_use_cases`** — `row_ref` (e.g. `Rules:14`, `csv:3`,
  `doc:2:1`), `name`, `description`, **`logic`** (migration 032, router
  caps at 2000 chars), `log_source`, `enabled` BOOL NULL (NULL = unknown →
  treated as enabled + assumption), `mappings` JSONB
  `[{technique_id, source: customer|keyword|ai, confidence, rationale}]`,
  `mapping_status` CHECK
  `customer_tagged|keyword_tagged|ai_tagged|unmapped|invalid`.
- **`mitre_settings`** — org-keyed tunables `(org_id, setting_key) → JSONB`
  (customization.py pattern; absent row = code default). Keys/defaults:
  `confidence_covered=0.7`, `confidence_partial_floor=0.4`,
  `partial_credit=0.5`, `count_disabled_as_coverage=false`.

**`summary` JSONB shape** (what reports/frontend/compare consume):

```text
overall / domains.{enterprise|ics|mobile}:   covered, partial, not_covered,
    not_applicable, applicable, strict_pct, weighted_pct
domains.*.tactics[]:  {id, shortname, name, <same rollup fields>}
gaps[]:      {technique_id, name, domain, state, tier, tactics[], feasibility
              (short|mid|long), via, category, hint, rank}
roadmap:     {short[], mid[], long[]}   (same gap dicts, bucketed)
narrative:   {executive_summary, gap_recommendations{tid→text},
              roadmap_prose{short,mid,long}, generated_by: ai|template,
              model_used}
assumptions[]           not_applicable[]: {technique_id, domain, reason}
applicable_domains[]    counts: {use_cases, customer_tagged, ai_tagged,
                                 unmapped, invalid}  (+keyword_tagged rows
                                 count under coverage provenance)
```

**⚠ ORM-constraint sync points (CLAUDE.md rule, learned Phase 5):** any
migration that changes a CHECK mirrored in an ORM model must update BOTH in
lockstep — `mitre_use_cases.mapping_status` (031 ↔ `mitre_use_case.py`) and
`audit_logs.resource_type` (030 ↔ `audit_log.py` + `enums.py`). A
`create_all`-bootstrapped DB with a stale ORM CheckConstraint 500s on every
write (a real bug caught by the Phase 5 adversarial review).

---

## 5. Ingest (trust boundary)

- **Structured dumps** (xlsx/xls/csv): direct cell access. Header row
  found by scanning the first 10 rows for the best synonym-match (title
  rows above headers are fine). Column synonyms per field
  (name/tags/logic/description/enabled/log_source — ~90 variants incl.
  "att&ck id", "mitre_ttp", "kql query"); no detectable name column →
  422 pointing at the template. Technique tags extracted by regex from
  the tags cell; status cells parsed to True/False/None.
- **Environment workbook** (xlsx/xls): sheets located by name synonyms
  (Assets, Log Sources, Security Tooling, Crown Jewels); missing sheets
  tolerated → assumption lines. Asset rows normalize to the ATT&CK
  platform vocabulary (Windows/Linux/macOS/Containers/ESXi/IaaS/SaaS/
  Office Suite/Identity Provider/Network Devices/Android/iOS) via
  longest-first word-boundary rules ("cisco ios" → Network Devices, not
  iOS); OT/ICS and mobile/MDM marker rows set the domain gates; unmatched
  rows become an assumption, never an error.
- **pdf/docx dumps**: text via the existing `parse_document()` (OCR
  fallback + 30-page cap inherited); <200 extractable chars → 422
  (mirrors the review pipeline's unreadable guard); rows AI-extracted at
  run time, capped at 40 chunks (~360KB).
- **Guards**: MIME allowlist with extension fallback, 50MB cap,
  `_sanitize_filename`, row caps 5,000 use-case / 10,000 asset rows (422
  beyond, stated in the error), empty-parse 422, intake exclusions
  require both target AND reason, industry/region capped at 200 chars
  (they flow into the narrative prompt).

---

## 6. Deterministic engines

**Applicability** (`compute_applicability(environment)`) — N/A decisions
with most-specific-reason-wins precedence: customer technique exclusion
(parents cover their sub-techniques) > deprecated ("deprecated in ATT&CK
v19.1") > customer platform exclusion > derived platform mismatch
("targets macOS; macOS not in asset inventory") > customer domain
exclusion > derived domain gate ("ICS matrix: no OT/ICS assets declared in
inventory"). Customer reasons are kept verbatim and attributed
`customer-declared`. Special cases: platforms `PRE` and `None` (all ICS
techniques in v19.1 carry `["None"]`) are environment-independent markers,
never filtered; platform filtering is skipped inside gated/excluded
domains (the domain reason blankets them); `inventory_provided: false`
filters nothing except exclusions and adds the loud
"coverage % is a lower bound" assumption. Revoked techniques are not part
of the register at all.

**Coverage** (`compute_coverage(use_cases, applicability, *, thresholds…)`)
— per applicable technique: `covered` (≥1 enabled mapping with confidence
≥ 0.7), `partial` (only disabled-rule mappings, or only 0.4–0.7
confidence), `not_covered`, `not_applicable`. Mappings < 0.4 don't count.
`count_disabled_as_coverage=true` promotes qualifying disabled mappings.
Parent with no direct qualifying mapping but ≥1 covered sub-technique →
`partial` (both levels stay in the register and the denominator).
Multi-tactic techniques count in every tactic. Headline strict % =
covered/applicable; weighted % credits partial at 0.5. Unknown/malformed
mapping IDs are ignored with an assumption; revoked IDs silently credit
their successor (assumption noted). `enabled: null` → treated enabled +
assumption.

**Ranking** (`rank_gaps`) — gaps = applicable techniques in
`not_covered|partial`, sorted by priority tier (priorities file; unlisted
= tier 4) → feasibility → not_covered-before-partial → tactic order →
id. Feasibility bridges the customer's Log Sources/Tooling sheets to
ATT&CK data-component categories via keyword maps (endpoint / registry /
network / identity / cloud / application / mobile / ot — extended in
Phase 6 from a scan of all 113 data components): **short** = a needed
category is already onboarded (names the exact source), **mid** =
obtainable from tooling they own, **long** = new capability (or no
standard telemetry → "bespoke detection engineering"). Every gap carries a
plain-English `hint`; the narrative's `gap_recommendations` override it in
displays when present.

**Compare** (`service.compare_assessments(current, baseline)`) — pure diff
of two completed runs: `newly_covered` (now covered, wasn't), `regressed`
(was covered → partial/not_covered), `na_changed` (entered/left the
applicable set; a straight N/A→covered appears in both lists — both facts
are true), overall + per-tactic deltas (positive = more coverage),
`attack_version_mismatch` flag (version-drift techniques are skipped).
Tolerates JSONB schema drift via `.get()` throughout.

---

## 7. The tagging ladder (provenance model)

Priority order, each level never overridden by a lower one:

1. **Customer tags** (`source=customer`, confidence 1.0,
   `customer_tagged`) — validated at CREATE time via `resolve()`: revoked
   IDs remap to successors (noted), deprecated/unknown/malformed IDs are
   dropped with notes; a row whose tags ALL fail becomes `invalid` and is
   routed to the ladder below.
2. **Keyword pre-pass** (`source=keyword`, confidence 0.9,
   `keyword_tagged`, Phase 6) — two high-precision signal classes only:
   exact multi-word ATT&CK technique names (word-boundary, ambiguous
   cross-domain names dropped, pre-compromise TA0042/TA0043 excluded — a
   SIEM rule can't observe recon) and the curated alias file matched
   against raw punctuation-significant text (`at.exe` never fires in
   "look at exe files"). Scans name+description+logic capped at 2000
   chars/field. Measured on a 22-rule realistic dump: 14 keyword-tagged /
   8 to AI (63% fewer LLM calls), zero false positives. An AI-down run
   now survives on keyword matches alone.
3. **AI tagging** (`source=ai`, model confidence, `ai_tagged`) — residue
   only; §8.
4. **Unmapped** — counted, excluded from coverage, listed in assumptions.

Phase 7 made the ladder see the actual detection condition: `logic` is
persisted separately from `description` and fed to both taggers (scan cap
2000, LLM excerpt cap 500). Measured effect on a both-columns dump:
keyword-tagged 1/12 → 10/12.

---

## 8. LLM usage (OpenRouter only — never Anthropic/OpenAI/Google directly)

Both agents subclass `ReviewAgent` solely to inherit the client, the
GLM-5.2 → DeepSeek → MiniMax → Qwen fallback chain,
unparseable-JSON-advances-chain, `asyncio.to_thread`, and `_model_used`
stamping. Registered nowhere in `ReviewOrchestrator`.

- **`MitreTaggingAgent`** — mode via the `review(payload, document_type)`
  param: `"tagging"` (JSON batches of 25 rules → `mappings[]`, every
  row_ref echoed once) or `"extraction"` (pdf/docx text chunk →
  `use_cases[]`). Prompts: map what the logic OBSERVES not the attack
  chain, prefer the specific sub-technique, empty list is a correct
  answer, never invent IDs — and every emitted ID is STILL re-validated
  through `resolve()` in code. `_CONFIDENCE_CALIBRATION` appended so
  confidence semantics match the product.
- **`MitreNarrativeAgent`** — ONE call per run over computed JSON only
  (rollups, top-15 gaps + hints, roadmap counts, industry/region). Hard
  rules: plain English; may repeat but NEVER introduces/alters/rounds a
  number (templates print figures from computed data regardless, so a
  hallucinated number can't reach the customer); no invented facts. Never
  receives raw rule logic. Degrades to deterministic template text,
  flagged via `narrative.generated_by` in the summary, assumptions, UI
  badge, and report footer.
- Timeouts: `wait_for` 60s + one retry at 120s per call; batches run
  sequentially. `params.models_used` records which model actually
  answered per stage (audit trail). Cost: ~500 untagged rules ≈ 20 calls,
  well under $0.05 on the chain; the keyword pre-pass cuts this further.
- **Tagging quality: verified on the real prod key 2026-08-02 — 6/6
  correct on the mixed smoke** (see `db98efb`).

---

## 9. API reference (`/api/v1/mitre`, JWT, org-scoped, cross-org → 404)

| Endpoint | Roles | Behavior |
| --- | --- | --- |
| `POST /assessments` | admin, reviewer | Multipart create + synchronous parse → 201 + parse preview. 413 >50MB; 422 bad type/columns/caps/intake/unreadable-pdf. |
| `POST /assessments/{id}/run` | admin, reviewer | 202 fire-and-forget; 409 if running/completed (pending/failed may run). |
| `GET /assessments` | any | List (desc): status, headline strict/weighted %, `domains_brief` per row (per-domain strict %/covered/applicable from stored summary — no N+1). |
| `GET /assessments/{id}` | any | Status + params + summary + technique_results. Applies the 30-min stale-run guard. |
| `GET /assessments/{id}/use-cases` | any | Paginated rows (skip/limit≤500), `mapping_status` filter. |
| `GET /assessments/{id}/report?format=html\|pdf` | any (viewers may read — plan §15 Q1) | 409 unless completed. `{"format","data"}`; PDF as base64-in-JSON (matches reviews.py so the frontend blob pattern is shared). PDF unavailable locally → graceful 500 with message. |
| `GET /assessments/{id}/export.xlsx` | any | 409 unless completed. StreamingResponse, real xlsx content-type + attachment disposition (deliberately NOT base64 — plan §10). |
| `GET /assessments/{id}/navigator` | any | 409 unless completed. ATT&CK Navigator layer export (Phase 8): 1 applicable domain → layer JSON attachment; >1 → zip of per-domain layers. Pure `navigator.py`, layer format 4.5, colors mirror the report palette, N/A → `enabled:false`. |
| `GET /assessments/{id}/compare/{other_id}` | any | `{id}` = current, `{other_id}` = baseline. Both org-owned (404) + completed (409). |
| `GET /settings` / `PATCH /settings` | admin | The 4 tunables; PATCH validates types/ranges + `partial_floor < covered`; audited. |
| `DELETE /assessments/{id}` | admin, reviewer | Soft delete. |

Audit events (`audit_logs`): `mitre.assessment_created` / `_completed` /
`_deleted` with `resource_type='mitre_assessment'` (migration 030);
`mitre.settings_updated` stays `organization` (genuinely org-level).
`invalidate_cache()` after writes. Report/XLSX builders run in
`run_in_threadpool` so large builds can't stall the event loop.

---

## 10. Security posture

- **Upload endpoint is a trust boundary** — all server-side: MIME
  allowlist, 50MB, filename sanitization, row caps, empty/unreadable 422s.
  Client checks are UX only.
- **Org isolation**: every query filters `org_id == current_user.org_id`
  (+ the fire-and-forget pipeline's own queries, hardened Phase 5);
  compare validates BOTH assessments; cross-org is always 404.
- **Stored-XSS**: every customer/LLM string in the HTML report goes
  through `_esc()` (reused from `app/scoring/report.py` — the house
  stored-XSS lesson).
- **XLSX formula injection**: any string cell starting `=`/`+`/`-`/`@`
  gets an apostrophe prefix, across all 8 sheets (rule names,
  descriptions, logic, reasons are attacker-controlled).
- **Prompt exposure**: LLMs receive only rule name/description/logic
  excerpts (500-char caps) and platform booleans/industry/region
  (200-char caps) — never whole files, never the asset inventory,
  narrative never sees raw logic.
- **Resource exhaustion** (2026-08-01/02 adversarial findings, fixed):
  process-wide pipeline `Semaphore(3)`; extraction capped at 40 chunks;
  keyword scan `_FIELD_CAP=2000` per field (an uncapped 32KB logic cell
  cost ~50 min of worker thread on a 5k-row dump); router caps `logic` at
  create.
- **Adversarial sign-offs** (all Sonnet-takeover per the codex:rescue
  outage, logged in the handoff): Phase 2 hardening REVISE→fixed (3
  resource findings); Phase 4 surfaces ACCEPT (+2 non-blocking fixed);
  Phase 5 whole-module REVISE→fixed→re-verified (ORM sync-point bug);
  Phase 6 keyword layer REVISE→fixed→ACCEPT (false-positive classes +
  scan cost, reviewer's FP rules pinned as regression tests); Phase 7
  logic-injection pass ACCEPT zero-blocking.

---

## 11. Reports

- **PDF** (`report?format=pdf`) — one document, executive first: cover +
  methodology footnote ("scores detection presence, not efficacy") →
  executive summary (headline strict % with weighted noted, per-domain
  bars, narrative exec summary, top-5 gaps, roadmap-at-a-glance, rule
  counts) → per-tactic coverage tables per domain → full gap register →
  roadmap detail with prose → assumptions → N/A appendix grouped
  (matrix / platform / deprecated / customer-declared with verbatim
  reasons) → use-case appendix (capped at 500 rows, cap stated; the XLSX
  holds everything) → audit footer (attack_version, GIT_SHA, models_used,
  thresholds, narrative provenance, timestamps). WeasyPrint is imported
  lazily — native libs exist only in the prod image (Dockerfile.prod);
  local dev returns the graceful message.
- **XLSX** (`export.xlsx`) — sheets: Summary, Coverage by Tactic,
  Technique Register (one row per technique + mapped rule names),
  Use-Case Mappings (incl. the guarded Logic column), Gaps &
  Recommendations, Roadmap, Not Applicable, Assumptions. Bold headers,
  frozen top rows, sane widths — a working register, not a brochure.

---

## 12. Frontend (`/mitre`)

House pattern throughout: `'use client'`, AppShell-wrapped, inline axios
with `localStorage access_token` + redirect-to-/login guard, no shared API
client, `NEXT_PUBLIC_API_URL` base. Locked UI principles: full-width
results, data-dense, minimal borders, plain-English shadcn tooltips on
every %, badge, tier and reason; mobile 390px verified 0px horizontal
overflow on every page (real-browser checked).

- **`/mitre`** — list: status badge, strict-% bar (weighted in tooltip),
  per-domain mini-bars (`domains_brief`), trend arrow vs the previous
  completed run, empty-state explainer, New assessment CTA.
- **`/mitre/new`** — single-page wizard: the plan-§2 privacy notice shown
  BEFORE any file; two drag-drop zones (client validation mirrors server
  rules); template download links; intake (industry/region selects,
  disabled-rules toggle default No, scope-exclusions editor requiring
  target+reason); submit → inline parse preview (counts,
  detected-column chips, environment echo, warnings) → Run → redirect.
- **`/mitre/[assessmentId]`** — results: 5s visibility-aware polling
  while running; failed/pending states with re-run; executive band
  (tiles, top-5 gap chips, gated-domain notes); tabs: **Coverage**
  (CSS-grid Navigator-style tactic heatmap, sub-techniques indented,
  click → technique drawer showing state/tactics/N-A reason/mapped rules
  with enabled+source ("Tagged by you" / "Matched by rule" / "AI-mapped")
  +confidence), **Gaps & Roadmap** (ranked table with P-tier/feasibility
  badges + narrative recommendations + AI-written/template provenance
  badge; short/mid/long sections), **Assumptions & N/A** (grouped
  appendix, verbatim customer reasons), **Compare** (baseline selector →
  delta chips with improvement-is-green semantics incl. inverted metrics,
  tactics-that-moved chips, three-column newly/regressed/N-A-changed);
  PDF + XLSX + Navigator download buttons (blob patterns,
  disabled+tooltip until completed; Navigator saves layer JSON or a zip
  depending on the response content-type).

---

## 13. Testing

Backend baseline **687 passed / 7 skipped** (6 pre-existing platform
skips + the PDF test, which auto-skips where WeasyPrint's native libs are
absent; prod render verified live). Frontend: `tsc --noEmit` clean.

| File | Covers |
| --- | --- |
| `test_mitre_applicability.py` | Domain gating, platform filter (+PRE/"None" exemptions), exclusion attribution + most-specific-wins, parent-exclusion inheritance, no-inventory behavior, deprecated reason, ID validation, real-dataset smoke, priorities-file IDs resolve `ok`. |
| `test_mitre_coverage.py` | State thresholds (incl. exact 0.7 boundary), disabled policy param, enabled-None assumption, revoked-mapping remap, invalid-ID handling, sub-technique rollup, multi-tactic counting, golden strict/weighted %. |
| `test_mitre_ingest.py` | Template + messy-header detection, csv, empty/over-cap/no-name-column 422s, environment workbook (sheets, platform normalization, ICS/mobile flags, missing-sheet assumptions). |
| `test_mitre_api.py` | Real-Postgres E2E create→run→poll→results with hand-computed states, org isolation, 409 double-run, settings RBAC+validation, stale-run guard, intake validation. LLM stubbed via an autouse fixture (a local key can never leak into tests). |
| `test_mitre_agents.py` | Tagging batch success/failure-degrade, garbage-JSON chain advance, invalid/revoked AI IDs, confidence floor, extraction mode, narrative AI+template paths, all-batches-fail+zero-tags → failed, keyword-tag FP regression pins. |
| `test_mitre_ranking.py` | Feasibility buckets (onboarded/ownable/new/no-telemetry), tier ordering, state tie-break, covered/N-A exclusion, deterministic-layer-imports-no-AI guard. |
| `test_mitre_report.py` | HTML escapes planted `<script>`, XLSX guard incl. real-workbook readback + Logic column, 409s, StreamingResponse content-type, compare golden + cross-org 404, `domains_brief`. |
| `test_mitre_navigator.py` | Golden single-domain layer (colors/comments/enabled/versions/legend), multi-domain stable order, gated-domain exclusion; endpoint json vs zip, viewer-readable, cross-org 404 + pending 409. |

Reminder: migrations 029/031/032 (and 030) must be applied to `edgp_test`
before running the suite.

**Shared-test-DB gotcha (learned 2026-08-02):** `edgp_test` is one shared
database and the `db_session` fixture starts every test with
`TRUNCATE organizations CASCADE`. **Two sessions/agents running pytest
concurrently corrupt each other's runs** — the symptom is a handful of
spurious failures/ERRORs in *unrelated* files (missing rows, FK
violations) while the same files pass in isolation, and pg_stat_activity
shows multiple queued TRUNCATEs. Before trusting a red suite, check
whether another session is testing; before starting a long run, make sure
you're alone on `edgp_test`.

---

## 14. Operations runbook

- **Migrations** (no runner exists — RCA #3/#11/#12/#13): apply each
  `.sql` to `edgp_dev`, `edgp_test`, and on deploy `scopewise_prod` via
  `docker exec -i … psql`. Module migrations: 029 (tables), 030 (audit
  CHECK), 031 (mapping_status CHECK), 032 (logic column). **5th sync
  point:** CHECK changes mirrored in ORM models must update both in
  lockstep (see §4 warning).
- **Deploy**: standard VPS loop (git push → `docker compose -f
  docker-compose.vps.yml build` → `GIT_SHA=$(git rev-parse --short HEAD)
  … up -d`) → apply any new migration to `scopewise_prod` → smoke
  `/mitre` (200), `/api/v1/mitre/assessments` (401 unauth), health.
  GIT_SHA lands in the report audit footer. No outstanding deploy steps
  as of 2026-08-02: prod is at `b183f75` with migrations 029–032 applied
  (verified).
- **ATT&CK version upgrade**: bump `ATTACK_VERSION` in
  `scripts/build_attack_data.py`, run it (validates; new
  revoked-without-successor orphans fail loudly against the allowlist),
  review the printed per-domain counts, commit the regenerated
  `attack.json`, re-run the mitre suite (technique renames/restructures
  surface in the priorities-file test — v19 moved T1562.001→T1685,
  T1070.001→T1685.005), and review `technique_priorities.json` +
  `keyword_aliases.json` for renamed techniques. Old assessments keep
  their stamped `attack_version`; compare flags version mismatches.
- **OpenRouter down / key over cap**: assessments still complete —
  keyword-tagged + customer-tagged coverage, unmapped residue with
  assumptions, template narrative. No operator action needed beyond the
  key limit itself.
- **Local dev quirks**: WeasyPrint native libs absent → PDF endpoint
  returns the graceful message (HTML format works); running the web UI
  against a local API needs `CORS_ORIGINS` to include the dev port; the
  repo-root `.env` breaks `Settings()` if you run API scripts from the
  repo root — run them from `apps/api`.

---

## 15. Build history

| Phase | Commits | Date | Delivered |
| --- | --- | --- | --- |
| Plan | `07737c7` | 08-01 | Design doc + intake decisions locked |
| 0 | `126faf5` | 08-01 | Pinned ATT&CK v19.1 dataset + build script; pure applicability/coverage; priorities file; 23 tests |
| 1 | `645fe3e` | 08-01 | Migration 029, models, ingest, router/service, tagged-only E2E; 16 tests |
| 2 | `2ad1c39` | 08-01 | Tagging+narrative agents, gap ranking, pdf/docx extraction; 14 tests |
| 2-hardening | `14b1b7b` | 08-01 | Adversarial REVISE→fixed: Semaphore(3), extraction chunk cap, intake caps; **first prod deploy** |
| 3 | `ebde017` | 08-01 | `/mitre` frontend (list/wizard/results+heatmap+drawer), nav, templates; browser-verified incl. mobile |
| 4 | `8a608c0` | 08-02 | PDF/XLSX reports, compare/trend, `domains_brief`; ACCEPT sign-off; prod deploy |
| 5 | `f813f4c` | 08-02 | Launch closeout: prod PDF smoke PASS, migration 030 (audit enum), whole-module adversarial REVISE→fixed (ORM sync-point), §15 questions resolved |
| smoke | `db98efb` | 08-02 | **AI-tagging quality: 6/6 on the real prod key** — last pending item closed |
| 6 | `198b4c7`,`fb0b97a`,`93b825d`,`68ade56` | 08-02 | Keyword pre-pass (+migration 031), synonym widening, mobile/OT feasibility categories; REVISE→ACCEPT; prod deploy |
| 7 | `999ee5d`,`b183f75` | 08-02 | Persist `logic` (migration 032), feed both taggers; keyword hits 1/12→10/12; ACCEPT; prod deploy verified 08-02 |
| 8 | *(pending commit)* | 08-02 | Navigator layer export — implemented + tested (6 tests); fill in the hash when its session commits |

## 16. Optional feature work (plan §14 — not launch blockers)

Originally deferred by design; now queued as optional **Phases 8–13**
(one feature per session, kickoff prompt committed as `cf6e9e4`).
**Phase 8 (ATT&CK Navigator layer export) is implemented** (2026-08-02;
the `navigator.py` / API-table / frontend / test entries above describe
it) and **Phase 9 (interactive column-mapping wizard) is in progress** —
both land via their own build sessions; add their §15 rows with commit
hashes when they do. Still open, build only on request: interactive column-mapping wizard, per-mapping
AI-override UI, threat-informed actor/industry weighting,
scheduled/continuous re-assessment + SIEM API pulls, per-rule detection
*quality* scoring (v1 scores presence — stated in the methodology
footnote and assumptions), ICS/Mobile entries in the priorities file,
per-org priority-tier overrides (the `mitre_settings` pattern already
supports it). When one of these lands, extend §15's history table and
the relevant sections here.
