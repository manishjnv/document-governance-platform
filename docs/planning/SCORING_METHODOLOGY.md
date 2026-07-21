# Scoring Methodology — Overall Score, Risk Level, and Finding Severity

**Purpose of this doc:** answer "why should I trust this number?" for
customers and for ourselves. There is no single industry body that
publishes an official "SOW/RFP risk score" the way CVSS does for software
vulnerabilities — but the pieces of our methodology are each grounded in a
named, citable framework, not invented from scratch. This doc says which
framework backs which part, and is honest about the one part that still
needs external validation (finding severity calibration).

---

## Overall Score (0-100, higher is better)

**What it measures:** how complete and well-specified the document is
across 7 categories (completeness, clarity, consistency, commercial,
delivery, operations, security), weighted and combined into one number.

**Framework grounding:** the category structure (deliverables, acceptance
criteria, scope boundaries, timeline, payment terms) follows the **PMBOK
Guide (Project Management Institute)** Scope Management knowledge area —
the standard reference for what a complete statement of work should
contain. This isn't a proprietary checklist; it's the same structure PMs
are trained against.

**Implementation:** `apps/api/app/scoring/algorithm.py`
`DocumentScorer._calculate_overall_score` — weighted average of the 7
category scores, weights in `DocumentScorer.WEIGHTS` (per-org
customizable, `app/admin/customization.py` `get_scoring_weights`).

**2026-07-21 redesign — category scores were zeroing out on real
documents:** two stacked flat-sum penalty mechanisms guaranteed that
every completed production review stored all 7 categories and
`overall_score` as exactly 0.00 (confirmed against prod data — 31-70
findings per review is normal, and both sums grew linearly with finding
count against a fixed 100-point budget). Fixed in two steps, verified
against a real 70-finding production review:

1. **Per-category penalties now saturate instead of cliff-clamping.**
   Each category's own keyword-matched penalty sum maps to a score via
   `100 * e^(-k * raw_sum)` (`_saturating_category_score`,
   `CATEGORY_SATURATION_K = 0.017`) instead of linear subtraction
   clamped at 0. Calibrated so one critical-severity match (raw 25)
   lands a category at ~65 (yellow) and a heavily-matched category
   approaches 0 asymptotically — a category with 12 matched findings
   now reads visibly differently from one with 30, instead of both
   flatlining at 0. The k differs from `RISK_SATURATION_K` because the
   input scale differs (one category's own matches vs. a whole review's
   raw sum) — see the constant's in-code comment.
2. **The cross-category "general severity penalty" was retired
   entirely** (not capped — an intermediate capped version still zeroed
   everything once stacked on the per-category curve). It double-counted
   the same severity signal each category's own penalty already carries,
   and overall severity/volume is already captured — separately,
   correctly — by `risk_score`. Each category's score is now driven only
   by its own matched findings, which is also easier to explain to a
   customer: "commercial is 11 because these 16 commercial findings
   exist," with no invisible cross-category adjustment.

---

## Risk Level (0-100, higher is worse)

**What it measures:** how much exposure this document creates if signed
as-is — combining *how severe* the issues are and *how many* there are.

**Framework grounding:** this is a **likelihood × impact** risk model, the
standard structure used in **ISO 31000** (general risk management) and
**NIST SP 800-30** (security/compliance risk assessment). Severity maps to
impact; finding volume is the likelihood-adjacent signal. We combine them
with a saturating curve rather than a flat sum — see below for why that
matters.

### The 2026-07-19 redesign (and why)

The original model was `critical_count × 15 + major_count × 10 +
total_findings`, capped at 100. In practice, any real SOW/RFP review (6
agents + rule engine, typically 30-40+ findings) reached the 100 cap
almost immediately — every document we tested showed "100%, High," with
no way to tell a moderately risky document from a catastrophic one. A
capped linear sum has no headroom once you cross the cap; two very
different documents become visually identical.

**New model:**

```
raw_sum = sum(RISK_SEVERITY_WEIGHTS[finding.severity] for finding in all_findings)
risk_score = 100 * (1 - e^(-k * raw_sum))
```

This is a standard exponential saturation curve: it climbs quickly at
first, then slows down, asymptotically approaching 100 without ever
truly capping — a document with 15 critical findings still reads
meaningfully worse than one with 5, instead of both pinning at the
ceiling.

`RISK_SEVERITY_WEIGHTS` and the saturation constant `k` are calibrated
against real review volume (30-400 raw points is typical for an actual
SOW/RFP with 6 agents + rule engine) — see
`DocumentScorer.RISK_SATURATION_K` for the current value and the
calibration notes in code.

**Per-org tuning:** `RISK_SEVERITY_WEIGHTS` is overridable per-org via
`org_risk_weights` (migration `022_review_risk_model.sql`,
`app/admin/customization.py` `get_risk_weights`/`set_risk_weight`) — same
pattern as the existing scoring-weight customization. No admin UI ships
for this yet; the plumbing exists so one can be added without a schema
change.

### Risk by Area (breakdown)

The same risk score is also computed **per axis** — Scope, Delivery,
Commercial, Security, Governance, Legal, Compliance — using the same
saturating formula, so a customer sees *which kind* of risk is driving
the number instead of one blended figure. Axis = the reviewing agent
(`ScopeReviewer` → Scope, `LegalReviewer` → Legal, etc.); rule-engine
findings (no agent) fall under "Compliance."

**Why these specific axes, and why Legal checks liability/IP/termination/
indemnification specifically:** **IACCM / World Commerce & Contracting**
publishes annual research on the "Most Negotiated Terms" in commercial
contracts. Liability caps, IP ownership, termination rights, and
indemnification consistently rank at the top. That's the real, citable
reason `LegalReviewer` targets those specific clauses — not an arbitrary
choice.

**Why the RFP rule set looks the way it does:** the required
evaluation-criteria disclosure, vendor-qualification, and submission-format
checks mirror **FAR Part 15** (U.S. Federal Acquisition Regulation),
which mandates structured, weighted evaluation-criteria disclosure in
government RFPs — the same discipline we check for in any RFP.

**Implementation:** `DocumentScorer._calculate_risk_breakdown`,
`Review.risk_breakdown` (JSONB column, migration `022`).

---

## Finding Severity (critical / major / medium / low / info)

**What it measures:** how serious the reviewing agent (or rule) judged a
single finding to be.

**Honest status: this is the weakest-grounded part of the system today.**
Severity is assigned by LLM judgment with no external validation yet —
tracked as an open item in
`docs/planning/LEGAL_SEVERITY_CALIBRATION.md`, which needs a legal SME to
compare the system's severity judgments against real risk assessment
before it can be trusted at face value. Until that sign-off lands, treat
severity labels as a reasonable first pass, not a certified rating.

The risk-model weights (`RISK_SEVERITY_WEIGHTS`) and the finding-severity
scoring penalties (`_SPECIFIC_SEVERITY_PENALTY` /
`_GENERAL_SEVERITY_PENALTY`) intentionally use the same relative ordering
(critical > major > medium > low) so severity means the same thing
everywhere in the product, even while the underlying severity judgment
itself is still pending calibration.

---

## What this doc is NOT claiming

- Not a claim that this is *the* industry-standard way to score a SOW/RFP
  — no such single standard exists.
- Not a claim that finding severity is independently validated yet — see
  above.
- Not a claim that the specific numeric weights are "correct" in an
  absolute sense — they're a defensible, documented starting point,
  openly tunable per-org, not a black box.

The goal is that every number on the results page can be traced back to
either a named framework or an explicit, stated assumption — never an
unexplained black box.
