# MITRE ATT&CK Coverage Assessment — Module Reference

**Status:** COMPLETE (Phases 0–7 + optional Phases 8–12 + Phase 13
SIEM integration 13a–13d), launch-ready, live in production at
`https://scopewise.assessiq.in/mitre`. Phase 13's own contract/deep
reference is `docs/planning/MITRE_SIEM_INTEGRATION_PLAN.md` — read BOTH
docs before touching `app/mitre/connectors/*` or `app/mitre/tasks.py`.
**Written:** 2026-08-02, after Phase 7. This is the end-to-end reference
for what the module is and how every piece works; the original design
rationale lives in `docs/planning/MITRE_ASSESSMENT_PLAN.md` (read that for
*why*, this for *what exists*).

**Baselines:** backend **687 passed / 7 skipped**, certified at the
Phase 7 gate (`b183f75`; the 7th skip = the PDF-render test on dev boxes
without WeasyPrint's native libs — prod image has them, prod render smoke
PASSED 2026-08-02); `npx tsc --noEmit` clean (re-verified 2026-08-02). Backend count after optional Phases 8–12:
**723 passed / 7 skipped** (certified solo on shared `edgp_test` — see
the `edgp-test-single-runner-rule` memory for why runs from two sessions
at once deadlock). Prod state: **deployed through Phase 12** —
`/opt/scopewise` at `436612a`; migrations 029–033 all applied to
`scopewise_prod` (Phases 11–12 add none).

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
| `quality.py` | Pure, Phase 12: deterministic 0-100 "detection strength" per covered/partial technique (provenance + enabled + logic-present + telemetry-match signals) + rationale + rollup. An EFFICACY signal, deliberately separate from coverage %. See §6. |
| `connectors/` | Phase 13: SIEM pull package — `egress.py` (resolve-then-pin SSRF guard, the ONLY outbound-HTTP door; https/443, hardcoded host allowlists, redirects rejected, caps), `sentinel.py` (Entra client-credentials → alertRules → canonical template CSV; fixed Microsoft hosts, regex-validated IDs), `vault.py` (AES-256-GCM, AAD-bound to connection_id, `SIEM_CRED_KEY` env master key, key_version), `base.py` (dispatch + error taxonomy). Contract: `MITRE_SIEM_INTEGRATION_PLAN.md`. |
| `tasks.py` | Phase 13c/13d: Celery beat sweep (15 min) + per-connection pull-and-run task (fresh-engine-per-call — the app engine binds to the first loop), stale-running self-heal, `connection_health` (streak math shared with the notifier), admin email after exactly 2 consecutive scheduled failures (one notice per streak, reset on success). Runs in the `scopewise-worker` container. |
| `agents.py` | `MitreTaggingAgent` (tagging + extraction prompt modes) and `MitreNarrativeAgent` — `ReviewAgent` subclasses (ConflictDetector pattern: inherit the OpenRouter client + GLM-5.2→DeepSeek→MiniMax→Qwen chain + unparseable-JSON-advances-chain). Batch drivers with 60s/120s retry and degrade discipline. See §8. |
| `ingest.py` | Structured file readers: xlsx (openpyxl direct cell access — deliberately NOT `parse_document()`, whose ExcelParser flattens columns), xls (xlrd), csv (stdlib). Header/sheet/platform synonym detection (~90 real-world variants), trust-boundary guards. See §5. |
| `service.py` | Pipeline driver (`run_assessment_pipeline`, fire-and-forget task under a process-wide `Semaphore(3)`), `build_mappings` (customer-tag validation), `compare_assessments` (trend diff), org tunables get/set (`mitre_settings`). |
| `router.py` | All endpoints under `/api/v1/mitre` (§9). Org-scoped, soft-delete-aware, upload trust boundary. |
| `report.py` | HTML report builder (Jinja2, `templates/`) + lazy-WeasyPrint `generate_pdf`. All builders are synchronous and are called via `run_in_threadpool` from the router. Phase 14h split the former monolithic file into this + `report_common.py` + `report_xlsx.py`; `build_xlsx_export` is re-exported here for backward compatibility. See §11. |
| `report_common.py` | Phase 14h: shared constants/helpers (`_esc`, `_guard` formula-injection guard, state/tier labels, `resolve_branding()` merging per-org overrides over `DEFAULT_BRANDING` with defense-in-depth hex re-validation). |
| `report_xlsx.py` | Phase 14h: the XLSX gap-register builder (`build_xlsx_export`, split out of `report.py`), openpyxl-native only (no xlsxwriter). |
| `templates/` | Phase 14h: Jinja2 templates for the HTML/PDF report — `base.html` (shared shell, running page-header brand element, watermark), `cover.html`, `executive.html`, `detail.html`, `appendix.html`, `style.css` (Jinja-templated so `{{ brand_color }}` interpolates directly into the `<style>` block). |
| `navigator.py` | Pure, Phase 8: builds one ATT&CK Navigator layer (format 4.5) per applicable domain from STORED technique_results — colors mirror the report palette, N/A → `enabled:false` with the reason as the comment, deterministic (no timestamps, byte-stable). |
| `data/attack.json` | Pinned ATT&CK **v19.1** compact dataset (0.7 MB, checked in — the app NEVER fetches from the internet). Enterprise 858 techniques/15 tactics, ICS 118/12, Mobile 190/14 (counts include revoked/deprecated, which carry flags). |
| `data/technique_priorities.json` | Curated 40-technique priority tier list (tiers 1–3) for gap ranking. Sources cited in-file (Red Canary TDR, CISA #StopRansomware, Picus, DBIR, M-Trends). **User-approved 2026-08-01** (stamped in-file). Enterprise-only in v1. |
| `data/keyword_aliases.json` | Curated tool/command → technique alias map (39 aliases, cited sources) for the Phase 6 pre-pass, e.g. `mimikatz`→T1003.001, `-enc`→T1059.001. |
| `data/threat_profiles.json` | Phase 11: curated industry (10 profiles + banking/insurance aliases, keyed to the wizard's INDUSTRIES lowercased) and actor (10 ATT&CK groups incl. G-codes) → technique lists, sources cited in-file (DBIR/CISA/M-Trends/Dragos/HC3/FS-ISAC + ATT&CK Groups). 143 IDs, all resolve `ok` (test-enforced). Feeds threat-informed gap weighting — ordering only, never coverage %. |
| `plain_language.py` | Pure, Phase 14a: loads the curated files below, `describe_technique()` (curated entry or attack.json first-sentence fallback), `detection_sketch()` ("Using `<via>`, alert on: `<hint>`"), and `derive_why()` — the deterministic one-sentence why-phrase per state (not-covered count / disabled rule / low-confidence AI / sub-technique rollup / covered proof + strength / N-A verbatim). Golden-tested; reused by the drawer explain endpoint (and the Phase 14c XLSX "Why" column when built). Phase 14i adds `telemetry_requirements()` (per-technique, per-ATT&CK-data-source-component `{component, fields, where, gotcha}`, curated entry or bare-component-name fallback) and `telemetry_lines()` (deterministic one-line-per-component rendering shared by the XLSX and PDF report builders). |
| `data/technique_plain_language.json` | Phase 14a: hand-curated definition / attacker_use / detection_hint for the 57 techniques in technique_priorities ∪ threat_profiles (the realistic top-gap set). Never runtime-LLM; ID validity + rule coverage test-enforced. |
| `data/tactic_lines.json` | Phase 14a: one plain-English story line per tactic shortname (21 — all three domains, incl. v19's enterprise stealth/defense-impairment split). Completeness vs attack.json test-enforced. |
| `data/telemetry_fields.json` | Phase 14i: hand-curated "what does my query need?" guidance for the top 35 (of 113) ATT&CK data-source components by technique-reference frequency (83%/88% coverage at top 25/35) — `fields` (plain-English query parameters), `where` (vendor-neutral usual event sources), `gotcha` (the single most common reason an already-onboarded source still can't support the detection, never phrased as "your source is missing X" — this product never ingests raw logs). Uncurated (long-tail) components fall back to the bare name with no invented guidance. Never runtime-LLM; component-key validity against attack.json + all-35-present test-enforced. |

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
  `customer_tagged|keyword_tagged|ai_tagged|manual|unmapped|invalid`
  (`manual` added by migration 033, Phase 10).
- **`mitre_settings`** — org-keyed tunables `(org_id, setting_key) → JSONB`
  (customization.py pattern; absent row = code default). Keys/defaults:
  `confidence_covered=0.7`, `confidence_partial_floor=0.4`,
  `partial_credit=0.5`, `count_disabled_as_coverage=false`,
  `threat_weighting_enabled=true` (Phase 11 — gap-ordering only),
  `quality_ai_enabled=false` (Phase 12 — optional AI strength re-rating;
  quality never depends on it).

**`summary` JSONB shape** (what reports/frontend/compare consume):

```text
overall / domains.{enterprise|ics|mobile}:   covered, partial, not_covered,
    not_applicable, applicable, strict_pct, weighted_pct
domains.*.tactics[]:  {id, shortname, name, <same rollup fields>}
gaps[]:      {technique_id, name, domain, state, tier, tactics[], feasibility
              (short|mid|long), via, category, hint,
              threat_relevance (labels[]|null, Phase 11), rank}
roadmap:     {short[], mid[], long[]}   (same gap dicts, bucketed)
narrative:   {executive_summary, gap_recommendations{tid→text},
              roadmap_prose{short,mid,long}, generated_by: ai|template,
              model_used}
quality:     {scored, avg_strength, strong, moderate, weak}  (Phase 12
             rollup; technique_results entries additionally carry
             strength 0-100 + strength_rationale on covered/partial
             techniques with direct rules)
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
displays when present. **Phase 11 threat weighting:**
`build_threat_profile(industry, actors)` looks up the curated
`threat_profiles.json` (exact technique IDs; unknown industry/actor =
no-op) and matching gaps carry `threat_relevance` labels and sort above
EQUAL-TIER peers (a second sort key right after tier — never a tier jump,
never a coverage/state change). Org-toggleable via
`threat_weighting_enabled` (default on); when off, ordering reverts but
the annotation stays (provenance).

**Quality** (`quality.compute_quality(results, use_cases, …)`, Phase 12)
— annotates covered/partial techniques that have direct qualifying rules
with a deterministic 0-100 detection strength: provenance base
(customer/manual 30, keyword 25, AI≥covered-conf 20, AI below 10) +
enabled bonus (30/15 unknown/0 disabled — a disabled rule can never
reach "strong") + logic present (10) + telemetry match (30 — the rule's
log_source/logic run through ranking's category bridge against the
technique's data sources), best rule + redundancy bonus (5/extra rule,
cap 10). Buckets: strong ≥75 / moderate ≥45 / weak. Rationale built from
fixed fragments only. Returns the "inconclusive" items (logic present,
expected telemetry known, no match) for the OPTIONAL AI pass (§8) —
gated by `quality_ai_enabled` (off), capped, degrade-to-heuristic.
Never touches states, coverage %, or ranking; recompute (Phase 10)
re-annotates heuristic-only.

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

0. **Manual reviewer override** (`source=manual`, confidence 1.0, `manual`,
   Phase 10) — an admin/reviewer edits one rule's technique list post-run
   via `PATCH .../use-cases/{id}/mappings`; replaces the row's mappings
   wholesale (empty list = "maps to nothing") and triggers an inline
   deterministic recompute of coverage/gaps/roadmap. Outranks everything.
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
- **`MitreQualityAgent`** (Phase 12, OPTIONAL — `quality_ai_enabled` off
  by default) — subclasses `MitreTaggingAgent` for the plumbing, own
  prompt (rubric bands matching the heuristic buckets; "rate ONLY from
  the given logic"). Sees only heuristic-inconclusive items, max 40/run,
  500-char excerpts; outputs clamped 0-100 in code, unknown IDs dropped,
  rationale capped 300, merged scores prefixed "AI-assessed:"; any
  failure keeps the deterministic heuristic score.
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
| `GET /assessments` | any | List (desc): status, headline strict/weighted %, `domains_brief` per row (per-domain strict %/covered/applicable from stored summary — no N+1). Phase 14f: `archived` + `project_name` per row; `?include_archived=true` includes soft-archived rows (default hides them). |
| `PATCH /assessments/{id}` | admin, reviewer | Phase 14f housekeeping: `{"name"?, "archived"?}` — rename (1-255 chars) and/or soft-archive (params JSONB flag; archived rows leave the default list but stay selectable in Compare). Audited `mitre.assessment_updated`. Deliberately no delete here. |
| `GET /assessments/{id}` | any | Status + params + summary + technique_results. Applies the 30-min stale-run guard. |
| `GET /assessments/{id}/use-cases` | any | Paginated rows (skip/limit≤500), `mapping_status` filter. |
| `GET /assessments/{id}/report?format=html\|pdf&scope=…` | any (viewers may read — plan §15 Q1) | 409 unless completed. `{"format","data"}`; PDF as base64-in-JSON (matches reviews.py so the frontend blob pattern is shared). PDF unavailable locally → graceful 500 with message. `scope`: `full` (default) \| `executive` (1–3 page leadership cut: cover + executive section, TOC/xrefs stripped) \| `coverage` / `gaps` / `assumptions` (title + just that tab's section). Passes the previous completed run for the trend block and the files list for the cover. |
| `GET /assessments/{id}/export.xlsx?scope=…` | any | 409 unless completed. StreamingResponse, real xlsx content-type + attachment disposition (deliberately NOT base64 — plan §10). `scope`: `full` \| `coverage` \| `gaps` \| `assumptions` — workbook built once, non-tab sheets pruned; filename suffixed with the scope. |
| `GET /assessments/{id}/navigator` | any | 409 unless completed. ATT&CK Navigator layer export (Phase 8): 1 applicable domain → layer JSON attachment; >1 → zip of per-domain layers. Pure `navigator.py`, layer format 4.5, colors mirror the report palette, N/A → `enabled:false`. |
| `POST /assessments/{id}/remap` | admin/reviewer | 409 unless `pending` (atomic status-conditional guard in the row-replacement transaction — run/remap race closed). Phase 9 wizard: `{"columns": {field: 0-based index}}` re-parses the stored dump with an explicit map (`validate_column_override` 422s bad fields/indexes), replaces rows, updates `params.columns`, audits `mitre.assessment_remapped`, returns a fresh parse preview (`headers` + `sample_rows` now on create too). 422 for pdf/docx extraction dumps. |
| `POST /assessments/from-siem` | admin, reviewer | Phase 13a token-at-trigger Sentinel pull: `{platform, config, secret, name?, intake?}` — secret used once, NEVER persisted/logged/echoed; connector emits a template CSV through the exact upload create path; provenance in `params.siem`. Config 422; upstream failures 502 with actionable, secret-free messages. |
| `GET/POST/PATCH/DELETE /connections`, `POST /connections/{id}/test` | admin | Phase 13b/13d saved connections: secret AES-256-GCM at rest (write-only — no response ever carries it), config revalidated on change, schedule trio validated as a unit (13c), GET includes per-connection `health` (last pull/error + scheduled-failure streak). `/test` = dry-run rule count. Vault unconfigured → 503. |
| `POST /assessments/from-connection/{id}` | admin, reviewer | Phase 13b: same pipeline as from-siem, secret decrypted in-process from the vault for the pull only; provenance gains connection_id/name. |
| `PATCH /assessments/{id}/use-cases/{use_case_id}/mappings` | admin, reviewer | 409 unless `completed`. Phase 10 override: body `{"technique_ids": [...]}` = the FULL new list for that rule (empty = maps to nothing, max 20). Every ID validated via `resolve()` (revoked→successor with a note; deprecated/unknown/malformed → 422). Row becomes `mapping_status='manual'`, mappings `source='manual'` @ 1.0; coverage/gaps/roadmap recomputed inline (pure code, `service.recompute_results`, narrative kept + assumption note appended, counts gain a `manual` key). `SELECT … FOR UPDATE` on the assessment serializes concurrent edits; audits `mitre.mappings_edited`. |
| `GET /assessments/{id}/techniques/{tid}/explain` | any | Phase 14a: plain-language four-block explanation (what / where / why / what-good-looks-like) for one technique. 409 unless completed; 404 if the technique isn't in the stored register. Fully deterministic — curated files + stored result data + `ranking.technique_feasibility` for non-gap techniques; no LLM. Phase 14g adds `where.expected_telemetry` (ATT&CK data sources) and `where.in_scope_because` (environment entries whose parsed interpretation put the domain/platforms in play). Phase 14i adds `good.telemetry` — `plain_language.telemetry_requirements()` output (per-data-source-component fields/where/gotcha) rendered in the drawer's "What would good look like?" block. |
| `GET /assessments/{id}/compare/{other_id}` | any | `{id}` = current, `{other_id}` = baseline. Both org-owned (404) + completed (409). |
| `GET /threat-catalog` | any | Phase 11: curated actor list (name + ATT&CK G-code + note) and profiled-industry labels from `threat_profiles.json` — feeds the wizard's actor chips. Static, org-agnostic. |
| `GET /settings` / `PATCH /settings` | admin | The 5 tunables; PATCH validates types/ranges + `partial_floor < covered`; audited. Intake note: `threat_actors` (≤10) is validated against the catalog at create — unknown names 422. |
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

**Phase 14h (branding + polish):** three org-scoped `mitre_settings`
overrides — `report_display_name` (default "ScopeWise"), `report_accent_color`
(hex, validated at write time in `service.py` and again at render time in
`resolve_branding()` since it's interpolated into a CSS `<style>` block),
`report_watermark_text` (optional, empty by default). Both `report.py` and
`report_xlsx.py` builders accept a trailing `branding` dict; the two
router endpoints fetch org settings and pass it through. No new endpoints,
no admin UI, no DB migration (`mitre_settings` is already a generic
org-scoped KV table).

- **PDF** (`report?format=pdf`, rebuilt Phase 14e) — cover (project
  metadata, upload summary, headline + plain subtitle, methodology, TOC
  with real page numbers via `target-counter`) → executive section (≤2
  pages by construction: traffic-light domain scorecard, top-5 fixes in
  plain words with threat tie-ins + "details p. N" cross-refs,
  roadmap-at-a-glance + effort-to-impact projection, trend vs the
  previous completed run — fetched by the report endpoint) → detailed
  section (stacked per-tactic bars with tactic one-liners, parent-level
  heatmap grids, gap register grouped by feasibility where each entry
  carries the 14a why-phrase + detection sketch + via-log-source + the
  AI recommendation with its badge, Phase 14i: a "Log fields needed" line
  per gap NAMING its telemetry components, with the field guidance printed
  ONCE in a "Log fields reference" table right after the register — per-gap
  repetition added ~1.23 MB / ~680 pages on a real 842-gap assessment
  because 487 techniques share "Process Creation"; the table sits inside
  the register section so the per-tab `gaps` scope keeps it and the
  `executive` cut still drops it)
  → appendices (register with names,
  N/A grouped, assumptions, 14g how-we-read-your-files, rule mappings in
  numeric order with plain-words statuses, 500-row cap stated) → audit
  footer (attack_version, GIT_SHA, models_used, thresholds, narrative +
  SIEM provenance). Running header + page N of M. WeasyPrint imported
  lazily — native libs exist only in the prod image. Phase 14h adds: a
  logo in the cover + a repeating page header (WeasyPrint CSS GCPM
  `position: running()`/`content: element()`), an optional diagonal
  watermark (`position: fixed`), and document metadata (`<meta>` tags in
  `base.html`'s `<head>` — WeasyPrint maps these to the PDF's
  `/Author`/`/Subject`/`/Keywords`, `<title>` → `/Title`).
- **XLSX** (`export.xlsx`, polished Phase 14c, further polished Phase 14h)
  — sheets: **Read Me** (guide, colored legend cells, key numbers, "is
  this % bad?" context, Phase 14h: `protection.sheet = True` —
  accidental-edit guard, no password), Summary (+What-it-means column,
  metadata rows), Coverage by Tactic (Phase 14h: `DataBarRule`
  conditional formatting on the Coverage %/Weighted % columns + a native
  `BarChart` of coverage % per tactic), Technique Register (+Name,
  plain-words state, **Why** via `plain_language.derive_why`, tactic
  names), Use-Case Mappings (numeric row sort, plain-words statuses,
  guarded Logic column), Gaps & Recommendations (feasibility-grouped,
  colored section headers; Phase 14h: Priority column is now a real
  integer with a `"P"0` number format — displays as P1/P2/P3 but is
  sortable/rankable — plus a genuine 3-color `ColorScaleRule` replacing
  the old static per-cell fill; Phase 14i: a "Log fields needed" column
  via `plain_language.telemetry_lines`, blank for techniques with no
  curated data-source component), Roadmap, Not Applicable, Assumptions,
  and (when present) the 14g **How We Read Your Files** evidence sheet.
  Frozen headers, auto-filter, wrapped text, state/tier/feasibility fills.
  Phase 14h also sets workbook core properties before save: `title`
  (includes the assessment name), `creator` ("ScopeWise"), and
  `description` (org display name — openpyxl has no wired-up support for
  the docProps/app.xml "Company" extended property, confirmed by source
  inspection, so `description` carries that role instead). openpyxl-native
  only throughout — xlsxwriter is intentionally not used.

---

## 12. Frontend (`/mitre`)

House pattern throughout: `'use client'`, AppShell-wrapped, inline axios
with `localStorage access_token` + redirect-to-/login guard, no shared API
client, `NEXT_PUBLIC_API_URL` base. Locked UI principles: full-width
results, data-dense, minimal borders, plain-English shadcn tooltips on
every %, badge, tier and reason; mobile 390px verified 0px horizontal
overflow on every page (real-browser checked).

- **`/mitre`** — list, redesigned post-14 as a responsive card grid
  (1/2/3 columns by screen; the old six-column table read as cryptic and
  empty): each card carries the name + project/Sentinel/archived chips,
  a big coverage % with the plain-words "your rules detect X of Y
  applicable techniques" line, delta vs the previous completed run,
  per-matrix bars with full labels (Enterprise / ICS-OT / Mobile), a
  status + ATT&CK-version + date footer, plain-English helper lines for
  pending/running/failed, and inline rename/archive actions. Whole card
  is clickable and keyboard-navigable. Toolbar: client-side search
  (name/project), status filter, show-archived toggle, coverage
  sparkline over completed runs.
- **Phase 14b drill-down layer** — `DrillDownPanel` (technique list with
  state colors, plain phrases, partial why-brief) + `RuleListPanel`
  (rules with plain-words mapping status and, 14g, the per-mapping
  journey: source/confidence/rationale verbatim) sit behind every
  number: tiles, heatmap headers, N/A group counts, rules-by-status
  chips, the 14d `UploadSummaryCard` counts, and the wizard's
  parse-preview tiles. Rows click through to the technique drawer.
- **Post-14 polish layer** (2026-08-02 evening): all three side panels
  are mouse-resizable via a left-edge drag handle (`useSheetResize` —
  shared remembered width, keyboard arrows, phones stay full-width);
  heatmap cells show "ID Name" with one delegated hover-intent tooltip
  (solid bg, glides between cells), collapsible matrix sections, and the
  legend doubles as an in-place state filter; the gaps table runs dense
  dot+text badges ("P1 · Critical", "70 · Moderate", "Build now · via
  Sysmon"); Assumptions & N/A is a two-column card layout with
  reason-aggregated technique chips; the tab bar hosts the on-page
  **"is it covered?" search** (matches technique ID/name, tactic,
  ATT&CK platform — enriched per-technique into GET — and rule
  names/log sources; results open the drill-down panel grouped by
  state) plus per-tab PDF/Excel download icons; the header offers
  **Exec PDF** (scope=executive) alongside Full PDF, and the Navigator
  tooltip states plainly it is a technical layer file, not a document.
- **`/mitre/new`** — single-page wizard: the plan-§2 privacy notice shown
  BEFORE any file; two drag-drop zones (client validation mirrors server
  rules); template download links; intake (industry/region selects,
  Phase 11 threat-actor chips fed by `GET /threat-catalog`,
  disabled-rules toggle default No, scope-exclusions editor requiring
  target+reason); submit → inline parse preview (counts,
  detected-column chips, environment echo, warnings) → Run → redirect.
- **`/mitre/[assessmentId]`** — results: 5s visibility-aware polling
  while running; failed/pending states with re-run; executive band
  (tiles, top-5 gap chips, gated-domain notes); tabs: **Coverage**
  (CSS-grid Navigator-style tactic heatmap, sub-techniques indented,
  click → technique drawer showing state/tactics/N-A reason/mapped rules
  with enabled+source ("Tagged by you" / "Matched by rule" / "AI-mapped")
  +confidence; Phase 12 adds a detection-strength chip + rationale line;
  Phase 14a adds the four plain-language blocks — what is this / where is
  the gap (tactic story line, via-log-source, platforms) / why is it a gap
  (deterministic why-phrase) / what would good look like (detection sketch
  + closest-covered-rule starting point) — fetched per-open from the
  explain endpoint, graceful fallback to the pre-14a content if it fails), **Gaps & Roadmap** (ranked table with P-tier/feasibility
  badges, a Phase 11 violet "Threat match" chip on profile-relevant rows,
  a Phase 12 "Strength" column (partial gaps' scores, tooltip states it
  is separate from coverage %), narrative recommendations, and the
  AI-written/template provenance
  badge; short/mid/long sections), **Assumptions & N/A** (grouped
  appendix, verbatim customer reasons), **Compare** (baseline selector →
  delta chips with improvement-is-green semantics incl. inverted metrics,
  tactics-that-moved chips, three-column newly/regressed/N-A-changed);
  PDF + XLSX + Navigator download buttons (blob patterns,
  disabled+tooltip until completed; Navigator saves layer JSON or a zip
  depending on the response content-type).

---

## 13. Testing

Backend baseline **809 passed / 7 skipped** (Phase 14i, +6 new telemetry-
fields tests over the post-14h 803/7 baseline — 6 pre-existing platform
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
| `test_mitre_report.py` | HTML escapes planted `<script>`, XLSX guard incl. real-workbook readback + Logic column, 409s, StreamingResponse content-type, compare golden + cross-org 404, `domains_brief`; Phase 14h: `test_xlsx_phase14h_polish` (data-bar/color-scale CF rule counts, native chart presence, numeric Priority + number_format, Read Me sheet protection, workbook core properties); Phase 14i: `test_xlsx_phase14c_structure` extended for the "Log fields needed" column header + curated cell content. |
| `test_mitre_navigator.py` | Golden single-domain layer (colors/comments/enabled/versions/legend), multi-domain stable order, gated-domain exclusion; endpoint json vs zip, viewer-readable, cross-org 404 + pending 409. |
| `test_mitre_mapping_edit.py` | Phase 10 PATCH: manual provenance + inline recompute (states flip, counts.manual, assumption note, audit row), empty-list unmap, invalid/malformed/over-cap 422s, non-completed 409, cross-org 404 (both IDs) + viewer 403. |
| `test_mitre_threat_profile.py` | Phase 11: every curated ID resolves `ok` + alias integrity, real-file lookup (Banking alias, unknown = no-op), within-tier lift golden, no-tier-jump golden, toggle-off keeps order but keeps annotation, intake threat_actors 422s (unknown/non-list/over-10). |
| `test_mitre_quality.py` | Phase 12: heuristic goldens (full-signal 100, disabled capped 70, telemetry match +30, low-conf AI weak, redundancy cap, no-telemetry note, only direct-rule covered/partial scored), inconclusive selection, rollup, AI pass clamped/filtered/merged + garbage-degrades-to-heuristic. |
| `test_mitre_siem.py` | 13a: egress deny-set table (+mixed-answer rebinding), pin assertion, allowlist-before-resolve, redirect/size caps, hostile Retry-After, nextLink suffix-spoof, Sentinel config regexes (+dot-edge resource groups), normalization goldens round-tripped through real ingest, endpoint E2E + secret-absence scan + RBAC. No test touches the network. |
| `test_mitre_connections.py` | 13b: crypto round-trip/AAD-transplant/key-version/corrupt/missing-key, CRUD secret-write-only (+DB ciphertext scan), all-admin-routes RBAC, org-isolation 404s, 503 mapping, secret length cap, dry-run test endpoint, from-connection provenance, DEBUG-level log-scrub. |
| `test_mitre_schedule.py` | 13c: due-instant goldens (daily/weekly/wrap), schedule PATCH validation, sweep advance-on-enqueue + dedup-no-advance, stale-running self-heal (+enqueue same pass), pending-preview non-blocking, worker pull completed/failed/deleted-connection paths. |
| `test_mitre_siem_health.py` | 13d: list `siem` brief + report-footer provenance (secret-free), health/streak math, notification at exactly 2 / once per streak / reset on success / no secrets or rule content in the email, threshold pin. |
| `test_mitre_plain_language.py` | 14a: curated IDs all resolve `ok` + cover priorities ∪ threat-profiles, entries complete, tactic lines cover every dataset shortname, first-sentence fallback, why-phrase goldens per state (incl. the sample-kit covered-vs-disabled visible difference), explain endpoint E2E (four blocks, sibling closest-rule, 404/409). 14i: `telemetry_fields.json` keys all real ATT&CK components, entries complete, all 35 required components present, `telemetry_requirements`/`telemetry_lines` curated (T1059.001) vs uncurated-degrade (T1219.003) goldens, explain endpoint `good.telemetry`. |

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
  CHECK), 031 (mapping_status CHECK), 032 (logic column), 033
  (mapping_status + 'manual'), 034 (mitre_connections vault), 035
  (schedule columns). **5th sync
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
- **SIEM worker ops (Phase 13c/13d)**: the `scopewise-worker` container
  (compose service `worker`: Celery worker + in-process beat, no ports,
  512m/0.5cpu) runs the 15-min schedule sweep + scheduled pulls. Its env
  needs `SIEM_CRED_KEY` (32-byte base64, generated into the VPS `.env`,
  never committed — absent = saved connections 503) and `SMTP_*` (13d
  admin notifications). Deploy = normal compose loop (the worker builds
  from the same API image). Health/streak visible at `/mitre/connections`
  (admin). Full ops detail: `MITRE_SIEM_INTEGRATION_PLAN.md`.
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
| 8 (opt) | `cdf6cce` | 08-02 | ATT&CK Navigator layer export (pure `navigator.py`, format 4.5, json/zip endpoint, results-page button); no migration/AI; review waived per kickoff (read-only JSON) |
| 9 (opt) | `ed9cec9` | 08-02 | Column-mapping wizard: preview `headers`+`sample_rows`, `POST .../remap` with validated override + atomic run-race guard, CSV reader caps, threadpool parse; REVISE→ACCEPT; prod deploy |
| 10 (opt) | `6ce8e48` | 08-02 | Per-mapping reviewer override: `PATCH .../use-cases/{id}/mappings` (resolve()-validated full-list edit, `manual` provenance @ 1.0, migration 033 + ORM lockstep, FOR UPDATE serialization, audit) + inline pure recompute + drawer edit UI; ACCEPT; prod deploy |
| 11 (opt) | `62f1df2` | 08-02 | Threat-informed gap weighting: curated `threat_profiles.json` (143 validated IDs, cited sources), `build_threat_profile` + within-tier sort lift, `threat_weighting_enabled` tunable, intake `threat_actors` + `GET /threat-catalog`, wizard actor chips + "Threat match" gap chip; no migration/AI; ACCEPT; prod deploy |
| 12 (opt) | `436612a` | 08-02 | Detection-strength scoring: pure `quality.py` heuristic (0-100 + rationale on technique_results, `summary.quality` rollup), optional `MitreQualityAgent` behind `quality_ai_enabled` (off, degrade-to-heuristic), drawer chip + gaps Strength column labeled distinct from coverage %; no migration; ACCEPT; prod deploy |
| 13a | `09b545e` | 08-02 | SIEM design (`598c2dc`) + Sentinel connector, token-at-trigger: `connectors/` package (resolve-then-pin egress guard, fixed Microsoft hosts), `POST /assessments/from-siem`, template-CSV reuse of the create path, wizard source toggle; REVISE→fixed→ACCEPT |
| 13b | `a94aabb` | 08-02 | Credential vault: migration 034 `mitre_connections`, AES-256-GCM AAD-bound secrets (`SIEM_CRED_KEY`), admin CRUD secret-write-only + `/test` + `from-connection`; heaviest review, ACCEPT (7/7 verified + crypto probes) |
| 13c+13d | `496b2bb` | 08-02 | Scheduler/worker (`scopewise-worker`, migration 035, 15-min sweep, self-healing dedup, per-call engines) + provenance surfacing (list chip/results line/report footer), connection health + streak, admin email at 2 consecutive scheduled failures; both REVISE→fixed→ACCEPT; prod deploy |
| 14a | `98c82b0` | 08-02 | UX clarity (plan: `MITRE_UX_CLARITY_PLAN.md`): drawer four plain-language blocks driven by curated `technique_plain_language.json` (57 entries) + `tactic_lines.json` (21 shortnames), pure `plain_language.py` why-phrase derivation (golden-tested), `GET .../techniques/{tid}/explain`, `ranking.technique_feasibility` helper. No migration, no pipeline change, no runtime LLM. Suite 781→797/7. |
| 14b | `eea44e3` | 08-02 | Every number clickable: `DrillDownPanel` (technique lists, grouped-by-state, partial why-brief inline) + `RuleListPanel` wired to coverage/domain/state tiles, heatmap domain+tactic headers, N/A group counts, rules-by-status chips, wizard parse-preview tiles; technique names enriched into GET at read time; headline subtitle + "is this % bad?" popover; header hover definitions; pluralization fixes. |
| 14c | `4a2325f` | 08-02 | XLSX polish: Read Me guide sheet first, auto-filter/wrap/frozen everywhere, state/tier/feasibility fills, register Name + plain-words + Why columns (reuses `derive_why`) with tactic names, numeric row sort + plain-words statuses, feasibility-grouped gaps with colored headers, Summary What-it-means column ("Strict %"→"Coverage %"). Structure goldens. |
| 14d | `36415d2` | 08-02 | Project metadata (project/scope/prepared-by/purpose in `params.intake`, capped, display-only, never sent to LLMs) + `files[]` in GET + XLSX metadata rows + wizard inputs + header line + `UploadSummaryCard` (clickable rule split/disabled counts, environment summary). Also lands the 14g parser: `parse_environment_file` emits additive per-entry `interpretations`. |
| 14e | `c15ab34` | 08-02 | PDF redesign: cover (metadata, upload summary, TOC with `target-counter` page numbers) → executive ≤2 pages (traffic-light scorecard, top-5 fixes with curated definitions + threat tie-ins + cross-refs, effort-to-impact projection, trend vs previous completed run — the report endpoint now fetches it) → detailed (stacked tactic bars + tactic one-liners, parent-level heatmap grids, feasibility-grouped gap register with why/sketch/via/AI-badge per entry) → appendices (incl. how-we-read-your-files). Running header + page N of M. |
| 14f | `c64b324` | 08-02 | Past-run history: header "Past runs" dropdown (delta vs current, jump, Compare shortcut), list search/status filter/sparkline/project names, inline rename + soft archive via `PATCH /assessments/{id}` (params JSONB flag — no migration, no deletes); archived hidden from default list (`include_archived` query), still selectable in Compare. |
| 14g | `bee1f8f` | 08-02 | Evidence trail: explain gains `expected_telemetry` + `in_scope_because` (drawer renders both); rule panel shows the per-mapping journey (plain source, confidence, rationale verbatim); XLSX "How We Read Your Files" sheet; threat-profile-matches chip → drill panel. Suite at **800/7** after 14a–14g. |
| 14-polish | `6051af6`…`2698eda` | 08-02 | User-feedback passes after walking the deployed UI (full per-commit detail: `SESSION_HANDOFF_2026_08_02_MITRE_PHASE_14_POLISH.md`): (1) all three side panels mouse-resizable via a left-edge drag handle (`useSheetResize` — shared remembered width, keyboard arrows, viewport-clamped, phones stay full-width); (2) heatmap cells show "ID Name" truncated in the same footprint + ONE delegated custom tooltip for all ~900 cells (solid bg, smooth fade, plain-words state/N-A reason) replacing native `title`; drawer hides ICS "None"/PRE pseudo-platforms, a/an grammar fix; mobile guards (past-runs dropdown viewport clamp, header row wraps); (3) XLSX Summary rebuilt as a sectioned sheet — branded title band, EXECUTIVE SUMMARY (narrative + context line), KEY NUMBERS (traffic-light coverage cell, state-colored counts), TOP 5 THINGS TO FIX FIRST, ABOUT THIS ASSESSMENT; (4) gaps table ~50% denser (px-2/py-1.5, single-line technique) with dot+text badges that carry meaning (P1 · Critical / 70 · Moderate / Build now · via Sysmon) replacing pastel pills; (5) Assumptions & N/A rebuilt — two-column accent-border assumptions grid, N/A appendix as reason-aggregated group cards with clickable technique chips. Later waves: heatmap hover fixes + collapsible matrices + legend filter (`9eabcd1`,`4d579c2`); report tables bordered grid + branded headers + zebra (`35f5d40`); darker fonts, filled state/priority pills, one-row-per-reason N/A, two-column assumptions, compact appendix tables (`a9534b5`); attack-stage table headers + balanced columns, XLSX all-cell borders (`9256ab1`); list page table→card grid (`b8d0e75`); export scopes (executive/per-tab PDF + scoped XLSX), XLSX Summary emphasis pass (visible borders, pointer-style exec summary, bold/centered values), on-page coverage search + platforms enrichment (`2698eda`). Suite 801/7 after the scope test. |
| 14h | `fa7ba86`,`e5ff17a`,`77221f9` + this commit | 08-02 | Report branding & polish, 4 sequential commits: (1) refactor — split the monolithic `report.py` into Jinja2 `templates/` + `report_common.py` + `report_xlsx.py`, zero behavior change; (2) branding — 3 new `mitre_settings` overrides (display name/accent color/watermark text), logo + running page header + optional watermark in the PDF, no migration; (3) XLSX polish — `DataBarRule`/native `BarChart` on Coverage by Tactic, `ColorScaleRule` + numeric Priority column on Gaps & Recommendations, Read Me sheet protection, workbook core properties (openpyxl-native only, xlsxwriter forbidden — no wired-up "Company" property in openpyxl, used `description` instead); (4) PDF metadata + this doc update. No computed numbers changed anywhere; suite 801→802/7 (+1 new test in unit 3). |
| 14i | `75b58bf` | 08-03 | "What logs do I need?" per gap (plan's second, distinctly-titled §14h section — relabeled 14i here to avoid colliding with the already-shipped report-branding 14h above): new curated `data/telemetry_fields.json` (top 35 of 113 ATT&CK data-source components by technique-reference frequency, 83%/88% coverage at top 25/35 — `fields`/`where`/`gotcha` per component, hand-written, never runtime-LLM); pure `plain_language.telemetry_requirements()` + `telemetry_lines()` (curated entry or bare-component-name fallback for the long tail). Surfaced in exactly 3 places, no new UI area: explain endpoint `good.telemetry` rendered in the drawer's existing "What would good look like?" block (one compact line per component: fields, where, gotcha in muted text); XLSX "Log fields needed" column on Gaps & Recommendations (reuses existing bordered/wrapped styling helpers); PDF/HTML gap register names each gap's telemetry components under the detection sketch, with the full guidance in a single "Log fields reference" table after the register (review fix: printing the guidance per gap repeated 1.23 MB / ~680 pages on the 842-gap customer sample, since 487 techniques share "Process Creation"; the table is 35 rows / 19 KB and lives inside the register section so the per-tab `gaps` scope keeps it while `executive` still excludes it). Honesty boundary preserved throughout: wording is "your query needs X; your `<source>` should carry it" — never "your source is missing X" (this product never ingests raw logs, so field-level verification is never claimed). No coverage/scoring/pipeline change, no migration, no new settings; 62 no-data-source techniques keep their unchanged "bespoke detection engineering" verdict. Suite 803→809/7 (+6 new tests in `test_mitre_plain_language.py` + the extended XLSX structure golden); `tsc --noEmit` clean. |

## 16. Optional feature work (plan §14 — not launch blockers)

Originally deferred by design; queued as optional **Phases 8–13** (one
feature per session, kickoff prompt committed as `cf6e9e4`). **Shipped:
Phase 8 (ATT&CK Navigator layer export), Phase 9 (interactive
column-mapping wizard), Phase 10 (per-mapping reviewer override +
inline recompute), Phase 11 (threat-informed actor/industry gap
weighting), Phase 12 (per-rule detection-strength scoring), and
Phase 13 (SIEM integration 13a–13d: Sentinel pull, credential vault,
scheduler/worker, provenance + failure observability — contract:
`MITRE_SIEM_INTEGRATION_PLAN.md`)** — see §15 for commits. Still open,
build only on request: additional SIEM connectors (Splunk ES / Elastic —
the first customer-supplied-hostname connectors, exercising the egress
guard's full deny set), ICS/Mobile entries in the priorities file, and
per-org priority-tier overrides (the `mitre_settings` pattern already
supports it). When one of these lands, extend §15's history table and
the relevant sections here.
