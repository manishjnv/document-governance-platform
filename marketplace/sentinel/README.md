# ScopeSense MITRE Coverage — Sentinel workbook (Content Hub add-on, Phase A)

Plan: `docs/planning/SENTINEL_CONTENT_HUB_ADDON_PLAN.md`.

`ScopeWiseMitreCoverage.workbook.json` is **generated — never hand-edit**:

```
python scripts/generate_sentinel_workbook.py
```

Source of truth is the MITRE module's pinned data
(`apps/api/app/mitre/data/attack.json`, `technique_priorities.json`) plus the
component→table map inside the generator script. Regenerate after any ATT&CK
version upgrade.

## What it shows (all in-tenant, viewer's own RBAC, nothing leaves the tenant)

| Tab | Content | Data source |
|---|---|---|
| Coverage | Enabled-rules-only ATT&CK v19.1 heatmap, % stat, per-tactic bars, not-covered grid | ARM `alertRules` (hidden query parameters) + embedded technique datatable |
| Rule health | Enabled rules sorted by alert evidence (never-fired first), noisiest rules, disabled rules | `SecurityAlert` + ARM |
| Telemetry | Required tables per ATT&CK data component vs. actual ingestion | `Usage` + embedded needs datatable |
| Top gaps | Uncovered techniques ranked by curated prevalence tier | embedded priority datatable |
| Full assessment | Funnel to the ScopeSense SaaS | markdown |

## Testing (needs a Sentinel workspace)

1. Sentinel → Workbooks → **Add workbook** → edit → **Advanced Editor** →
   paste the JSON → Apply.
2. Pick the workspace in the parameter pill; viewer needs
   **Microsoft Sentinel Reader**.
3. Check each tab with (a) an empty workspace, (b) a workspace with rules.

## Known blind spots to verify in the first live test

Authored without a live workspace — these serializations are best-effort and
the most likely things to need iteration:

1. **JSONPath filter expressions** in the ARM transformers
   (`$.value[?(@.properties.enabled==true)]...`) — if the workbook's JSONPath
   implementation rejects filters, fall back to pulling all rules plus an
   `enabled` column and filtering in KQL instead.
2. **ARM-query parameters** (`CoveredTechniques`, `EnabledRuleNames`): exact
   parameter serialization (`queryType: 12` inside a parameters item, custom
   `delimiter`) may need adjustment in the workbook editor — build one by
   hand in the UI once and diff against the generated JSON.
3. **Workspace parameter** (`type: 5` ARG resource picker) — confirm
   `{Workspace}` resolves to the full ARM resource ID so the alertRules path
   works.
4. **`SecurityAlert` join key** — alerts link to rules by `AlertName` ==
   rule display name; renamed rules will show as never-fired. Documented
   fuzziness, acceptable for v0.
5. **`api-version` 2024-09-01** for `Microsoft.SecurityInsights/alertRules`
   — bump if the API rejects it.

## Not in scope for the free workbook (deliberate — this is the funnel)

Keyword/AI mapping of untagged rules, applicability filtering, threat-actor
weighting, reports, trend, Splunk. See the plan's Tier 2.
