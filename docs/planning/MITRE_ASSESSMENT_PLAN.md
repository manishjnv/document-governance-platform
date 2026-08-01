# MITRE ATT&CK Coverage Assessment — Design + Implementation Plan

**Status:** Plan approved-pending-review, not started.
**Written:** 2026-08-01 (design-only session; no code touched).
**Read first:** root `CLAUDE.md` (migrations rule, testing baselines, VPS deploy),
`docs/planning/PROMPT_ENGINEERING_GUIDE.md` (before writing the two new LLM prompts).

---

## 1. Goal

A new, self-contained ScopeWise module: a customer uploads their SIEM
use-case/detection-rule dump (with or without MITRE TTP tags) plus an asset/
environment inventory, answers a short intake form, and receives a MITRE
ATT&CK coverage assessment — executive and detailed — with:

- Coverage % **overall**, **per domain** (Enterprise / ICS / Mobile),
  **per tactic** ("section wise"), and **per technique/sub-technique**
  ("TTP wise").
- **Gaps** clearly explained, ranked by priority.
- **Exact recommendations** per gap (which detection to build, on which log
  source they already have — or which log source to onboard first).
- **Remediation roadmap** bucketed short (0–3 mo) / mid (3–9 mo) /
  long (9–18 mo) term.
- **Assumptions** (auto-collected + customer-declared) and **Not-Applicable
  techniques with explicit reasons**.
- Outputs: interactive in-app results, executive+detailed **PDF**, detailed
  **XLSX** gap register. Input file types: **xlsx, xls, csv, pdf, docx**.
- **Trend comparison** between any two assessments of the same org.

**Hard constraint: zero behavioral change to existing functionality.** The
entire feature is a new `app/mitre/` backend package, new DB tables, and a new
`/mitre` frontend section. Exactly two shared files gain one addition each
(§5). Nothing in the SOW/RFP review pipeline is modified.

### Decisions locked with the user (2026-08-01)

| Decision | Choice |
| --- | --- |
| ATT&CK domains | **All three: Enterprise + ICS + Mobile** (asset list gates which domains are applicable per customer) |
| Coverage denominator | **Applicability-filtered**: techniques impossible in the customer's environment become N/A-with-reason and leave the denominator |
| v1 outputs | **In-app + PDF + XLSX** |
| Lifecycle | **Point-in-time runs + trend comparison** between runs |

---

## 2. What the customer must provide (intake spec)

This section is the product answer to "what else is needed from customer?"

### Required

1. **Use-case / detection-rule dump** — xlsx, xls, csv, pdf, or docx. The
   customer is explicitly asked (and the template's primary columns are):
   **use-case name**, **MITRE technique tags** (`T1059`, `T1059.001`, …),
   and the **full detection condition/logic**. Also recommended:
   description, log source, status (enabled/disabled). Untagged dumps
   still work — the AI tags them, confidence-scored and listed under
   Assumptions — but tags are requested up front, not treated as a bonus.
   Spreadsheets in the template layout (§9) skip all column-mapping
   guesswork.
2. **Environment workbook** — one multi-sheet Excel template (user
   decision 2026-08-01: these arrive as a file, not as on-screen
   checklists):
   - *Assets / Platforms* — which platforms exist at all: Windows / Linux
     / macOS; AWS / Azure / GCP; Microsoft 365 / Google Workspace / other
     SaaS; identity providers (AD, Entra ID, Okta); containers/Kubernetes;
     network infrastructure; **OT/ICS assets (gates the ICS matrix)**;
     **managed mobile fleet + MDM (gates the Mobile matrix)**.
   - *Log Sources* — SIEM/log platform(s) plus onboarded sources, one row
     each, mapped by the ingest step to ATT&CK data sources (endpoint/EDR
     telemetry, Windows event logs, Sysmon, identity/auth logs, DNS,
     proxy/web, email gateway, cloud control plane, cloud audit,
     netflow/NDR, firewall, DLP, container runtime, OT telemetry, MDM).
   - *Security Tooling* — EDR, AV, email security, proxy/SWG, NDR, DLP,
     CASB, WAF, IAM/PAM — used to judge what's *feasible* to detect and to
     bucket the roadmap.
   - *Crown Jewels* — critical assets/services; feeds gap-priority
     tie-breaks and roadmap narrative in v1.
   Missing sheets are tolerated (each absence becomes an assumption line).
3. **On-screen intake** (kept deliberately small; stored on the
   assessment):
   - Industry and region — dropdown selects.
   - "Count disabled rules as coverage?" toggle — default **No** (a
     disabled rule scores at best "partial").
   - Scope-exclusions editor — rows of *what is excluded* + *reason*
     (see below).

### Scope exclusions, explained

A scope exclusion is the customer declaring "do not assess us on this, and
here is why" — e.g. "Mobile out of scope: BYOD fleet is unmanaged and not a
SOC responsibility", "AWS monitored by our MSSP under a separate contract",
"T1200 Hardware Additions: accepted risk, physical access controls in
place". The reason is mandatory because the report must distinguish three
different kinds of "not covered": (a) a genuine gap, (b) *derived* N/A —
impossible in this environment because the platform doesn't exist, and
(c) *declared* N/A — deliberately excluded by the customer. Declared
exclusions leave the coverage denominator just like derived N/A, but the
N/A appendix prints them separately, attributed "customer-declared", with
the verbatim reason — so an executive reading "78% coverage" knows exactly
what that number does and does not claim.

### Optional (each one materially improves accuracy — say so in the UI)

- Incident history / top concerning threat actors.
- Prior assessments, pentest or red-team findings.
- Per-log-source retention and ingestion coverage (% of fleet reporting).
- Compliance drivers (informs roadmap ordering narrative).

### Privacy notice — displayed on screen (user decision 2026-08-01)

The upload wizard shows this before any file is selected (plain-English
copy finalized at build time): *"We never ask for credentials, raw log
data, or personal data — upload rule metadata and environment inventory
only. Files are stored encrypted; only minimal rule excerpts are sent for
AI tagging."* Backing behavior: rule dumps occasionally embed secrets in
queries — file contents are stored via the existing encrypted storage
backend, never echoed into LLM prompts beyond the rule fields needed for
mapping, never written to logs.

---

## 3. Approaches considered

- **A. Isolated module reusing platform primitives (CHOSEN).** New
  `app/mitre/` package + new `mitre_*` tables + static bundled ATT&CK data;
  reuses auth/org scoping, storage, openpyxl/xlrd/pypdf parsing, the
  `ReviewAgent` OpenRouter machinery via subclassing (the proven
  `ConflictDetector` pattern), WeasyPrint HTML→PDF reporting, and the
  admin-customization org-override pattern. Two one-line shared-file
  touchpoints. Cheapest, safest, matches every existing convention.
- **B. Piggyback on the Document/Review pipeline** (new `document_type
  ='MITRE'`, a 7th registered agent). Rejected: requires ALTERing the
  `documents.document_type` CHECK (a documented recurring trap), and a 7th
  agent in `ReviewOrchestrator.agents` silently changes every review's
  status math and `overall_confidence` — exactly the load-bearing path the
  requirement says not to touch.
- **C. Standalone service/app.** Rejected: duplicates auth, storage, org
  model, and deploy plumbing on a shared VPS for no isolation benefit that
  approach A doesn't already give.

---

## 4. Architecture overview

```text
Use-case dump (xlsx/xls/csv/pdf/docx) ─┐
Environment workbook (xlsx) ───────────┼─→ POST /api/v1/mitre/assessments   (create+parse, sync)
Intake form (JSON) ────────────────────┘         │  returns parse preview + detected column map
                                          ▼
                             POST /assessments/{id}/run   (202; fire-and-forget task)
                                          │
        ┌─────────────────────────────────┴───────────────────────────────┐
        │ 1 validate customer TTP tags against pinned ATT&CK data         │
        │ 2 AI-tag untagged rules (batched, OpenRouter chain)             │
        │ 3 applicability engine: assets+intake → N/A with reasons        │
        │ 4 coverage computation: per-technique state + all rollups       │
        │ 5 gap ranking (deterministic) + LLM narrative/recommendations   │
        │ 6 persist technique_results + summary JSONB; status=completed   │
        └─────────────────────────────────┬───────────────────────────────┘
                                          ▼
   GET /assessments/{id}  (frontend polls status, then renders results)
   GET /assessments/{id}/report?format=html|pdf     GET .../export.xlsx
   GET /assessments/{id}/compare/{other_id}         (trend)
```

**Numbers are deterministic; prose is LLM.** Every percentage, count, state,
and N/A reason is computed by pure Python from the pinned ATT&CK dataset —
reproducible and testable. The LLM contributes only (a) technique tagging of
untagged rules (confidence-scored, listed in assumptions) and (b) narrative:
executive summary, per-gap recommendation text, roadmap prose.

### Isolation guarantee (the "don't touch existing functionality" contract)

| Shared file touched | Change |
| --- | --- |
| `apps/api/main.py` | +1 import, +1 `app.include_router(mitre.router)` (appended at the end of registrations — NOT between `documents_extra`/`documents`, whose order is load-bearing) |
| `apps/web/components/AppShell.tsx` | +1 entry in `NAV_ITEMS` (label "MITRE Assessment", lucide `Target` icon) |

Everything else is new files. Explicitly NOT touched: `app/parser.py`,
`app/routers/documents.py`, `app/routers/reviews.py`, `app/ai/agent.py`,
`app/ai/orchestrator.py`, any `models/*.py`, any existing frontend page.
New tables only — no ALTERs — so the `test_insights_extra.py` hand-rolled
fixture (migration checklist item 4) is **not** in play; the migration
checklist reduces to the three psql applies (§6).

---

## 5. ATT&CK reference data (static, pinned, offline)

- `scripts/build_attack_data.py` (dev-run, never at runtime): downloads the
  official MITRE `attack-stix-data` bundles (enterprise-attack, ics-attack,
  mobile-attack) for a pinned version, compacts them to
  `apps/api/app/mitre/data/attack.json`:
  `{version, generated_at, domains: {enterprise|ics|mobile: {tactics:
  [{id, shortname, name}], techniques: [{id, name, tactics[], platforms[],
  data_sources[], is_subtechnique, parent_id, deprecated, revoked,
  superseded_by, summary}]}}}`. Checked into the repo (a few MB) — the app
  never fetches from the internet.
- Pin the latest ATT&CK release at build time; the version string is stamped
  on every assessment (`attack_version`) and printed in report footers.
  Upgrading ATT&CK later = rerun script, commit new JSON; old assessments
  keep their stamped version (results are already materialized).
- `apps/api/app/mitre/data/technique_priorities.json` — hand-curated tier
  list (~40 high-prevalence techniques from public threat reporting; source
  links in the file header) used for gap ranking. Org-overridable later;
  static in v1.
- Revoked techniques remap to `superseded_by` during tag validation;
  deprecated ones are flagged and excluded from the denominator with reason
  "deprecated in ATT&CK vNN".

---

## 6. Data model — migration `029_mitre_assessment.sql`

Three feature tables plus the small keyed `mitre_settings` tunables table
(§8), all in one migration and all inheriting the house conventions (UUID v4 PKs,
`org_id` FK → organizations CASCADE, `TimestampMixin` + `SoftDeleteMixin`,
string+CHECK enums kept SQLite-portable, idempotent DDL in the style of
`027_finding_evidence.sql`). New model files under `app/models/` must be
registered in `app/models/__init__.py` `__all__` (FK targets before
dependents).

1. **`mitre_assessments`** — `assessment_id` PK, `org_id`, `name`,
   `status` CHECK (`pending|running|completed|failed`) with the Review-style
   lifecycle invariants (`completed ⇒ completed_at`, `failed ⇒
   error_message`), `attack_version`, `params` JSONB (intake answers,
   detected column map, thresholds used), `technique_results` JSONB
   (per-technique state array, ~1k entries — written once, always read
   whole), `summary` JSONB (all rollup %s, gap list, roadmap, assumptions,
   N/A list), `error_message`, `completed_at`, `created_by` (SET NULL).
2. **`mitre_files`** — `file_id` PK, `assessment_id` FK, `org_id`, `kind`
   CHECK (`use_cases|environment`), `filename`, `file_type` CHECK
   (`xlsx|xls|csv|pdf|docx`), `s3_path` (key
   `org/{org_id}/mitre/{assessment_id}/{fname}`), `parse_status`,
   `row_count`.
3. **`mitre_use_cases`** — `use_case_id` PK, `assessment_id` FK, `org_id`,
   `file_id` FK, `row_ref`, `name`, `description`, `log_source`, `enabled`
   bool (nullable = unknown), `mappings` JSONB
   (`[{technique_id, source: customer|ai, confidence, rationale}]`),
   `mapping_status` CHECK (`customer_tagged|ai_tagged|unmapped|invalid`).

`technique_results` stays JSONB rather than a fourth table: it is
write-once/read-whole (heatmap loads everything anyway) and trend diffing is
a Python dict comparison. `ponytail:` promote to a table only if cross-
assessment SQL analytics are ever needed.

**Apply checklist (no runner exists — RCA #3/#11/#12/#13):**
`docker exec -i edgp-postgres psql -U edgp_user -d edgp_dev < apps/api/migrations/029_mitre_assessment.sql`,
same into `edgp_test`, and on deploy
`docker exec -i scopewise-postgres psql -U scopewise_user -d scopewise_prod < ...`.
Item 4 (test_insights_extra fixture) is N/A — new tables only, no ALTERs to
its five duplicated tables. Keep it that way in every revision of this plan.

---

## 7. Backend module layout

```text
apps/api/app/mitre/
  __init__.py
  router.py          # APIRouter(prefix="/api/v1/mitre", tags=["mitre"])
  service.py         # run_assessment() pipeline driver + fire-and-forget task
  ingest.py          # structured xlsx/xls/csv readers, column detection, pdf/docx extraction
  attack_data.py     # loads pinned attack.json once (module-level), lookup/remap helpers
  applicability.py   # pure functions: assets+intake → N/A set with reasons
  coverage.py        # pure functions: use-case mappings → technique states + rollups
  agents.py          # MitreTaggingAgent + MitreNarrativeAgent (ReviewAgent subclasses)
  report.py          # HTML report (ReportGenerator-style) + XLSX writer (openpyxl)
  data/attack.json               (generated by scripts/build_attack_data.py)
  data/technique_priorities.json (curated)
apps/api/migrations/029_mitre_assessment.sql
apps/api/app/models/{mitre_assessment,mitre_file,mitre_use_case}.py
apps/api/tests/test_mitre_{ingest,applicability,coverage,api,report}.py
scripts/build_attack_data.py
```

### Pipeline stages (`service.py`)

1. **Ingest (`ingest.py`)** — runs synchronously inside the create endpoint:
   - xlsx via openpyxl / xls via xlrd / csv via stdlib — **direct cell
     access**, NOT `parse_document()` (the existing `ExcelParser` flattens
     sheets to text and destroys the column alignment TTP tags live in).
   - Environment workbook: sheets located by name synonyms (Assets, Log
     Sources, Tooling, Crown Jewels), each header-detected like the
     use-case dump; missing sheets tolerated, each absence recorded as an
     assumption line.
   - Column detection: header-row heuristics (synonym lists for
     name/description/logic/technique/status/log-source, e.g. "technique",
     "ttp", "mitre id", "attack id" → tags column). If headers are
     ambiguous, one LLM call classifies them. The final mapping is stored in
     `params` and echoed in the parse preview and the Assumptions section.
     If no name column is detectable → 422 with a message pointing at the
     downloadable template. `ponytail:` no interactive column-mapping wizard
     in v1 — auto-detect + assumption line + template escape hatch; build
     the wizard only if real dumps defeat detection.
   - pdf/docx dumps: text via existing `parse_document()` (OCR fallback and
     its 30-page cap apply), then the tagging agent extracts use-case
     entries from text chunks. Flagged in Assumptions as lower-fidelity.
   - Guards (this endpoint is a trust boundary): existing 50MB cap pattern,
     MIME allowlist, `_sanitize_filename` logic, empty-parse → 422 (mirror
     `reviews.py`'s guard), row caps: 5,000 use-case rows / 10,000 asset
     rows (422 beyond, stated in the error).
2. **Tag validation** — regex `T\d{4}(\.\d{3})?` over the tags column;
   validate IDs against `attack_data`; remap revoked → `superseded_by`;
   invalid/deprecated IDs recorded and the row routed to AI tagging.
   Rows with valid customer tags are NEVER re-tagged by AI (customer truth
   wins; source recorded as `customer`).
3. **AI tagging (`agents.py::MitreTaggingAgent`)** — subclass of
   `ReviewAgent` exactly like `ConflictDetector`: inherits the OpenRouter
   client, GLM-5.2→DeepSeek→MiniMax→Qwen fallback chain,
   unparseable-JSON-advances-chain, `asyncio.to_thread`, and `_model_used`
   stamping — registered NOWHERE in `ReviewOrchestrator`. Batches of ~25
   rules per call (name+description+logic excerpt), JSON out:
   `[{row_ref, technique_ids[], confidence, rationale}]`, appended
   `_CONFIDENCE_CALIBRATION` rubric. Per-batch `asyncio.wait_for` timeout +
   degrade-to-unmapped (a failed batch must not kill the assessment).
   Confidence policy: ≥0.7 counts as coverage; 0.4–0.7 counts as
   "partial"; <0.4 → `unmapped` and listed under Assumptions. Cost: ~500
   rules ≈ 20 calls ≈ well under $0.05 on the current chain.
4. **Applicability (`applicability.py`, pure)** — asset platforms + intake
   answers → N/A decisions with reason strings, most specific reason wins:
   domain-level ("ICS matrix: no OT/ICS assets declared in inventory"),
   platform-level ("T1553.001 targets macOS; macOS not in asset
   inventory"), customer-declared exclusions (verbatim, attributed).
   Missing environment workbook entirely = nothing filtered except
   customer exclusions, and a loud assumption line ("no environment
   inventory provided — full matrices assumed applicable; coverage % is a
   lower bound").
5. **Coverage (`coverage.py`, pure)** — per applicable technique:
   `covered` (≥1 enabled mapping with qualifying confidence), `partial`
   (only disabled-rule mappings, or only 0.4–0.7-confidence AI mappings),
   `not_covered`, `not_applicable`. Sub-technique rollup: a parent with no
   direct mapping but ≥1 covered sub-technique reports `partial` at parent
   level; both levels appear in the register. Headline coverage % =
   `covered / applicable` (strict); secondary figure credits partial at
   0.5. Rollups: overall, per-domain, per-tactic (a technique in N tactics
   counts in each — standard ATT&CK practice, noted in methodology
   footnote).
6. **Gap ranking (deterministic)** — uncovered techniques ranked by:
   priority tier (`technique_priorities.json`) → feasibility (customer
   already ingests a required data source → cheapest wins) → tactic
   position. Roadmap bucketing is dependency-based: **short** = required
   log source already onboarded (write detections now; name the exact
   techniques + log source); **mid** = log source obtainable from tooling
   they already own (onboard, then detect); **long** = requires new
   capability (e.g. no NDR exists) or architectural work.
7. **Narrative (`agents.py::MitreNarrativeAgent`)** — one LLM call taking
   the computed JSON (rollups, ranked gaps, roadmap buckets, N/A summary)
   and returning: executive summary (≤1 page), per-gap recommendation
   sentences, roadmap prose. It may rephrase but NEVER introduces numbers —
   report templates print numbers exclusively from the computed summary.
   Degrades to template text on failure (assessment still completes).
8. **Persist + finish** — write `technique_results` + `summary`, status
   transitions per the Review lifecycle CHECKs, `log_action()` audit,
   `invalidate_cache()`.

### Execution model

`POST /assessments/{id}/run` returns 202 immediately and launches
`asyncio.create_task` over the pipeline (LLM calls already threaded; DB via
its own session). The existing review trigger's synchronous-202 precedent is
NOT copied: a 500-rule tagging run (~20 sequential batches) would blow
through Cloudflare's ~100s proxy timeout. Frontend polls
`GET /assessments/{id}` (the admin page's visibility-aware `setInterval`
pattern). Stale-run guard: `GET` marks a `running` assessment older than 30
min as `failed` ("interrupted — likely a deploy/restart; re-run").
`ponytail:` fire-and-forget task dies on container restart — the stale guard
is the recovery path; move to the existing Celery app only if that proves
insufficient (note: no Celery worker runs in the standard VPS deploy today,
so Celery is NOT the v1 answer).

---

## 8. API surface (`/api/v1/mitre`, all org-scoped via existing deps)

| Endpoint | Purpose |
| --- | --- |
| `POST /assessments` | multipart: use-case dump, environment workbook (optional but strongly encouraged), intake JSON (industry/region, disabled-rules policy, scope exclusions). Creates rows, parses synchronously, returns parse preview (row count, detected columns/sheets, tagged/untagged split, warnings) |
| `POST /assessments/{id}/run` | 202; starts pipeline (idempotent-guard: 409 if already running/completed) |
| `GET /assessments` | list for org (name, status, date, headline %, attack_version) |
| `GET /assessments/{id}` | status + full summary + technique_results |
| `GET /assessments/{id}/use-cases` | paginated rows with mappings (filter by mapping_status) |
| `GET /assessments/{id}/report?format=html\|pdf` | exec+detailed report; PDF base64-in-JSON (matches review report shape) |
| `GET /assessments/{id}/export.xlsx` | `StreamingResponse`, proper content-type (do NOT copy the base64 shape for a workbook) |
| `GET /assessments/{id}/compare/{other_id}` | trend diff (both must belong to org) |
| `DELETE /assessments/{id}` | soft delete |

Roles: create/run/delete require `admin|reviewer`; reads allow `viewer`
(matches the platform's existing convention). Tunables (confidence
threshold, partial-credit weight, disabled-rules policy) live in a
`mitre_settings` keyed table inside migration 029 following the
`app/admin/customization.py` get/set-with-org-override pattern (own module,
own admin-only PATCH endpoint in `router.py` — no edits to existing admin
files). CLAUDE.md mandates this pattern for new tunables.

---

## 9. Frontend (`apps/web/app/mitre/`)

All pages: `'use client'`, AppShell-wrapped, inline axios +
`localStorage access_token` guard — replicate the house pattern verbatim; NO
shared API client refactor (would break the zero-change rule).

**UI principles (user-specified 2026-08-01, consistent with the existing
UI-taste rules: tight spacing, data-dense, no AI-generated look):**

- **Full-screen flexible layout** — results page uses the full viewport
  like the review results overhaul; content stretches to fill, no
  max-width straitjacket on the heatmap/register views.
- **Minimal borders, breathing gutters** — separate panels with spacing
  and subtle background shifts, not box-borders everywhere; consistent
  gutter between content and container edges (no text hugging pane edges).
- **Compact, professional, data-rich** — dense tiles/tables an analyst can
  scan; no oversized hero cards or decorative filler.
- **Modular components** — each results panel (exec band, heatmap, gap
  table, roadmap, assumptions, compare view, technique drawer) is its own
  component file colocated under `app/mitre/components/`; pages compose
  them. Panels take data via props only, so any panel can be rearranged,
  reused in the PDF-preview, or org-hidden later without rework.
- **Highly customizable** — per-org tunables via the §8 `mitre_settings`
  pattern (thresholds, weights, disabled-rules policy) from day one; panel
  visibility/report-section toggles ride the same keyed pattern when
  requested (structure supports it; don't build the toggle UI in v1).
- **Tooltips everywhere data needs context** — shadcn Tooltip with a
  smooth fade/scale transition (~150ms ease-out); every %, state badge,
  confidence value, and N/A reason gets a hover explanation.
- **Plain English throughout** — UI labels, tooltips, and all
  LLM-narrative output in simple, human-readable English: short sentences,
  no unexplained jargon ("techniques we can't see yet because no log
  source covers them", not "telemetry-gap-induced detection debt"). This
  is a hard requirement written into the MitreNarrativeAgent prompt and a
  review criterion for report templates.

- **`/mitre`** — assessment list: cards/table with status badge, headline
  coverage %, per-domain mini-bars, trend arrow vs previous completed run,
  "New assessment" CTA.
- **`/mitre/new`** — single-page wizard: the §2 privacy notice shown
  before any file is chosen; use-case dump drop + environment workbook
  drop (client validation mirroring server rules); template download
  links; slim intake form (industry + region dropdowns, disabled-rules
  toggle defaulting to No, scope-exclusions editor with what + reason
  rows); submit → create → parse preview inline (detected columns/sheets,
  tagged/untagged counts, warnings) → "Run assessment" → run + redirect
  to results.
- **`/mitre/[assessmentId]`** — results:
  - While running: progress state + poll (admin-page interval pattern).
  - Executive band: overall % tile, per-domain tiles, covered/partial/
    uncovered/N.A. counts, top-5 gaps, attack_version + run date.
  - Coverage tab: per-domain tactic columns (Navigator-style heatmap grid,
    CSS grid + shadcn Tooltip — no new charting dependency), click →
    technique drawer (state, mapped use cases, confidence, source).
  - Gaps & Roadmap tab: ranked gap table (technique, tactic, priority,
    why-it-matters, exact recommendation, feasibility) + short/mid/long
    roadmap sections.
  - Assumptions & N/A tab: assumption list; N/A table with reasons,
    grouped domain → platform → declared-exclusion.
  - Compare selector (other completed assessments) → delta view: coverage
    % deltas overall/per-tactic, newly-covered / regressed / N/A-changed
    technique lists (the `versions/diff` three-column pattern).
  - Download buttons: PDF (blob pattern from results page) + XLSX.
- **Templates**: `apps/web/public/templates/scopewise-mitre-use-cases.xlsx`
  (columns: name, MITRE tags, full detection condition/logic, description,
  log source, status) and `...-environment.xlsx` (sheets: Assets, Log
  Sources, Security Tooling, Crown Jewels). Static files generated once by
  a dev script — plain `<a download>` links, no endpoint.

---

## 10. Reports

- **PDF (exec + detailed in one document)** — `app/mitre/report.py`
  mirroring `app/scoring/report.py`'s structure: branded HTML with `_esc()`
  on ALL customer/LLM strings (stored-XSS lesson already learned there),
  A4 `@page` print CSS, lazy WeasyPrint import (system libs exist only in
  Dockerfile.prod). Order: cover + methodology footnote → executive summary
  (1–2 pp: headline %s, domain bars, top gaps, roadmap-at-a-glance) →
  detailed sections (per-tactic tables, full gap register with
  recommendations, roadmap detail, assumptions, N/A appendix, use-case
  mapping appendix) → audit footer (attack_version, git SHA, models used,
  thresholds).
- **XLSX** — openpyxl `Workbook` (already installed; no new dependency),
  sheets: `Summary`, `Coverage by Tactic`, `Technique Register` (one row
  per applicable technique+state+mapped rules), `Use-Case Mappings`,
  `Gaps & Recommendations`, `Roadmap`, `Not Applicable`, `Assumptions`.
  **Formula-injection guard:** any cell value starting with `=`, `+`, `-`,
  `@` gets an apostrophe prefix — rule names/descriptions are untrusted.

---

## 11. Security notes (gate before push)

Upload endpoint is a trust boundary: server-side MIME allowlist + size cap +
filename sanitization + row caps + empty-parse 422 (client checks are UX
only). Org scoping on every query (`org_id == current_user.org_id`); compare
endpoint validates BOTH assessments belong to the caller's org. HTML report
escapes everything; XLSX export neutralizes formula injection; LLM prompts
receive only rule name/description/logic excerpts (never whole-file dumps,
never asset inventory details beyond platform booleans). Per the global
playbook this feature (new upload surface + LLM classifier) requires an
adversarial sign-off before push — codex:rescue is broken on this account
(memory 2026-07-23), so use the approved Sonnet-takeover fallback with the
attack vectors: cross-org access on every new endpoint, upload abuse
(zip-bomb xlsx, MIME spoof, oversized rows), report XSS, XLSX formula
injection, prompt injection from rule names into the tagging agent.

---

## 12. Testing (baseline: 402 passed / 2 skipped must not regress; `tsc --noEmit` clean)

- **Pure-function unit tests** (no DB/LLM): `applicability.py` (domain
  gating, platform filtering, exclusion attribution, no-asset-list
  behavior), `coverage.py` (state assignment incl. disabled/low-confidence
  → partial, sub-technique rollup, multi-tactic counting, % math),
  tag validation (revoked remap, deprecated exclusion, malformed IDs).
- **Ingest tests** with small fixture files: template xlsx, messy-header
  xlsx, tagged/untagged mixes, legacy xls, csv, an empty file (422), an
  over-cap file (422).
- **API tests** against `edgp_test` Postgres (apply 029 first!) with the
  LLM layer mocked exactly as existing agent tests do (no OpenRouter key →
  test adapter): create→preview→run→poll→results happy path; org isolation
  (user B cannot read/compare user A's assessments); 409 double-run; compare
  endpoint; XLSX/PDF endpoints return correct content types.
- **Report tests**: HTML contains escaped payloads (`<script>` in a rule
  name), XLSX formula-injection prefix applied.
- Two-line check in `scripts/build_attack_data.py` output validation
  (technique counts per domain > known floor, all revoked have
  `superseded_by`).

---

## 13. Implementation phases (each = one commit-sized unit; ~4–5 sessions total)

**Phase 0 — Data + pure logic (no DB, no API).**
`build_attack_data.py` + checked-in `attack.json` + `technique_priorities.json`;
`attack_data.py`, `applicability.py`, `coverage.py` + their unit tests.
*Accept:* pure tests green; counts sane; zero imports from app internals
beyond stdlib.

**Phase 1 — Persistence + ingest + API skeleton (tagged-only E2E).**
Migration 029 (+ apply to dev/test DBs), 3 models + registry entries,
`ingest.py`, `router.py` + `service.py` with tag-validation path only (AI
tagging stubbed to `unmapped`), `main.py` +2 lines.
*Accept:* full API tests green for a pre-tagged template xlsx: upload →
run → coverage numbers correct end-to-end; suite baseline intact.

**Phase 2 — LLM stages.**
`agents.py` (both agents; prompts written after reading
PROMPT_ENGINEERING_GUIDE, changelog entries added there), batching, timeout/
degrade paths, assumptions assembly.
*Accept:* mocked-LLM tests for batch success/partial-failure/garbage-JSON;
one live smoke run on a real dump (manual).

**Phase 3 — Frontend.**
Three pages + nav entry + templates in `public/`.
*Accept:* `tsc --noEmit` clean; manual click-through of new/list/results
with a seeded assessment.

**Phase 4 — Reports + trend.**
`report.py` (HTML/PDF + XLSX), report/export/compare endpoints, compare UI.
*Accept:* report tests green; PDF renders in prod image; XLSX opens in
Excel; compare shows correct deltas between two seeded runs.

**Phase 5 — Hardening + deploy.**
Sonnet adversarial sign-off (§11 vectors), apply 029 to `scopewise_prod`,
standard VPS deploy loop with `GIT_SHA`, smoke test live, update
`docs/IMPLEMENTATION_PROGRESS.md`, PROMPT_ENGINEERING_GUIDE changelog,
session handoff.

---

## 14. Explicitly out of scope for v1 (deferred, not forgotten)

- Interactive column-mapping wizard (auto-detect + template covers v1).
- Manual re-tagging/override UI for individual AI mappings (PATCH endpoint
  reserved in design; build when a customer asks).
- Threat-informed weighting by actor/industry (needs curated actor-technique
  data + intake expansion).
- ATT&CK Navigator layer JSON export (trivial to add later; small demand).
- Scheduled/continuous re-assessment; SIEM API pull integrations.
- Per-technique detection-rule *quality* scoring (v1 scores presence, not
  efficacy — stated in the methodology footnote and Assumptions).

## 15. Open questions (non-blocking; defaults chosen)

1. Should viewers be allowed to download the XLSX (contains full rule
   inventory)? Default: yes, same as PDF — flag if rule dumps are
   considered more sensitive than review documents.
2. Marketing page for the feature (SEO)? Not in this plan; separate
   content task if wanted.
3. `technique_priorities.json` curation source list — draft in Phase 0,
   worth a 10-minute user review before Phase 2 bakes it into rankings.
