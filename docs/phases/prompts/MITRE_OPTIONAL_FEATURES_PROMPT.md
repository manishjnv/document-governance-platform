# Kickoff prompt — MITRE optional features (plan §14), Phases 8–13

Covers the six optional MITRE features deferred by design. **Run ONE
feature per session** — they are independent, each has its own migration/
UI/tests/review, and one session cannot do all six at quality. In a fresh
session, paste the shared context below **plus the one feature block** you
are implementing. Do them in the listed order (low-risk/high-clarity
first); skip any you don't want.

---

## SHARED CONTEXT (paste with every feature)

ScopeWise MITRE module Phases 0–7 are COMPLETE and live in prod
(2026-08-02, HEAD ≈ `b183f75`): deterministic coverage/gap engine + a
deterministic keyword/alias tagging pre-pass with AI only for the residue
+ narrative + full `/api/v1/mitre` API + `/mitre` UI (list / wizard /
results with heatmap, gaps, roadmap, assumptions, compare tabs) + PDF/
HTML/XLSX reports + trend compare. ATT&CK v19.1 pinned in
`app/mitre/data/attack.json`. Migrations 029–032 in all 3 DBs. Backend
baseline **687 passed / 7 skipped**; `tsc --noEmit` clean.

Standing rules (do not violate):
- **Isolation:** all work stays under `apps/api/app/mitre/*` and
  `apps/web/app/mitre/*`; the only ever-permitted shared edits are the
  already-done `main.py` router line + `AppShell` nav entry. Do NOT touch
  the SOW/RFP review pipeline (`app/ai/*`, `app/routers/reviews.py`,
  `orchestrator.py`); never register anything in
  `ReviewOrchestrator.agents`.
- **Coding-over-AI** ([[feedback-coding-over-ai]]): prefer deterministic
  code; reserve AI for genuine extraction/prose/fuzzy-judgment, and only
  after a deterministic pass handles the rest. Never lower quality to
  avoid AI.
- **Migrations** (root `CLAUDE.md`): no runner — apply every new `.sql`
  to edgp_dev + edgp_test now, scopewise_prod on deploy; if it ALTERs a
  CHECK also declared as an ORM `CheckConstraint`, update that string too
  (the 5th sync-point). New tables don't touch `test_insights_extra.py`.
- **LLM key:** the app reads `settings.openrouter_api_key` (app config /
  VPS `.env`, the unlimited SOW-audit key). Never judge budget from
  `$OPENROUTER_API_KEY` ([[reference-openrouter-key-identity]]).
- **Security/classifier-adjacent changes need an adversarial sign-off
  before push** (Sonnet takeover — codex:rescue is down). Tagged per
  feature below.
- **Tests:** minimal-targeted (project taste); don't regress the suite or
  `tsc`. **Don't commit/push/deploy unless the user asks.** One commit
  per logical unit. Deploy = standard VPS loop + apply the migration to
  prod + smoke. Read root `CLAUDE.md`,
  `docs/planning/MITRE_ASSESSMENT_PLAN.md`, and the target files before
  editing; state your plan first.

Recommended order: **8 → 9 → 10 → 11 → 12 → 13.** 8 is pure/low-risk; 13
(SIEM integration) is a design-first sub-project — do it last.

---

## PHASE 8 — ATT&CK Navigator layer export (pure code, low risk)

**Goal:** export an assessment's coverage as a MITRE ATT&CK **Navigator
layer JSON** so customers can open it in the official Navigator.

**Build:**
- `app/mitre/navigator.py` (pure): `build_navigator_layers(assessment)` →
  one layer per applicable domain (enterprise/ics/mobile), Navigator layer
  v4.5 schema: `{name, versions:{attack,navigator,layer}, domain:
  "enterprise-attack"|..., techniques:[{techniqueID, score|color,
  comment, enabled}]}`. Map state→color deterministically (covered=green,
  partial=amber, not_covered=red, not_applicable=disabled/grey);
  `comment` = mapped use-case count + N/A reason. Pin the `attack` version
  from the assessment.
- Endpoint `GET /assessments/{id}/navigator.(json|zip)` —
  `StreamingResponse`; multi-domain → a zip of per-domain layers. Org-
  scoped via `_completed_assessment`, viewer-readable (matches report
  policy). No new DB.
- Frontend: a "Download Navigator layer" button next to the PDF/XLSX
  buttons on the results page (blob download).

**Tests:** golden layer JSON for a seeded assessment (technique count,
colors per state, version pinned); multi-domain → zip with N entries;
cross-org 404; non-completed 409. **Review:** none required (read-only,
no untrusted HTML/formula sink — but escape/encode nothing executable).

---

## PHASE 9 — Interactive column-mapping wizard (frontend + one endpoint)

**Goal:** when ingest can't confidently detect columns (or the user wants
to correct them), let the user map columns by hand in the wizard instead
of being forced to the template.

**Build:**
- Backend: extend the create/preview flow so the parse preview returns,
  per file, the **raw header row + a sample of the first ~5 data rows +
  the auto-detected mapping**. Add `POST /assessments/{id}/remap` (or a
  create param) that accepts an explicit `{field: column_index}` override
  and re-parses the stored file with it (re-runs `ingest` with a supplied
  column map — refactor `_detect_columns` so an override can bypass
  detection). Org-scoped; only allowed while status is `pending` (before
  run). Store the final map in `params.columns` as today.
- Frontend `/mitre/new`: if detection is low-confidence or the user
  clicks "adjust columns", show a compact grid — dropdowns mapping each
  ScopeWise field (name/description/logic/tags/status/log_source) to a
  detected header, previewing the sample rows. Re-preview on apply.

**Tests:** remap endpoint re-parses with an override and changes the
detected map; rejects overrides on a non-pending assessment; out-of-range
index → 422. `tsc` clean. **Review:** light (it's an ingest path — confirm
the override can't read a file outside the assessment's org / can't index
past the row).

---

## PHASE 10 — Per-mapping override UI (accept/reject/edit a mapping)

**Goal:** let a reviewer correct individual technique mappings on a use
case (remove a wrong AI/keyword tag, add a missing one), with clear
provenance, and recompute coverage.

**Build:**
- Migration: none if you reuse the `mappings` JSONB + a new
  `mapping_status='manual'` value → migration `033` extends the
  `ck_mitre_use_cases_mapping_status` CHECK **and** the ORM
  `CheckConstraint` (5th sync-point). Add `source:"manual"` to edited
  mappings.
- `PATCH /assessments/{id}/use-cases/{use_case_id}/mappings` — body =
  the new technique-ID list; validate every ID through
  `attack_data.resolve()` (reject invalid); set `source:"manual"`,
  confidence 1.0; org-scoped; admin/reviewer only; audit via `log_action`
  (`resource_type="mitre_assessment"`).
- **Recompute:** re-run coverage/ranking (not tagging/narrative) for the
  assessment after an edit and update `technique_results`/`summary`, so
  the numbers reflect the correction. Reuse the pure `coverage`/`ranking`
  functions; do it inline (fast, no LLM).
- Frontend: in the technique drawer / a use-case list view, an edit
  control to add/remove technique IDs on a row; show "Edited by reviewer"
  provenance; refresh the results.

**Tests:** PATCH updates mappings + status=manual + recomputes coverage;
invalid ID rejected; cross-org 404; viewer forbidden (403); audit row
written. **Review: REQUIRED (Sonnet)** — coverage-affecting mutation:
focus on cross-org write, ID validation, recompute consistency, and that
a manual edit can't be spoofed onto another org's assessment.

---

## PHASE 11 — Threat-informed weighting (curated data, pure code)

**Goal:** prioritize gaps by how relevant each technique is to the
customer's **industry / named threat actors**, not just global prevalence.

**Build (deterministic — no AI):**
- `app/mitre/data/threat_profiles.json` — curated mapping of
  industry → high-relevance technique IDs and (optionally) actor →
  technique IDs, sourced from MITRE ATT&CK Groups + public industry
  threat reporting (cite sources in the header; keep IDs validated
  against `attack.json`). This is the curation-heavy part; keep it
  high-confidence.
- Intake already collects `industry`; add optional "known/among concerning
  threat actors" multi-select (from the curated actor list) to
  `/mitre/new`, stored in `params.intake`.
- `ranking.py`: add a weighting term — a gap technique that's in the
  customer's industry/actor profile ranks above equal-tier peers. Keep it
  a tunable weight via the `mitre_settings` pattern (org-overridable);
  default on. Does NOT change coverage %, only gap ordering + roadmap
  emphasis; surface "prioritized for your industry/actor X" in the gap
  row + narrative input.
- A test asserting `ranking.py` still imports no AI module.

**Tests:** golden ranking with/without an industry profile (profile
techniques rank up); weight tunable respected; unknown industry → no-op;
data-file IDs all resolve. **Review: light (Sonnet)** — it influences
what customers prioritize; confirm no coverage-% change and the curated
data is validated, not attacker-supplied.

---

## PHASE 12 — Per-rule detection-quality scoring (coding-first, AI optional)

**Goal:** score not just whether a technique is *covered* but how *well* a
detection covers it (v1 scores presence only — this adds an efficacy
signal). Keep it clearly separate from the coverage % so it doesn't muddy
the headline number.

**Build (deterministic first, per coding-over-AI):**
- `app/mitre/quality.py` (pure): a coarse heuristic score per
  covered/partial technique from signals already present — does the rule's
  logic reference the technique's expected ATT&CK **data sources/
  components** (reuse `ranking.component_category` + the technique's
  `data_sources`)? is the rule enabled? is the mapping customer/keyword
  (high-confidence) vs low-confidence AI? Output a 0–100 "detection
  strength" per technique + a short deterministic rationale. Store on the
  technique_results entries + a summary rollup.
- **AI optional, only for the residue:** if a rule's logic is free-text
  and the heuristic is inconclusive, an optional LLM pass (subclass the
  existing tagging agent, its own prompt) can rate coverage quality —
  gated behind a `mitre_settings` flag, off by default, degrades to
  heuristic. Do NOT make quality depend on AI.
- Frontend: a "detection strength" column/badge in the gap/coverage view
  with a plain-English tooltip; clearly labeled distinct from coverage %.

**Tests:** heuristic score golden cases (data-source match raises score,
disabled/low-confidence lowers it); AI path mocked + degrades; summary
rollup correct. **Review: light-to-moderate (Sonnet)** — it's a new
scored signal; confirm it never alters coverage %, and any AI path is
capped/escaped like the taggers.

---

## PHASE 13 — Scheduled/continuous re-assessment + SIEM API pull (DESIGN FIRST)

**Goal:** pull detection rules directly from a customer SIEM (Splunk ES,
Microsoft Sentinel, Elastic) on a schedule and auto-run assessments,
showing coverage trend over time automatically.

**This is a multi-phase sub-project, not a single build — START WITH
`superpowers:brainstorming`**, because it introduces genuinely new,
high-risk surfaces the current module doesn't have:
- **Customer SIEM credentials at rest** — a real secrets-management
  problem (encryption, rotation, least-privilege, per-org isolation). The
  module currently stores no third-party credentials; this changes the
  threat model materially.
- **A scheduler/worker** — Celery exists (`celery_app.py`) but **no beat
  scheduler or worker runs in the standard VPS deploy**; continuous runs
  need that infra stood up (and it's a shared VPS — coordinate ports/
  containers per CLAUDE.md).
- **Per-SIEM API clients** (auth, pagination, rate limits, rule-format
  normalization to the ingest row contract) — one connector per platform.
- **Egress from the app to customer networks** — SSRF/allowlist concerns.

Deliverable of the brainstorming session: a decomposed spec (connector
framework → one connector → credential vault → scheduler → auto-run/trend)
with each piece as its own phase + its own adversarial sign-off. **Do not
build any of it until that design is approved** — building credential
storage or a scheduler ad-hoc is exactly the wrong move. The trend/compare
*data model* already exists (Phase 4), so the auto-run just feeds it.

---

## How to run

Per session: `Read docs/phases/prompts/MITRE_OPTIONAL_FEATURES_PROMPT.md;
implement Phase <N> only (shared context + that block). Phases 0–7 are
live in prod; baseline 687 passed / 7 skipped, tsc clean.` Then commit/
deploy on the user's go, and move to the next phase in a fresh session.
