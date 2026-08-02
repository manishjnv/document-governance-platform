# Claude Review Prompt – MITRE ATT&CK Assessment Data Collection Review

**Revised 2026-08-03 (plan phase A1)** — rewritten so a fresh consultant
session can run this standalone, with no repo access, against the CURRENT
build. If you're reading this to review the module, everything you need
about what data it collects and how is embedded below; you don't need to
open the codebase to form an opinion.

## Role
Act as a senior MITRE ATT&CK consultant, SOC architect, SIEM engineer, threat hunter, detection engineer, and Big-4 cybersecurity assessor.

Your objective is to review the data-collection module of my MITRE ATT&CK assessment application and determine whether it collects the minimum amount of information required to perform a comprehensive, accurate, and auditable assessment while keeping the burden on the customer as low as possible.

Do not redesign the entire application from scratch.

Your task is to critically review the existing design and identify:
- Missing information
- Unnecessary information
- Duplicate information
- Overly technical questions
- Questions customers are unlikely to answer
- Data that could be imported automatically
- Better methods of collecting evidence
- Improvements to the user experience
- Improvements to ATT&CK mapping accuracy

## Hard invariants — do not recommend violating these

These are locked product decisions, not open questions. A recommendation
that violates one of these will be rejected regardless of how well-reasoned
it is — critique within these bounds, not against them.

1. **Numbers are deterministic.** Every percentage, count, state, and N/A
   reason is computed in pure Python against a pinned ATT&CK dataset. The
   LLM's ONLY two jobs are (a) tagging use cases the customer didn't tag
   and the deterministic keyword pre-pass couldn't, and (b) narrative
   prose that may rephrase computed facts but never invents or adjusts a
   number.
2. **No raw-log ingestion, ever.** The product never asks for or accepts
   log samples/exports. It reasons only from metadata the customer
   already has on hand (rule inventories, asset lists, log-source names).
3. **No field-level verification claims.** Because raw logs are never
   ingested, the product can never claim "your source has/lacks field X".
   The honesty boundary is always framed as a question back to the
   customer: "verify that field X is present", never "field X is
   missing" or "field X is confirmed present".
4. **Module isolation.** This is a self-contained module; do not propose
   folding it into, or sharing state/orchestration with, the main
   document-review pipeline.
5. **Don't redesign.** Propose additions, removals, and rewording within
   the existing wizard → upload → run → report shape, not a new shape.

## Current field inventory (verbatim from the running build)

### Intake wizard (JSON, one-time per assessment)

| Field | Required? | Consumed by |
| --- | --- | --- |
| `industry` | optional, ≤200 chars | narrative LLM prompt + threat-profile lookup (gap-ordering only) |
| `region` | optional, ≤200 chars | narrative LLM prompt + region-based threat weighting (gap-ordering only) |
| `threat_actors` | optional, ≤10, validated against a curated catalog | threat-informed gap weighting (ordering only, never coverage %) |
| `count_disabled_as_coverage` | optional bool, default false | coverage engine: whether a disabled-but-qualifying rule counts as covered |
| `exclusions[]` (`target` + mandatory `reason`) | optional list | applicability engine: forces techniques/platforms/domains to N/A with the reason attributed "customer-declared" |
| `project_name`, `scope_label`, `prepared_by`, `purpose_note` | all optional, ≤200/≤500 chars | display-only: report cover page, XLSX summary sheet — never sent to any engine or LLM |

### Use-case / detection-rule dump (xlsx/xls/csv — required)

Header row is auto-detected (scanned across the first 10 rows); columns
matched by a synonym table (~90 real-world header variants seen across
Splunk ES, Sentinel, Elastic, QRadar, and generic exports):

| Field | Required? | Synonym examples | Consumed by |
| --- | --- | --- | --- |
| Name | required (no detectable name column → hard reject with template guidance) | "use case", "rule name", "detection name", "analytic rule", "correlation search" | display only |
| Technique tags | optional per row | "technique", "ttp", "mitre id", "att&ck id", "mapped technique" | coverage engine directly if present; else keyword pre-pass, else AI tagging |
| Detection logic | optional | "logic", "kql", "spl", "sigma rule", "detection query" | AI tagging context; XLSX/PDF "why" text |
| Description | optional | "description", "summary", "objective" | AI tagging context |
| Enabled/status | optional, unrecognizable → treated as enabled + assumption | "status", "active", "deployment status" | coverage engine (disabled rules only count under the org toggle) |
| Log source | optional | "log source", "data source", "sourcetype", "telemetry" | gap-ranking feasibility bridge; Phase A3 telemetry cross-check |

PDF/DOCX dumps are accepted via AI text extraction (lower fidelity, always
flagged in assumptions), capped at 40 chunks (~360KB), <200 extractable
chars is a hard reject.

### Environment workbook (xlsx/xls — optional; no workbook = no N/A filtering except customer exclusions, plus a loud "coverage is a lower bound" assumption)

Four sheets, located by name synonym; any missing sheet is tolerated
(assumption, never an error):

| Sheet | Purpose | Consumed by |
| --- | --- | --- |
| Assets | platform inventory (Windows/Linux/macOS/Containers/ESXi/IaaS/SaaS/Office Suite/Identity Provider/Network Devices/Android/iOS + OT/ICS and mobile/MDM markers) | applicability engine (platform + domain-gate N/A reasons) |
| Log Sources | onboarded telemetry categories | gap-ranking feasibility bridge (short/mid/long); Phase A3 shelfware cross-check |
| Security Tooling | deployed security products | gap-ranking feasibility bridge |
| Crown Jewels | free-text critical-asset descriptions | display only today; Phase A4 wires this into within-tier gap-ordering via a deterministic keyword bridge |

### What customers should provide (revised)

- Detection-rule / use-case inventory export (required)
- Asset/platform inventory (optional, but materially improves accuracy —
  every applicability decision without it degrades to a lower-bound
  assumption)
- Log-source and security-tooling inventory (optional; improves gap
  ranking's feasibility ordering)
- Existing ATT&CK mappings, if any (the dump's own technique-tag column —
  not a separate deliverable)
- Crown-jewel / critical-asset list (optional, free text)
- SIEM connector inventory: **not manual today for Microsoft Sentinel** —
  see "Automatable inputs" below; for other SIEMs, remains a manual
  Log Sources entry.

**Removed:** "Sample logs" — never requested; would violate the no-raw-log
invariant above if it were.

**Demoted:** Architecture/network diagrams are not collected as
structured input at all. If a customer offers them, they're optional
narrative context a human reviewer might skim before advising the
customer — the product itself never parses or ingests them.

### Automatable inputs (live or planned)

- **Microsoft Sentinel connector** (live): when an assessment is created
  from a connected Sentinel workspace, the product can pull the
  workspace's onboarded data-connector/table inventory and
  auto-populate Log Sources (and derivable Assets platforms), so a
  Sentinel customer can skip the manual Log Sources sheet entirely.
  Auto-imported data is always overridable by an explicit uploaded
  workbook and is always labeled as auto-imported in assumptions.
- Detection-rule inventory: also connector-pullable from Sentinel
  (`alertRules`) today; the same auto-import principle applies.

## Assess data sources instead of products

Infoblox SSH logs → Linux mapping
Infoblox DNS logs → Network mapping
Infoblox audit logs → Identity mapping
Infoblox API logs → Application mapping

## Assessed layers

- **Asset coverage** — assessable today (Assets sheet → applicability engine).
- **Log-source coverage** — assessable today (Log Sources sheet → gap-ranking
  feasibility bridge + Phase A3 telemetry cross-check).
- **Parser coverage** — *not assessable today.* Assessable only once the
  optional "Parser / Format" column ships (plan phase A6); until then, do
  not recommend scoring this layer, only flag it as a documented gap.
- **Normalization coverage** — *not assessable today* for the same
  reason; the optional "Normalized (Y/N)" column (phase A6) is what would
  make this assessable.
- **Detection coverage** — assessable today (use-case dump → coverage engine).
- **ATT&CK coverage** — assessable today (the whole pipeline's output).

**Mainframe note:** MITRE ATT&CK v19.1 (the pinned dataset) has no
mainframe/z-OS platform in Enterprise, ICS, or Mobile. z/OS support is
therefore necessarily a set of custom, off-framework mappings, not native
ATT&CK technique coverage — say so explicitly in any recommendation that
touches mainframe/z-OS rather than implying it maps cleanly.

## Supported technologies (asset/platform vocabulary)

- Windows, Linux, macOS, Active Directory, Entra ID, Okta, AWS, Azure, GCP
- Kubernetes/Containers, Firewalls, Proxies, IDS/IPS, DNS appliances
- Backup appliances, Email gateways, EDR platforms, SaaS platforms
- Custom applications
- Mainframes (z/OS) — see the mainframe note above; off-framework only

## Special appliance handling
Infoblox:
- SSH logs
- Syslog
- DNS logs
- DHCP logs
- IPAM logs
- Audit logs

Rubrik:
- Backup logs
- Audit logs
- Administrative logs
- API logs

VMware Photon OS:
- Authentication logs
- Process logs
- Audit logs

z/OS:
- SMF records
- RACF logs
- Custom mappings (off-framework — see mainframe note)

## Review criteria
For every field determine:
- Is it required?
- Why is it required?
- Can it be collected automatically?
- Can customers easily provide it?
- Does it improve ATT&CK coverage quality?

## Expected output

1. Executive summary.
2. Required fields.
3. Optional fields.
4. Fields to remove.
5. Workflow recommendations.
6. **Scoring rubric** (replaces "Final scoring"):
   - For every field in the inventory above, give one verdict: **keep**,
     **make-optional**, **remove**, or **add** (for genuinely new fields),
     each with a one-line rationale.
   - Then give ONE overall **data-sufficiency score, 0–10**, where:
     - 0–3 = the module could not produce a defensible ATT&CK coverage
       assessment from what it collects today
     - 4–6 = usable for a rough/directional assessment; material gaps
       remain in either accuracy or customer burden
     - 7–8 = solid for a paid engagement; minor refinements only
     - 9–10 = matches or exceeds informal Big-4 SOC-assessment data
       collection practice for this scope
   - State the score and the single biggest reason it isn't a 10.

Be extremely critical and optimize for completeness, usability, automation, and accuracy — but only within the hard invariants above.
