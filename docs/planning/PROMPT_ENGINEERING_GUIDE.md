# Prompt Engineering Guide — ScopeWise AI Review Agents

This is the process doc for how the 6 review agents' prompts get
improved over time. The prompts themselves live in
`apps/api/app/ai/agent.py` (source of truth) and are mirrored to
`prompts/*.md` (read-only, regenerated via `scripts/generate_prompt_docs.py`).

## What "improving accuracy" means here

ScopeWise does not train or fine-tune a model. Every agent is a system
prompt sent to a hosted model via OpenRouter
(`apps/api/app/config.py`'s `openrouter_model` + fallback chain — see
CLAUDE.md, this is a deliberate cost choice, never call Anthropic/OpenAI/
Google directly for the review pipeline). "Improving the AI's accuracy"
is **prompt engineering**: sharpening what each agent is told to look
for, how it's told to score confidence, and what output shape it must
return — not retraining weights. Measured via
`docs/planning/5_LAUNCH_CRITERIA.md`'s Metrics 1.1-1.4 (precision,
recall, confidence calibration, deduplication).

## Division of labor: rule engine vs. AI agents

`apps/api/app/rules/builtin.py` already runs ~40 deterministic checks
(section presence, word count, keyword presence, conditional rules) and
measured **100%/100% precision/recall** on the 2026-07-18 pass — it's
exact-match, so it can't be wrong on what it actually checks. When
writing or editing an agent prompt, **don't ask the agent to duplicate
what the rule engine already checks by keyword/section match** (e.g. "is
confidentiality mentioned" — `SOW-013` already does this). Ask the agent
to judge what the rule engine structurally cannot: quality, mutuality,
interaction between clauses, ambiguity, and risk severity. Several
prompts below now say this explicitly ("a rule engine already checks X,
your job is Y") so a future editor doesn't accidentally re-litigate it.

## 2026-07-20 revision — sources and rationale

Triggered by: the 2026-07-18 accuracy pass
(`docs/planning/5_LAUNCH_CRITERIA.md` Measured Results) found
structured-field extraction (LegalReviewer governing-law detection,
PMOReviewer governance-structure detection) right 75% of the time while
stated `overall_confidence` clustered at 80-100% — real overconfidence,
not calibration across all findings. Separately, building a real-document
test set (`docs/sample/`) surfaced concrete, well-established checklist
items the prompts were missing.

### 1. Shared confidence-calibration rubric

Added `_CONFIDENCE_CALIBRATION` (module-level constant, `agent.py`),
appended to every agent's prompt before its output-schema block. Gives
concrete anchors instead of leaving confidence to untethered judgment:

- 0.85-1.0: quoting exact clause text
- 0.60-0.84: present but requires interpretation, or inferred from a
  plausibly-applicable section
- 0.30-0.59: inferring absence/ambiguity from what's not stated
- Below 0.30: guessing, or document too fragmentary

Explicitly instructs against defaulting to 0.8-0.9 as a "safe middle" —
that's the exact pattern the 2026-07-18 pass measured.

### 2. Per-agent additions

Sourced from two places: (a) IACCM's "Most Negotiated Terms" research
(already cited as a scoring-methodology source in
`docs/planning/SCORING_METHODOLOGY.md`) for what real contract risk
concentrates in, and (b) a real GSA (US federal) Email-as-a-Service SOW
template found while assembling the real-document test set
(`docs/sample/SOW_Template/statement-of-work-template-18.docx`) — its
"Constraints" section (Access Control, Authentication, Personnel Security
Clearances, NDAs, Accessibility, Data, Confidentiality/Security/Privacy,
Privacy Act) is real, established government-contract checklist content,
not invented.

| Agent | Added | Why |
|---|---|---|
| Scope | Explicit exclusions check, unstated client-side assumptions | A deliverables list with no exclusions is a scope-creep entry point; unstated client dependencies are a common real gap |
| Delivery | Staffing/resource availability, schedule buffer | A timeline with no named/role-based resourcing or zero slack is optimistic by default |
| Commercial | Renewal/auto-renewal terms, currency & tax treatment (conditional on cross-border indication) | Silent auto-renewal with a short notice window is a classic commercial trap; currency/tax only checked when actually relevant |
| Security | Personnel security clearances, breach/incident notification timeline, accessibility compliance (conditional on public-facing deliverable) | Sourced directly from the GSA template's real Constraints section |
| PMO | Reporting cadence specificity, risk register/RAID log mention | Vague cadence ("regular updates") is functionally no cadence |
| Legal | Confidentiality mutuality + duration (distinct from the rule engine's mere presence check), insurance requirement, assignment/subcontracting rights, force majeure | IACCM's top-10 negotiated terms; none of the 6 agents covered these before |

Conditional checks (currency/tax, accessibility) are explicitly scoped
in-prompt to skip when not applicable — a cross-border or public-facing
signal must be present, not forced onto every document.

### What was deliberately NOT done in the initial pass (later completed same day)

- No new agents, no schema restructuring beyond adding new `type` enum
  values and 1-2 new boolean fields per agent's structured-extraction
  object (`legal_terms`, `governance`, etc.) — additive only, so
  `apps/api/tests/test_legal_reviewer.py` and `test_pmo_reviewer.py`'s
  substring-based topic-coverage tests stay valid without modification.
- ~~No re-run of the live-API precision/recall harness~~ **Done later
  the same day** — see "Live-model validation" below. Found and fixed 3
  real bugs (`max_tokens`, timeout retry, missing `evidence` fields on 3
  agents) that a structural-test-only pass could never have caught.

## Live-model validation (2026-07-20, same day as the revision above)

Ran the revised prompts against real OpenRouter output (`z-ai/glm-5.2`)
on real documents — not simulated. Full writeup:
`docs/planning/5_LAUNCH_CRITERIA.md`'s "Real-document spot-check
(2026-07-20)" section. Three real bugs found and fixed in the process:

1. `max_tokens=4000` truncated JSON output on large real documents
   (~30K input tokens) — raised to 8000 in `apps/api/app/ai/agent.py`.
2. Agent timeout (60s, no retry) intermittently dropped a random agent's
   findings entirely on real API latency variance — added one retry at
   90s in `ReviewOrchestrator._run_agent`.
3. `DeliveryReviewer`, `CommercialReviewer`, `SecurityReviewer` never had
   an `evidence` field in their output schema (unlike Scope/PMO/Legal) —
   silently broke dedup and clause-location for 3 of 6 agents since
   those features depend on evidence text. Fixed by adding `"evidence"`
   to all 3 schemas + an explicit quote-evidence instruction.

Qualitative result: the calibration rubric visibly worked (confidence
tracked certainty rather than clustering high), every new checklist item
fired correctly with accurate reasoning, and the pipeline correctly
handled a genuinely hard real-world case (FAR-clause incorporation by
reference in a real federal contract) without false-flagging terms that
existed via reference rather than literal text.

## Real test set status (2026-07-20, updated 2026-07-22)

`docs/sample/` had 4 real RFP samples (`RFP_Sample/`) and ~90 SOW/RFP
templates (`SOW_Template/`, `RFP_template/`) — mostly blank fill-in-the-
blank templates (Lorem Ipsum, "DESCRIPTION HERE"), not usable for
grading. **Added `docs/sample/Real_Federal_Contracts/`**: 4 real, awarded,
filled US federal contracts sourced from USCIS's public contracts
reading room (see that folder's README for provenance/caveats — real
federal-contract formatting, not representative of a typical commercial
SOW). Still no real *commercial* (non-government) filled SOW/RFP in the
repo, and still short of the ≥10-doc launch-gate set.

**2026-07-21/22 — user-supplied hand-labeled ground truth now exists:**
`docs/sample/SOW_Sample/SOW_Review_Training_Guideline.md` contains 29
hand-labeled findings (SOW-001..SOW-029, each with section, page, line
range, finding, recommendation, and severity) against
`docs/sample/SOW_Sample/SOC_SOW_Testing.docx` (a commercial-style SOC
services SOW — parses cleanly, 5.3K chars). It also specifies a target
evidence model (evidence_type: location / missing_section /
cross_document / conflict / reference; anchors; line-level citations)
that goes beyond what the pipeline currently emits, plus an
"Enterprise Trust Framework" section (positioning, auditability,
compliance-mapping, multi-backend AI) that reads as product-direction
input, not just test data. **This is the ground truth the scored
Metrics 1.1/1.3 pass should run against first** — run the pipeline on
`SOC_SOW_Testing.docx`, score findings against the 29 labels, and
measure precision/recall/calibration for real (blocked only on the
OpenRouter key limit as of 2026-07-20). The user also added several
filled/real SOW PDFs to `SOW_Sample/` and `SOW_Template/` (AWS example
SOWs, a 126-page SOW-drafting guide, etc.) — all parse cleanly except
`SOW_Template/sample-statement-work.pdf` (6 pages, 95 chars extracted —
image-only scan, the parser has no OCR; a known gap, not a regression).

## Changelog

- **2026-07-20**: Confidence calibration rubric added to all 6 agents.
  Scope (+2 checks), Delivery (+2), Commercial (+2), Security (+3), PMO
  (+2), Legal (+3) additive checklist items. See table above.
- **2026-07-20 (same day, live-model validation pass)**: `max_tokens`
  4000→8000, agent timeout retry (60s→60s+90s), `evidence` field added
  to Delivery/Commercial/Security schemas. Sourced 4 real federal
  contracts into `docs/sample/Real_Federal_Contracts/`. 5 new tests.
