# Guideline Feasibility Plan: Evidence Model, SOW Rules, Detectors, Trust Basics

**Source docs**: `docs/sample/SOW_Sample/SOW_Review_Training_Guideline.md`
(the guideline), `docs/planning/ACCURACY_BASELINE_2026_07_22.md` (measured
baseline: strict recall 72.4%, precision ≈93%).
**Target duration**: Phase A ~half a day; Phase B ~half a day; Phase C ~1 day;
Phase D ~half a day. Phases are independent enough to run A alone and stop.
**Status**: Ready to start.
**Excludes**: The guideline's non-feasible half — multi-backend AI providers
(Azure OpenAI/Bedrock/Vertex — deliberate OpenRouter-only cost choice),
customer-managed keys, air-gapped deployment, dual-review workflow,
explainability sub-scores. Do not build these; do not "clean up while in there."

---

## Context

Two analyses (2026-07-21 gap analysis, 2026-07-22 accuracy baseline) compared
the review pipeline against the guideline. Confirmed gaps, in priority order
by measured impact:

1. **5 rule-engine defects measured in production** — 4 false-positive
   "section required" findings on sections that exist (heading keyword
   mismatch), 1 self-negating agent finding shipped to the user.
2. **4 measured recall misses** — all appendix/sub-section detail the agent
   prompts summarize past (TI operational detail, IR lifecycle, log-inventory
   ownership, log volume).
3. **13 SOW-critical section rules missing** from
   `apps/api/app/rules/builtin.py` (guideline §5). `2_MASTER_TASKS.md`
   rule-004 (RACI) was planned but never built.
4. **Finding model lacks typed evidence** (guideline §1/§6): no
   `evidence_type`, `page`, `line_start/end`, `anchor_before/after`,
   `matched_text` columns — evidence is one freetext column, so UI/rules
   can't distinguish a broken reference from a missing section.
5. **No broken-reference or conflict detector** (guideline §4) — two of the
   guideline's five evidence types are never produced.
6. **No per-review audit metadata** (guideline "Auditability"): document
   hash, model version, rule-library version are not recorded.

Read before touching anything: `docs/planning/PROMPT_ENGINEERING_GUIDE.md`
(mandatory before editing any `get_system_prompt()`),
`docs/planning/SCORING_METHODOLOGY.md` (if scoring is touched — it shouldn't
be), `docs/RCA_LOG.md` entries for the files you edit.

**Standing rules that bite in this plan:**
- Migrations must be applied in 4 places: local `edgp_dev`, local
  `edgp_test`, VPS `scopewise_prod`, AND the hand-rolled `CREATE TABLE` in
  `apps/api/tests/test_insights_extra.py` (`analytics_db` fixture). Phase B
  touches `findings` — check all four.
- After any agent prompt edit: `python scripts/generate_prompt_docs.py` to
  regenerate `prompts/`, and log rationale in PROMPT_ENGINEERING_GUIDE.md's
  changelog.
- New tunables follow the org-override pattern in
  `apps/api/app/admin/customization.py` (new rules must be org-disableable
  like existing ones).
- Full suite green before/after each phase: `cd apps/api && python -m pytest`
  (current baseline 505 passed — don't regress). Frontend changes:
  `npx tsc --noEmit` clean.
- Agent-prompt and rule-engine changes are AI-classifier paths → Tier 0
  judgment for design/review; Sonnet subagents may do mechanical
  implementation with line-by-line diff review; adversarial sign-off per the
  global playbook before push.

---

## Phase A — Measured-defect fixes + 13 section rules (highest ROI, no migration)

### A1. Fix the 4 rule false positives
In `apps/api/app/rules/builtin.py`, the section-presence checks for
Executive Summary, Scope of Work, Deliverables, Assumptions missed the test
document's actual headings ("Purpose", "Scope of Services", numbered
headings). Fix: widen each rule's heading-synonym list (e.g. Executive
Summary → also "purpose", "overview", "introduction"; Scope of Work → also
"scope of services", "services"; Assumptions → also "assumptions and
dependencies"). Verify each synonym against the real headings in
`docs/sample/SOW_Sample/SOC_SOW_Testing.docx` and the other sample SOWs in
`docs/sample/SOW_Template/`. Add one regression test per fixed rule using
the actual heading string that was missed.

### A2. Suppress self-negating findings
The SecurityReviewer emitted "Missing Accessibility Standard" whose own
description says the requirement is not applicable. Root-cause fix belongs at
the shared post-processing seam, not per-agent prompt patching: in the
orchestrator's finding-ingestion path (`apps/api/app/ai/orchestrator.py`,
where agent JSON becomes Finding rows), drop findings whose description
declares non-applicability (phrases like "not applicable", "no issue found",
"compliant") — a small deny-list check, case-insensitive, on the description
head. Also add one line to the base agent prompt: "If a check is not
applicable, omit it entirely — do not emit a finding saying so." Test: feed a
synthetic agent response containing a self-negating finding, assert it's
filtered.

### A3. Add the 13 SOW section rules (guideline §5)
Extend `builtin.py` with missing-section rules following the existing rule
pattern (id, category, severity, recommendation, org-disableable):
Project milestones, KPI section, Service credits, RACI matrix, Compliance
requirements, Data retention policy, Exit/transition-out plan, Disaster
Recovery, Business Continuity, Intellectual Property, Payment schedule,
Customer staffing assumptions, Glossary.
- Severity: High for RACI/exit plan/payment schedule/compliance/IP; Medium
  for the rest; Low for Glossary.
- Heading synonyms per rule (e.g. exit plan → "transition-out",
  "termination assistance", "offboarding"; service credits → "SLA credits",
  "penalties"). Note: many sample docs legitimately place these in an MSA —
  keep severities as above but the recommendation text should say "or
  reference the MSA section that covers it" to avoid false-alarm fatigue.
- One test per rule: a doc text missing the section fires it; a doc text
  containing a synonym heading doesn't.
- Reconciliation: these overlap with what agents already find (e.g. PMO
  flags missing RACI). That's fine — dedup already exists in the
  orchestrator; verify the new rule + agent finding pair actually dedups on
  the live test doc rather than double-reporting.

### A4. Prompt additions for the 4 recall misses
Per PROMPT_ENGINEERING_GUIDE.md process. Two edits in
`apps/api/app/ai/agent.py`:
- **ScopeReviewer**: add instruction to decompose each listed service line
  and check for operational detail — for Threat Intelligence (IOC lifecycle,
  sources, reporting) and Incident Response (NIST SP 800-61 phases:
  identification, containment, eradication, recovery, lessons learned).
- **PMOReviewer or DeliveryReviewer** (pick one, not both): add instruction
  to audit appendix tables for ownership/status/retention columns and
  volume estimates (GB/day, EPS) when a log inventory or resource table is
  present.
Then regenerate `prompts/`, changelog the rationale.

**Exit criteria A**: pytest green; rerun the review on `SOC_SOW_Testing.docx`
(rerun script pattern from 2026-07-21 session, container path known) and
re-score against the ground truth: the 4 false positives gone, strict recall
≥ 79% (23/29 — the two prompt-addressable misses SOW-004/006 caught; the
appendix ones may need Phase B page anchoring to fully land). Update
`ACCURACY_BASELINE_*.md` with a dated second measurement.

---

## Phase B — Typed evidence model (one migration, guideline §1/§6)

Add to `Finding` model + `findings` table (nullable, no backfill):
- `evidence_type` VARCHAR(30): `location | missing_section | cross_document
  | conflict | reference` (CHECK constraint or app-level enum)
- `page` INT NULL, `line_start` INT NULL, `line_end` INT NULL
- `anchor_before` VARCHAR(255) NULL, `anchor_after` VARCHAR(255) NULL
  (neighboring sections for missing-section findings)
- `matched_text` TEXT NULL (verbatim quote for location findings)

Work items:
1. Migration `0XX_finding_evidence.sql` — apply to all 4 places (see
   standing rules). Grep `test_insights_extra.py` for `CREATE TABLE` blocks
   touching `findings`.
2. Model + Pydantic schema updates; API responses include the new fields.
3. Producers: rule engine sets `evidence_type='missing_section'` (+ anchors
   where computable); ambiguous-language scan sets `location` + matched_text
   (it already knows the matched phrase); agents get the evidence fields
   added to their JSON output schema — prompt edit per the guide, tolerant
   parsing (missing fields → null, never a parse failure).
4. Known ceiling: `page_count` returns 1 for the 6-page test DOCX (parsing
   limitation, observed 2026-07-21), so agent-reported page numbers for DOCX
   are unreliable at first. Ship fields as nullable; fix DOCX pagination
   separately if page pinpointing becomes a priority. Do not block Phase B
   on it.
5. Frontend: display evidence_type as a small tag on finding cards and
   matched_text as a quoted block when present (`apps/web` finding
   components); `tsc --noEmit` clean.

**Exit criteria B**: migration applied ×4, suite green, a fresh review shows
typed evidence in API response and UI, PDF report unaffected (or gains the
tag cheaply — WeasyPrint template).

---

## Phase C — Broken-reference detector (+ conflict detector, optional)

### C1. Broken-reference detector (deterministic, high value, low risk)
New `apps/api/app/rules/references.py`: regex-scan document text for
internal references — `Appendix [A-Z]`, `Section \d+(\.\d+)?`, `Annex`,
`Exhibit`, `Schedule [A-Z0-9]`, `Table \d+` — and verify the target exists
among parsed headings/labels. Each dangling reference → finding with
`evidence_type='reference'`, matched_text = the referring sentence, severity
Major. Wire into the engine like `ambiguous_language.py`; org-disableable.
Tests: doc referencing a missing Appendix C fires; existing Appendix B
reference doesn't; case/format variants covered.

### C2. Conflict detector (LLM pass — build only if C1 lands cleanly)
Within-document contradiction check (guideline evidence type `conflict`):
one extra LLM call after the 6 agents, prompt: "list pairs of sections whose
statements contradict (dates, amounts, SLAs, scope), return section pair +
both quotes", producing `evidence_type='conflict'` findings with both quotes
in evidence. This adds ~1 agent-call of latency/cost per review — acceptable.
Keep it a separate orchestrator step (not a 7th persona) so it can be
feature-flagged off per org. If output quality is poor on the test doc,
park it and note in the doc — don't tune endlessly (abort criterion applies).

**Exit criteria C**: rerun on test doc — guideline §4's scenario (reference
to nonexistent content) produces a `reference` finding; suite green.

---

## Phase D — Audit metadata (guideline "Auditability", cheap trust win)

Add to the review record (reviews table or a JSONB `audit_meta` column —
prefer JSONB to avoid a wide migration): document SHA-256 (compute at upload
if not already stored), model id(s) actually used (the OpenRouter router
already knows which model answered — capture it), rule library version (a
`RULES_VERSION` constant bumped when builtin.py changes), app version/git
SHA, UTC timestamp (exists), triggering user (exists). Surface read-only in
the review detail UI and PDF report footer.
Skip (speculative until a customer asks): compliance-standard mapping per
rule, explainability scores, immutable audit log storage.

**Exit criteria D**: fresh review's audit block visible in API + PDF footer;
suite green.

---

## Order and delegation

A → (deploy + re-measure) → B → C → D. Each phase is one commit minimum
(one per logical unit), deployed via the standard VPS loop with migration
step for Phase B. Mechanical implementation (A1, A3 rule bodies, B model
plumbing, C1 regex engine) → Sonnet subagents with exact contracts + diff
review; prompt design (A4, C2) and all accuracy judgment → main session;
adversarial sign-off before push on agent.py / rules changes per playbook.
Re-measure against the ground truth after A and after C; append dated
results to `ACCURACY_BASELINE_2026_07_22.md`.
