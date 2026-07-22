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

## Next actions (not done in this session)

- Tighten the 4 rule-engine section detectors' heading synonyms.
- Suppress "not applicable" self-negating agent findings before persistence.
- Prompt additions for per-service operational detail + appendix table audits.
- Re-run this measurement after prompt changes to track recall movement
  (target per launch criteria: track toward >90% strict recall).
