# Accuracy Baseline — SOC_SOW_Testing.docx vs Ground Truth (2026-07-22)

First measured precision/recall for the review pipeline, using the 29-row
ground-truth table in `docs/sample/SOW_Sample/SOW_Review_Training_Guideline.md`
against the live production review of `SOC_SOW_Testing.docx`
(review `0c40b7a6-2411-4618-a8b1-8eedf083b4e5`, 73 findings, 6/6 agents,
post scoring-fix deploy `e8a5d26`).

Matching was done by semantic judgment (one finding may satisfy more than one
ground-truth row; a keyword matcher would under/over-count).

## Headline numbers

| Metric | Value |
|---|---|
| Recall (strict — clear match) | **21 / 29 = 72.4%** |
| Recall (lenient — incl. 4 partial matches) | **25 / 29 = 86.2%** |
| Findings mapping to a GT row | 24 of 73 |
| Extra findings valid beyond GT scope | ~44 (most endorsed by guideline §5 "Cross-Document Missing Sections": IP, DR/BC, data retention, payment, compliance, exit plan…) |
| Questionable / false-positive findings | ~5 |
| Effective precision (valid findings / total) | **≈ 68 / 73 = 93%** |

## Per-row match table

| GT | Finding (short) | Verdict | Matched live finding |
|---|---|---|---|
| SOW-001 | Objectives not measurable | ✅ | rule: Must Address Success Metrics |
| SOW-002 | Infra inventory incomplete | 🟡 partial | Scope: "critical business applications" deferred/undefined |
| SOW-003 | SOC activities not detailed | ✅ | rule: Scope of Work must be clearly defined |
| SOW-004 | Threat Intelligence lacks operational detail | ❌ miss | — |
| SOW-005 | Threat hunting methodology missing | 🟡 partial | Scope: hunting frequency adjustable/unpredictable (methodology/MITRE not flagged) |
| SOW-006 | Incident Response lifecycle undefined | ❌ miss | — |
| SOW-007 | Deliverables lack acceptance criteria | ✅ | Legal/Comm/Scope: "material objections" acceptance ambiguity |
| SOW-008 | Report contents undefined | ✅ | PMO: report format/content structure undefined |
| SOW-009 | Only acknowledgement SLA defined | ✅ | PMO: no resolution-time commitments |
| SOW-010 | Service hours / time zone missing | ✅ | PMO: support hours only implied (same finding as SOW-009) |
| SOW-011 | Ownership unclear (RACI) | ✅ | PMO: missing RACI matrix |
| SOW-012 | Escalation matrix missing | ✅ | PMO: no escalation path/levels |
| SOW-013 | Assumptions generic | ✅ | Scope: customer obligations with no timeline/SLA |
| SOW-014 | Log onboarding assumptions missing | ✅ | Scope: log-source availability not committed |
| SOW-015 | Out-of-scope incomplete | ✅ | Scope: missing exclusions |
| SOW-016 | Transition lacks timeline | ✅ | Delivery: transition phases have no dates |
| SOW-017 | Commercial terms incomplete | ✅ | Comm/Scope: no fee amount, currency, invoicing |
| SOW-018 | CR pricing undefined | ✅ | Comm: no rate card / approval workflow |
| SOW-019 | Ambiguous contractual wording | ✅ | Legal: §12 vague language + rule: "reasonable efforts" |
| SOW-020 | Open-items prioritization undefined | 🟡 partial | PMO: no decision/change authority defined |
| SOW-021 | Risks lack owners/mitigations | ✅ | PMO: risk register static, no owners/mitigation |
| SOW-022 | Acceptance clause too generic | ✅ | same as SOW-007 finding |
| SOW-023 | Confidentiality too generic | ✅ | Legal: no duration/survival, CI undefined |
| SOW-024 | Change approval workflow missing | ✅ | PMO: change authority not named |
| SOW-025 | Log inventory lacks ownership | ❌ miss | — |
| SOW-026 | Log volume not documented | ❌ miss | — |
| SOW-027 | Shift allocation missing | 🟡 partial | Delivery: shared IR specialist has no coverage model |
| SOW-028 | FTE allocation missing | ✅ | Delivery: "confirms no FTE allocation" |
| SOW-029 | Contract metadata incomplete | ✅ | Delivery: approved with no signature dates |

## Misses — where to improve

All 4 strict misses are **Appendix-level / sub-section detail** the agents
summarize past:

1. **SOW-004 / SOW-006** — Scope agent flags "activities not detailed" broadly
   but doesn't decompose per-service (TI lifecycle, IR lifecycle phases).
   Prompt fix: instruct ScopeReviewer to check each listed service line for
   operational detail (NIST SP 800-61 IR phases, IOC lifecycle).
2. **SOW-025 / SOW-026** — no agent inspects Appendix tables (log inventory
   ownership, GB/EPS volume). Prompt fix: PMO/Delivery agents should audit
   appendix tables for owner/status/volume columns.

## False positives (~5 of 73)

- Rule engine keyword misses on sections that **do exist** in the document:
  "Deliverables Section Required", "Scope of Work Section Required",
  "Assumptions and Constraints Required", "Executive Summary Required"
  (doc has Sections 3, 4, 8 and a Purpose section). Rule detection is
  presence-by-keyword and the doc's headings didn't match.
- SecurityReviewer's "Missing Accessibility Standard" finding whose own text
  says accessibility is *not applicable* — should be suppressed, not emitted.

## Second measurement — 2026-07-23 (post Phase A of GUIDELINE_FEASIBILITY_PLAN)

After the Phase A fixes (section-presence matching normalization + synonyms,
self-negating-finding filter, 13 guideline §5 rules SOW-021..033, ScopeReviewer
per-service-line decomposition, DeliveryReviewer appendix-table audit — commits
`0ea801f..08caf22`), review rerun on the VPS:
review `f5ed3e51-ae33-4906-86d2-5c5a46f87663`, doc
`58f0f7ad-b4e1-48b3-af53-63b988d4e2ca`, **6/6 agents, 79 findings**
(60 agent + 18 rule + 1 ambiguous-language). Note: a first rerun attempt
(review `311a8e14`) lost ScopeReviewer to a double timeout (OpenRouter latency
variance) — measurement uses the 6/6 run.

| Metric | 2026-07-22 | 2026-07-23 |
|---|---|---|
| Recall (strict) | 21/29 = 72.4% | **27/29 = 93.1%** |
| Recall (lenient, incl. partials) | 25/29 = 86.2% | **29/29 = 100%** |
| Rule-engine false positives | 4 | **0** |
| Self-negating findings shipped | 1 | **0** |
| Effective precision | ≈93% (68/73) | **≈97% (77/79)** |

Movement on the previously-missed rows:

- SOW-004 (TI operational detail) ❌→✅ — ScopeReviewer per-service
  decomposition fired exactly as prompted (sources/enrichment/reporting).
- SOW-006 (IR lifecycle) ❌→✅ — flagged missing lifecycle phases, critical.
- SOW-025/026 (log inventory ownership/volume) ❌→✅ — DeliveryReviewer
  "Incomplete Inventory" on Appendix A cites missing owner/status/volume
  (GB/day, EPS) columns, satisfying both rows with one finding.
- SOW-005 (hunt methodology) 🟡→✅, SOW-027 (shift allocation) 🟡→✅,
  SOW-010 (service hours) stays ✅ with explicit coverage-hours language.

Still not strict matches (both were 🟡 partial at baseline and remain so):

- SOW-002 (infrastructure inventory incomplete) — only indirectly covered via
  the Section 12 "critical business applications may be refined" scope-creep
  finding; no agent flags the Customer Environment inventory itself.
- SOW-020 (open-items prioritization process) — PMO flags undefined decision
  authority (same as baseline); no finding explicitly demands a
  prioritization/approval workflow for the open-items list.

Remaining questionable findings (~2 of 79): SOW-008/SOW-009 word-count rules
fire on sections whose prose lives partly in tables — borderline, not clearly
wrong. The 4 heading-keyword FPs and the self-negating finding are gone.
*(Resolved 2026-07-24: measured directly — Scope of Services has 56 words,
Deliverables 32, vs 100/150 thresholds, and DOCX table text already counts
toward section content. These firings are correct thin-detail detection —
the ground truth itself flags the same thinness (SOW-003/SOW-007). Not FPs;
no change made.)*

**Phase A exit criteria: PASS** (target was 4 FPs gone + strict recall ≥79%;
measured 0 FPs, 93.1%). Already past the >90% strict-recall launch target for
this document; next gate is after Phase C.

## Third measurement — 2026-07-23 (second session): last 2 partials closed

After the ScopeReviewer #9 (environment inventory) and PMOReviewer #7
(open-items governance) prompt additions, a fresh 6/6 production run
(doc `04fe42e5`, 81 findings, 147.2s, audit git_sha `8f9370a`):

- **SOW-002 🟡→✅** — ScopeReviewer "Incomplete Environment Inventory" ×2:
  no endpoint/server/subscription counts, and critical business
  applications explicitly deferred.
- **SOW-020 🟡→✅** — PMOReviewer "Unmanaged Open Items": Section 12's
  eight deferred decisions have no owner, priority, or resolution process.

**Strict recall on this document: 29/29 = 100%.** All 29 ground-truth rows
now have direct matches. Caveat unchanged: one document, one ground-truth
set — the ≥10-doc labeled corpus is still the real launch gate.

Same session also validated: RFP pipeline (RFP Sample - 2RFP.pdf →
detected RFP, 13 RFP-rule violations, 0 SOW rules, 40 real agent findings
across all 6 reviewers, 30.4s) — model routing works beyond the single
SOW test doc. Confidence calibration snapshot: avg confidence 87.7 vs
≈97% precision → ≈9-point gap, now UNDER-confident (was 17.95%
over-confident 2026-07-18); no prompt tuning warranted from a
single-document sample.

## Conflict detector — subtle-conflict validation (2026-07-24)

`docs/sample/SOW_Sample/Subtle_Conflicts_Test.docx` (checked in as the
regression doc) plants 5 realistic clause-vs-clause tensions, no numeric
side-by-sides. Live prod run: **4/4 true contradictions caught, 0 false
conflicts** — termination-for-convenience vs 100% exit charge, interest
accruing 15 days before the Net-45 due date, liability cap vs
"without limitation" indemnity, IP vesting vs retained-ownership license —
each with correct legal reasoning in the description. The 5th planted item
(England & Wales law + Singapore courts) is deliberately NOT a
contradiction (law/forum split is unusual but coherent); the detector
correctly declined it and LegalReviewer flagged it as "Ambiguous Legal
Language, major" instead. Conflict-scan quality no longer "unproven";
prompt unchanged.

Also 2026-07-24: measured 4-model accuracy comparison + fallback reorder +
parse-failure chain advance — see docs/planning/AI_MODEL_ROUTING.md
"Measured accuracy comparison". Evidence anchoring (fuzzy matching):
38/62 agent findings now carry section+page vs ~2 before.

## Phase C measurement note — 2026-07-23 (later same session)

Phase C (broken-reference detector REF-SCAN + conflict LLM scan
CONFLICT-SCAN, commits `ec9f3b8`+`a0f13e4`) deployed and exercised in 4
consecutive live prod reviews:

- **Reference scan: 0 dangling references — correct.** SOC_SOW_Testing.docx's
  internal references (Appendix A, Appendix B) all resolve to real headings;
  the dangling-reference capability is proven by 10 unit tests
  (`test_references.py`), including the guideline §4 scenario (missing
  Appendix C fires `evidence_type='reference'` with the referring sentence).
- **Conflict scan: 0 contradictions in ~37-42s, no failures.** The test doc
  contains deliberate *ambiguities* but arguably no hard *contradictions*,
  so 0 is plausible — quality on a genuinely conflicting document is
  unproven. Parked per the plan's abort criterion; revisit with a synthetic
  conflicting doc before trusting it.
- **Persona recall: confirmed unchanged.** 4 rerun attempts 20:42-21:04 UTC
  each lost a different agent to a 60s+120s double timeout (OpenRouter
  latency degradation at that hour — lesson: don't measure during degraded
  provider latency). A clean **6/6 run at 21:08 UTC** (review for doc
  `2d2dc7ba`, 74 findings) reproduces the Phase A pattern: all 4
  previously-missed rows (TI operational detail, IR lifecycle, log-inventory
  owner/volume) fire again; the 93.1% strict-recall figure stands post-C.

**Phase C exit criteria: PASS** (suite green incl. reference/conflict tests;
detectors live in prod; §4 scenario covered by regression tests; 6/6
confirmation run clean).

## Conflict detector validated — 2026-07-23 (second session)

The "quality unproven" caveat above is now resolved. A synthetic SOW with
3 planted hard contradictions
(`docs/sample/SOW_Sample/Synthetic_Conflicts_Test.docx`: 12- vs 24-month
term, 99.9% vs 99.5% availability, Sept vs Oct start date) was run through
the live production pipeline: **3/3 caught** (CONFLICT-1..3), each with
both verbatim quotes, sensible severity (term = critical), and
`evidence_type='conflict'`. Zero false conflicts — the detector even noted
the $240,000 figure was *consistent* with the 24-month reading instead of
flagging it. Scan cost: 24.3s of an 80.8s review.

## Phase D verification — 2026-07-23

Same 21:08 UTC review (first post-migration-028): `audit_meta` populated in
the API response — parsed-text SHA-256, `models_used` = z-ai/glm-5.2 for
all 6 agents (actual per-agent capture, not config echo),
`rules_version` 2026-07-23.1, UTC timestamp. `app_git_sha` is "unknown"
until the VPS compose passes a GIT_SHA env/build arg — cosmetic, noted.
**Phase D exit criteria: PASS.**

## Next actions (not done in this session)

- Tighten the 4 rule-engine section detectors' heading synonyms.
- Suppress "not applicable" self-negating agent findings before persistence.
- Prompt additions for per-service operational detail + appendix table audits.
- Re-run this measurement after prompt changes to track recall movement
  (target per launch criteria: track toward >90% strict recall).
