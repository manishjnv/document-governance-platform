# Plan: ScopeWise add-on for Microsoft Sentinel Content Hub

**Date:** 2026-08-19 · **Status:** planned, not started
**Market research behind this plan:** `SENTINEL_CONTENT_HUB_EVALUATION.md`
(read it first — it explains why the feature set below is what it is).

## Goal

A **free** Sentinel Content Hub solution ("ScopeWise MITRE Coverage
Assessment") that gives a SOC an honest in-tenant view of their detection
coverage — deliberately better than Sentinel's native MITRE blade on its
documented weaknesses, deliberately shallower than the ScopeWise SaaS — and
funnels them to the full assessment. Solution templates are not
transactable, so free-by-construction is not a choice, it's the mechanism.
Revenue stays on ScopeWise SaaS billing (Security Store transactable
listing is a later option, Tier 3).

## Feature spec

### Tier 1 — ships in the add-on (all in-tenant, viewer's own RBAC, no credentials to ScopeWise)

| # | Feature | Beats | How |
|---|---------|-------|-----|
| 1 | **Honest coverage workbook** — heatmap of *enabled* analytics rules only; rules that have **never fired** or not fired in 90d flagged (join `SecurityAlert` history); disabled rules shown as explicit risk; no "simulated" inflation | The native blade's #1 criticism: coverage ≠ detection | Workbook ARM datasource enumerates `alertRules` (viewer RBAC); KQL joins `SecurityAlert` by `AlertName`/rule id |
| 2 | **ATT&CK v19.1** technique/sub-technique matrix with sub-technique rollup | Blade is stuck on v18 | Bake technique metadata from our `attack.json` into the workbook as a static JSON grid (build-time generated, not fetched) |
| 3 | **Telemetry reality check** — techniques whose required tables/connectors are absent ("you have a T1110 rule but no sign-in logs") | Blade has no telemetry awareness | Static mapping generated from `apps/api/app/mitre/ranking.py::_LOG_SOURCE_RULES`; KQL `union isfuzzy` table-existence probes |
| 4 | **Top-5 gaps that matter** — prevalence-weighted teaser of the ranked roadmap | Blade ranks nothing | Static prevalence weights exported from our ranking data into the workbook; NOT the threat-actor engine |
| 5 | **Funnel** — "what the full assessment adds" panel + guided service-principal setup doc (Sentinel Reader role, 5 IDs) linking to scopewise.assessiq.in | — | Markdown steps in the workbook + solution README |

### Explicitly NOT in the add-on (paid SaaS, already built)

Keyword+AI tagging of untagged rules, applicability filtering,
threat-actor-weighted ranking + full roadmap, PPTX/PDF/XLSX reports,
trend + compare, tool-attestation overlay, Splunk/multi-SIEM, scheduled
pulls. The workbook's funnel panel names these explicitly.

### Tier 3 backlog (separate decisions, not this plan; rough priority order)

1. **Rule-health signals in the SaaS score** — never-fired / stale / noisy
   rules via `SecurityAlert` history (needs a wider-than-Reader role:
   optional, graceful-degrade). This is also the honest core of "detection
   effectiveness": passive alert-fired validation gives most of the value
   of purple-team simulation with none of its liability (see item 6).
2. **Detection-as-code** — per-gap KQL starter library first; optionally
   grow into full generated analytics rule + test case per gap. Strong
   differentiator but a real content-maintenance commitment — start with
   starters, expand only on customer pull.
3. **Security Copilot agent / in-product "ask why"** — evidence-based Q&A
   over an assessment ("why is Credential Access 52%?") reusing the
   deterministic why-phrases already in the technique drawer; the Security
   Store agent listing is the distribution surface.
4. **Defender XDR coverage view** — the native blade's other blind spot;
   the tool-attestation overlay already approximates it.
5. **Composite "SOC detection maturity" score** — see the guard in
   `SENTINEL_CONTENT_HUB_EVALUATION.md` §"worth incorporating": only 3 of
   the 6 proposed dimensions have real data today; do not ship a composite
   with fake inputs. Requires a `SCORING_METHODOLOGY.md` decision first.
6. **Purple-team / attack-simulation validation** (execute technique →
   did the alert fire?) — far backlog, V3-at-earliest. Requires running
   attack tooling inside customer environments: heavy liability, support
   and security surface, and it is the core product of funded vendors
   (Picus, AttackIQ, SnapAttack). Revisit only if item 1's passive
   validation proves insufficient AND a customer is paying for it.

## Commercial model (decided direction; prices are business decisions)

The ladder: **free Content Hub add-on → productized assessment (first
revenue) → continuous-monitoring subscription (recurring revenue)**.

- **First revenue = productized assessment, not subscriptions.** One
  full-scope assessment engagement (report + roadmap + walkthrough, the
  SaaS does the heavy lifting) is a realistic first sale; chasing many
  small monthly subscriptions from a cold start is not. Partner Center
  also supports **consulting-services listings** (assessments, workshops)
  — a separate, simpler listing path than the Sentinel solution PR and
  worth filing alongside it.
- **Subscriptions** (continuous monitoring: scheduled pulls + trend +
  reports — already built) start on ScopeWise's own billing: zero
  marketplace fee, zero integration work. A **transactable marketplace
  SaaS offer** (flat/per-user/metered, ~3% Microsoft fee) is a later
  upgrade for co-sell visibility — note it requires implementing
  Microsoft's SaaS fulfillment + metering APIs (landing page, webhook,
  license activation), which is real engineering, not just a listing.
- Tier prices (starter/pro/enterprise) are deliberately NOT fixed in this
  plan — decide before the Phase C listing goes live.

## Build phases

### Phase A — Workbook v0 (pure engineering, no Microsoft accounts needed)

The workbook is testable standalone: paste JSON into any Sentinel
workspace via Workbooks → New → Advanced Editor. Content Hub packaging
comes later; nothing blocks starting today.

1. New repo folder `marketplace/sentinel/` — workbook JSON + a small
   `scripts/generate_workbook_data.py` that exports ATT&CK v19.1 technique
   metadata + log-source mapping + prevalence weights from the existing
   Python module into the workbook's static JSON grids (single source of
   truth stays `apps/api/app/mitre/`; regenerate on ATT&CK upgrades).
2. Implement features 1–5 as workbook tabs. Hardest part: the ARM
   datasource pagination for `alertRules` and the SecurityAlert join
   (alert-to-rule linkage is by `AlertName` — document the known fuzziness).
3. Test against a dev Sentinel workspace (see prerequisites) and at least
   one real tenant (e.g. the existing customer workspace, read-only).

**Exit criteria:** workbook imports clean in a fresh workspace, all tabs
render with 0 rules (empty workspace) and with a real rule set, no
hardcoded workspace/tenant IDs.

### Phase B — Package as a Sentinel solution

1. Repo structure per `Azure/Azure-Sentinel` `Solutions/README.md`:
   `Solutions/ScopeWise/` with `Workbooks/`, `Package/mainTemplate.json`,
   `Package/createUiDefinition.json`, `SolutionMetadata.json`, `README.md`,
   `ReleaseNotes.md`. Use Microsoft's packaging tool
   (`Tools/Create-Azure-Sentinel-Solution/` V3) — do not hand-write
   mainTemplate.
2. Validate with the Sentinel VS Code extension / repo validation scripts;
   test-install the packaged solution into the dev workspace.

### Phase C — Microsoft process (user-owned, long pole — start in parallel with Phase A)

1. **Microsoft Cloud Partner Program enrollment + Partner Center account
   + Publisher ID** — company details, tax/bank forms; days-to-weeks of
   elapsed time. Microsoft recommends starting before the code is done.
2. PR to `Azure/Azure-Sentinel` GitHub repo; respond to Microsoft review
   (expect weeks and at least one revision round).
3. Partner Center: Azure Application offer, **Solution template** plan
   (free). Listing assets: description, categories, privacy policy URL,
   support contact, screenshots.
4. Private preview limited to named Azure subscription IDs (~4 weeks,
   2–3 friendly customers), then go live.

### Ongoing obligations (price these in before Phase C)

Partner-supported = ScopeWise is the support desk. Every update repeats
the PR + review cycle. ATT&CK version upgrades require regenerating the
static grids and republishing.

## Prerequisites / open items

- **Dev Sentinel workspace**: an Azure subscription with a near-empty Log
  Analytics workspace + Sentinel enabled (≈ zero ingestion cost; 31-day
  Sentinel trial available). Needed from Phase A step 3.
- **Partner Center enrollment** (user action, Phase C.1) — the elapsed-time
  long pole; start early.
- Privacy policy + support page on scopewise.assessiq.in (Partner Center
  listing requirements).

## Effort estimate (engineering only, excludes Microsoft elapsed time)

- Phase A: ~2–4 focused sessions (workbook KQL/ARM iteration is fiddly).
- Phase B: ~1 session with the packaging tool.
- Phase C engineering share (PR fixes, listing assets): ~1–2 sessions
  spread over the review weeks.
