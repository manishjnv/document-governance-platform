# Tool-Native Coverage Overlay — design plan (2026-08-18)

**Why:** the most common client objection to the assessment ("our EDR
covers that TTP — that's why there's no SIEM rule", raised on the MGH
engagement 2026-08-18). Today the Security Tooling sheet feeds roadmap
feasibility only; tool-native detections are invisible to coverage, so
EDR-heavy shops read artificially low.

**The idea in one line:** the client declares their security tools; the
assessment credits the techniques those tools are *publicly proven* to
detect — as a separate, clearly-labeled overlay that never merges with
the rule-based score.

## Hard invariants (carry over from the module's design)

1. **Two numbers, never one.** "SIEM rule coverage: 19.8%" and "including
   your declared tools' evaluated detections: ~45%" are always shown as
   two labeled figures. The overlay never changes `strict_pct`,
   `weighted_pct`, tactic rollups, or trend math.
2. **Evidence is published third-party data, cited on the page.** Per-tool
   technique lists come from MITRE's own ATT&CK Evaluations results
   (public, per-vendor, per-round) — never vendor marketing, never
   invented. Each tool entry cites its evaluation round in-file.
3. **The caveat prints wherever the overlay shows:** "vendor-evaluated
   capability, not proof the alerts are tuned, monitored, or reaching
   your SOC."
4. Deterministic: pure lookup, no LLM anywhere.

## Data

`app/mitre/data/tool_coverage.json` (new, curated, test-enforced):

```json
{
  "_comment": "per-tool technique lists from MITRE ATT&CK Evaluations …",
  "tools": {
    "crowdstrike falcon": {
      "label": "CrowdStrike Falcon",
      "synonyms": ["crowdstrike", "falcon", "crowdstrike falcon edr"],
      "source": "MITRE ATT&CK Evaluations, Enterprise Round 5 (Turla, 2023)",
      "url": "https://attackevals.mitre-engenuity.org/…",
      "techniques": ["T1003.001", "T1055", "…"]
    },
    "microsoft defender for endpoint": { "…": "…" }
  }
}
```

- Start with the tools MITRE actually evaluated and customers actually
  declare: CrowdStrike Falcon, Microsoft Defender for Endpoint,
  SentinelOne Singularity, Palo Alto Cortex XDR, Trend Vision One,
  Sophos Intercept X. Grow on demand.
- Every technique ID must resolve against the pinned attack.json
  (test-enforced, same pattern as threat_profiles).
- Refresh cadence: once per Evaluations round (~yearly).

## Matching

Customer's Security Tooling entries → tool keys via case-insensitive
substring over `synonyms` (same approach as the platform-synonym
normalizer in ingest). Unmatched entries keep today's behavior
(feasibility only) and are listed as an assumption ("N declared tools have
no published evaluation data — not overlaid").

## Pipeline & storage

- `coverage.py` (or a small pure `tool_overlay.py`): after states are
  computed, each technique result gains
  `"tool_covered": ["CrowdStrike Falcon"]` when (a) a declared tool's
  curated list contains it and (b) its state is `not_covered` or
  `partial`. Covered stays covered — the overlay only explains gaps.
- `summary.overall` gains `tool_covered_extra` (count) and
  `tool_adjusted_pct` = (covered + tool-covered-open) / applicable —
  stored alongside, never replacing, the existing numbers.
- Gap ranking: tool-covered gaps sink below equal-priority peers
  (ordering only — same rule as threat weighting).

## Surfaces

| Surface | Change |
|---|---|
| Heatmap (app, PDF, PPTX mosaic) | 4th color (blue) for "open, but tool-covered"; legend + counts |
| Board slide / exec pages | second labeled number + caveat line |
| XLSX Technique Tracker | "Tool coverage (vendor-evidenced)" column naming the tool(s) |
| Gap register / tracker rows | "Your CrowdStrike Falcon was evaluated as detecting this — confirm the alert reaches your SOC, or build the SIEM rule anyway" |
| Assumptions | source citation + unmatched-tools note |

## What the client does (the whole ask)

Fill the **Security Tooling** sheet of the environment workbook with
product names ("CrowdStrike Falcon", "Microsoft Defender for Endpoint").
No exports, no API access. **Template updated 2026-08-18** to carry
canonical-name examples and a note explaining precise names power the
overlay (shipped ahead of the feature — names collected now work later).

## Phases

- **T1 (backend core): ✅ SHIPPED 2026-08-19** — with one deliberate
  deviation from this plan: the overlay is computed at **render/read
  time** (`report_common.compute_tool_overlay`, pure lookup over declared
  tooling x stored states), NOT in the pipeline. Better than planned:
  zero storage/pipeline change, and it lights up retroactively on every
  existing assessment. Curated `data/tool_coverage.json` v1 uses a
  conservative core evaluated-technique set shared across the six tools
  (per-tool refinement to exact round results is a data-only change).
- **T2 (surfaces): ✅ SHIPPED 2026-08-19** — PDF (board second number,
  blue heatmap cells, per-gap "Tool credit" note), XLSX (Tracker "Tool
  coverage (MITRE-evaluated)" column + Summary row), PPTX (board line,
  blue mosaic cells + legend entry), app UI (blue strip under the
  executive band + drawer credit card via GET assessment's computed
  `tool_coverage` field). Deferred from this phase: gap-ranking demotion
  of tool-covered gaps (ordering churn vs rank tests — revisit on ask).
- **T3 (template + docs):** ✅ template guidance shipped 2026-08-18.
- **T4 (attestation): ✅ SHIPPED 2026-08-19** — the honest bridge from
  credit to score. `POST /assessments/{id}/tool-attest` (admin/reviewer):
  validates the tool is matched and each technique currently carries its
  credit, then creates one enabled rule row per technique
  (`mapping_status='tool_attested'`, mapping source `manual` @ 1.0,
  log_source = the tool, description stamps who attested + when + the
  evaluation basis) and recomputes coverage inline (same engine as the
  Phase 10 mapping edit). Migration 038 widens the mapping_status CHECK
  (+ ORM lockstep). UI: the drawer's credit card gains a "We monitor
  <tool>'s alerts — count as covered" button per tool. Once covered, the
  credit disappears and re-attesting is refused — the score owns it.
  Trust model: the customer attests, so the claim is theirs (same as
  their own ATT&CK tags); the rule row is auditable and lists as
  "Tool-attested — alert path confirmed" everywhere.

## Rejected

- Merging the two numbers or defaulting the headline to the adjusted one.
- Scraping vendor claim pages; only MITRE Evaluations results qualify.
- Auto-marking N/A ("covered elsewhere" is not "not applicable").
