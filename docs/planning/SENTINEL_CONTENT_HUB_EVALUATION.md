# Evaluation: Microsoft Sentinel Content Hub / Marketplace solution for ScopeWise MITRE

**Date:** 2026-08-19 · **Status:** evaluation + market research, nothing built
**Update 2026-08-19 (later same day):** market research added (§ Market research
below) — stance refined from "defer" to "free funnel add-on with the Tier-1
feature set, when GTM investment is approved". Build plan:
`SENTINEL_CONTENT_HUB_ADDON_PLAN.md` (kickoff:
`docs/phases/prompts/SENTINEL_CONTENT_HUB_ADDON_PROMPT.md`).
**Input:** external proposal to publish a partner-authored Sentinel Solution
(data connector + content) via the Azure/Azure-Sentinel GitHub repo, Partner
Center, and Content Hub, plus a "Sentinel-native MITRE assessment" product
sketch.

## Verdict in one paragraph

The proposal's *product* section is ~80% a description of what ScopeWise's
MITRE module already does in production. The genuinely new part is the
*distribution channel* (Content Hub / Azure Marketplace listing) and a
*Sentinel-native surface* (workbook inside the customer's tenant). The channel
is a Go-To-Market project — Microsoft partner enrollment, solution packaging,
GitHub PR review, certification, ~4-week preview, and a **permanent
partner-supported maintenance obligation** — not primarily an engineering one.
Recommendation: **don't build it now**; revisit when there's evidence
customers are being lost for lack of a marketplace presence. A few product
ideas from the proposal *are* worth incorporating into ScopeWise itself
(listed at the end).

## What the proposal asks for vs. what already exists

| Proposal item | ScopeWise status |
|---|---|
| Rules → ATT&CK mapping | ✅ tagging ladder (manual / customer / keyword / AI), `apps/api/app/mitre/` |
| Technique + sub-technique coverage, tactic rollups | ✅ coverage engine + heatmap + drawer |
| Detection gaps, priority gaps | ✅ ranking + Gaps/Roadmap tab (threat-actor weighted) |
| Telemetry / data coverage | ✅ log-source coverage + Sentinel data-connector auto-import (A7) |
| Recommendations + starter queries | ✅ per-gap recommendations; KQL starters in XLSX |
| Executive + technical reports | ✅ PPTX (18 slides), PDF, XLSX |
| Continuous assessment + trend | ✅ scheduled pulls (13c), compare endpoint, per-connection trend (2026-08-19) |
| Rule health | ◐ enabled/disabled handled; `last_triggered: never` caveat in XLSX |
| 30/60/90-day improvement plan | ◐ roadmap exists but isn't time-phased |
| Multi-factor maturity score | ❌ deliberate two-number design (strict/weighted) instead — see below |
| Detection *quality* / noise scoring | ❌ no data source (needs incident/alert history, a bigger permission ask than Sentinel Reader) |
| "Deterministic first, AI as assistant" | ✅ already the module's design principle |

## Why the Content Hub route is a poor architectural fit today

Content Hub solutions deliver content **into** Sentinel: data connectors that
ingest into Log Analytics, analytics rules, workbooks, playbooks. ScopeWise's
model is the reverse — it **pulls from** Sentinel (read-only service
principal → `alertRules` API) into a SaaS that runs the assessment. There is
no solution type for "a SaaS reads your rules"; forcing one means building
things ScopeWise doesn't need:

- A data connector ingesting ScopeWise results into customer tables (Logs
  Ingestion API + DCRs) duplicates the SaaS dashboard inside Sentinel — real
  engineering, marginal value.
- Shipping detection rules/hunting queries as content is a different product
  (a content library), and undercuts the assessment's vendor-neutral stance.
- It's Sentinel-only, weakening the multi-SIEM story (Splunk already works;
  same canonical-CSV contract would extend to Elastic/QRadar).

**Cheapest credible version if/when pursued:** a *workbook-only* solution — a
ScopeWise-branded workbook that enumerates the tenant's own analytics rules
via the workbook ARM data source (viewer's own RBAC, no credentials to us) and
renders a basic in-tenant ATT&CK heatmap of *explicitly tagged* rules only,
with a "full assessment (keyword+AI mapping, applicability, reports, trend) at
scopewise.assessiq.in" link. That is a teaser/funnel, deliberately inferior to
the SaaS. Process cost is unchanged (Partner Center, GitHub PR, certification)
but code cost is one workbook JSON.

**Process facts to price in:** Microsoft Cloud Partner Program + Partner
Center enrollment; solution package (`mainTemplate.json`,
`createUiDefinition.json`, `SolutionMetadata.json`) submitted by PR to
`Azure/Azure-Sentinel`; Microsoft review cycles measured in weeks; recommended
~4-week private preview; "Partner-supported" label = we are the support desk
forever; every solution update repeats the review cycle.

## What IS worth incorporating into ScopeWise (no marketplace needed)

1. **Time-phase the roadmap (30/60/90 days).** Presentation-only change to
   the existing ranked roadmap in UI + reports. Small, high perceived value.
2. **Composite "detection maturity" score — decide, don't drift.** The
   proposal's weighted blend (coverage / telemetry / quality / health)
   conflicts with the deliberate strict+weighted two-number invariant
   (re-affirmed 2026-08-19 when tool attestation was kept out of the main
   score). Only 3 of its 6 inputs have real data today (technique coverage,
   telemetry availability, rule health) — a composite built on fake inputs is
   the misleading-single-number problem the current design avoids. If ever
   built: update `SCORING_METHODOLOGY.md` first, use the org-tunable
   customization pattern, and label it separately from coverage.
3. **Alert-path second opinion (future):** detection *quality* needs
   SecurityAlert/SecurityIncident history — note as the feature that would
   justify asking customers for a wider role than Sentinel Reader. Not now.
4. **Free-tier teaser funnel** (basic heatmap free, reports/trend paid) — a
   business decision, no engineering blocker; the module already gates by org.

## Explicitly rejected

- Building/publishing the full Sentinel Solution now (GTM project without a
  customer signal; permanent support obligation).
- Push-based ingestion of ScopeWise output into customer Log Analytics.
- Shipping our own detection-rule content pack.

---

## Market research (2026-08-19) — what exists, and the add-on feature set

### Landscape

**Free / native (the floor any add-on must beat):**

- Sentinel's built-in **MITRE ATT&CK coverage blade** — heatmap of active
  analytics rules plus optional "simulated" coverage (rule templates,
  hunting queries). Documented weaknesses the community repeatedly calls
  out: coverage ≠ detection (a rule existing says nothing about it being
  enabled, tuned, or ever firing), simulated coverage inflates the map,
  Sentinel-only (no Defender XDR view), and it tracks an **outdated ATT&CK
  version (v18)** while ScopeWise is on v19.1.
- Microsoft's own **MITREAttack workbook** (Azure-Sentinel repo) mapping
  out-of-the-box detections, plus free community tooling (PowerShell rule
  exporters, GitHub "Sentinel-Assessment-Tool", Medium dashboards). A plain
  heatmap workbook is a **commodity** — worthless as a paid differentiator.

**Enterprise detection-posture platforms (the ceiling):**
CardinalOps ("detection posture management" / agentic detection
engineering, API-driven, multi-SIEM incl. Sentinel + Splunk), SOC Prime
(Sigma content marketplace delivering to 20+ SIEMs), SnapAttack. These are
enterprise-priced, continuous, and strong on rule *quality* and content
delivery — but not distributed as Content Hub solutions and priced far
above ScopeWise's segment.

**New 2026 surface:** the **Microsoft Security Store** (Defender portal) —
partner-built Security Copilot agents, Sentinel Data Lake notebook jobs,
and **transactable SaaS listings** (MISA-qualified integrations). This is
where monetization actually happens; classic **Sentinel solution templates
are NOT transactable** — a Content Hub listing is free by construction.

### The gap ScopeWise fits

Between the free-but-shallow native blade and the enterprise-priced posture
platforms: an affordable, assessment-grade product with consultant-quality
reporting. That is what the SaaS already is. The add-on's only job is to be
the **free in-tenant hook** that demonstrates it.

### Recommended feature set

**Tier 1 — the free Content Hub add-on (workbook-centric solution, no
credentials to us, viewer's own RBAC):**

1. **"Honest coverage" workbook** — the hook. Heatmap of *enabled* rules
   only, cross-joined with `SecurityAlert` history to flag rules that have
   **never fired** or gone stale, disabled rules shown as explicit risk,
   simulated inflation excluded. Directly answers the blade's most-cited
   criticism; nothing free does this today.
2. **Current ATT&CK version (v19.1)** + sub-technique rollup view — beats
   the blade's v18 with zero engineering (our attack.json already exists).
3. **Telemetry reality check** — tables/data connectors present vs.
   techniques that need them (reuse `ranking._LOG_SOURCE_RULES` as a static
   KQL mapping). "You have a T1110 rule but no sign-in logs" is a gap class
   the blade can't see.
4. **Top-5 gaps that matter** — a taste of the ranked roadmap (static
   prevalence weighting in KQL, not the full threat-actor engine).
5. **Deployment doc + "get the full assessment" funnel** — guided
   service-principal setup for connecting to ScopeWise.

**Tier 2 — the paid side (already built; listed as a separate transactable
SaaS offer / Security Store listing, or own billing):** full tagging ladder
(keyword + AI for the untagged majority the blade ignores), applicability
filtering, threat-actor-weighted ranking + roadmap, exec PPTX/PDF/XLSX,
trend + compare, tool-attestation overlay, multi-SIEM (Splunk), scheduled
pulls. The add-on must *name* these as what the free tier is missing.

**Tier 3 — build-new backlog surfaced by the research (priority order):**

1. **Rule-health in the SaaS score** (never-fired/stale via SecurityAlert
   history) — the CardinalOps differentiator; needs the wider-than-Reader
   permission ask, so make it optional-role, graceful-degrade.
2. **Per-gap KQL starter library** — extend the existing XLSX starters into
   curated per-technique templates (SOC Prime-lite; watch the maintenance
   burden, keep it starters-not-content-pack).
3. **Security Copilot agent listing** — "ask your assessment" agent over
   the ScopeWise API; the Security Store is far less crowded than Content
   Hub and is the transactable surface. Worth a spike after the workbook.
4. **Defender XDR coverage view** — the blade's other blind spot; the
   tool-attestation overlay already approximates this, formalize later.

### Commercial structure (confirmed)

Solution template = free listing only → the add-on is a funnel by design.
Revenue path: ScopeWise SaaS billing as today, optionally a transactable
SaaS offer in the marketplace/Security Store later (adds Microsoft's fee
but co-sell visibility). Do not build a managed-app plan just to charge for
a workbook.

### Sources

- learn.microsoft.com/azure/sentinel/mitre-coverage (blade capabilities/version)
- techcommunity.microsoft.com — "Joint forces: MS Sentinel and the MITRE framework"; "AI-Powered MITRE ATT&CK Tagging for SOC Optimization"; "What's new in Microsoft Sentinel: February 2026"
- practical365.com — "Practical Sentinel: The Value of MITRE ATT&CK" (blade limitations)
- github.com/Azure/Azure-Sentinel — MITREAttack.json workbook, Solutions/README (packaging)
- learn.microsoft.com/security/store/partners — Security Store publishing
- learn.microsoft.com/partner-center — solution-template non-transactability, SaaS offer plans
- cardinalops.com, socprime.com materials (competitor positioning)
