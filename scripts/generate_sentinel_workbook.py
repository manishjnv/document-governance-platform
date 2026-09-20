"""Generate the ScopeSense Sentinel Content Hub workbook (Phase A of
docs/planning/SENTINEL_CONTENT_HUB_ADDON_PLAN.md).

Reads the MITRE module's pinned data (apps/api/app/mitre/data/) and emits
marketplace/sentinel/ScopeWiseMitreCoverage.workbook.json — an Azure
Workbook ("honest coverage"): enabled-rules-only ATT&CK v19.1 coverage,
never-fired rule health, telemetry reality check, and a top-gaps teaser.

Regenerate after any ATT&CK version upgrade:
    python scripts/generate_sentinel_workbook.py

Import for testing: Sentinel -> Workbooks -> Add workbook -> Advanced
Editor -> paste the JSON. See marketplace/sentinel/README.md.
"""

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "apps" / "api" / "app" / "mitre" / "data"
OUT_DIR = ROOT / "marketplace" / "sentinel"
OUT = OUT_DIR / "ScopeWiseMitreCoverage.workbook.json"

# Rule names may contain commas; ARM-query parameters join values with this.
DELIM = "~|~"

# ATT&CK data-source component -> Sentinel tables that typically carry it.
# ponytail: ~most common components only; unmapped components produce no
# telemetry probe (absence of a probe is not a claim of coverage).
COMPONENT_TABLES = {
    "Process Creation": ["SecurityEvent", "DeviceProcessEvents", "Syslog"],
    "Command Execution": ["DeviceProcessEvents", "SecurityEvent", "Syslog"],
    "Network Traffic Content": ["CommonSecurityLog", "DeviceNetworkEvents"],
    "Network Traffic Flow": ["CommonSecurityLog", "DeviceNetworkEvents", "AzureNetworkAnalytics_CL"],
    "Network Connection Creation": ["DeviceNetworkEvents", "CommonSecurityLog"],
    "Logon Session Creation": ["SigninLogs", "SecurityEvent", "IdentityLogonEvents"],
    "Logon Session Metadata": ["SigninLogs", "AADNonInteractiveUserSignInLogs"],
    "User Account Authentication": ["SigninLogs", "SecurityEvent"],
    "File Creation": ["DeviceFileEvents", "SecurityEvent"],
    "File Modification": ["DeviceFileEvents"],
    "File Access": ["DeviceFileEvents", "SecurityEvent"],
    "Windows Registry Key Creation": ["DeviceRegistryEvents", "SecurityEvent"],
    "Windows Registry Key Modification": ["DeviceRegistryEvents", "SecurityEvent"],
    "Application Log Content": ["OfficeActivity", "W3CIISLog", "AppServiceHTTPLogs"],
    "Cloud Service Metadata": ["AzureActivity", "AWSCloudTrail", "GCPAuditLogs"],
    "Cloud Service Modification": ["AzureActivity", "AWSCloudTrail"],
    "Cloud Storage Access": ["AzureActivity", "AWSCloudTrail", "StorageBlobLogs"],
    "DNS": ["DnsEvents", "DeviceNetworkEvents"],
    "Script Execution": ["DeviceEvents", "SecurityEvent"],
    "Module Load": ["DeviceImageLoadEvents"],
    "Driver Load": ["DeviceEvents"],
    "Service Creation": ["SecurityEvent", "DeviceEvents"],
    "Scheduled Job Creation": ["SecurityEvent", "DeviceEvents"],
    "OS API Execution": ["DeviceEvents"],
    "Web Credential Usage": ["SigninLogs", "AADNonInteractiveUserSignInLogs"],
    "Active Directory Object Modification": ["SecurityEvent", "AuditLogs"],
    "Group Modification": ["AuditLogs", "SecurityEvent"],
    "User Account Creation": ["AuditLogs", "SecurityEvent"],
    "User Account Modification": ["AuditLogs", "SecurityEvent"],
    "Email": ["EmailEvents", "OfficeActivity"],
}

FULL_ASSESSMENT_URL = "https://scopesense.in/mitre"


def _kql_str(value) -> str:
    escaped = str(value or "").replace("\\", "\\\\").replace('"', '\\"')
    return f'"{escaped}"'


def load_techniques():
    attack = json.loads((DATA / "attack.json").read_text(encoding="utf-8"))
    ent = attack["domains"]["enterprise"]
    tactic_names = {}
    tactics = ent.get("tactics") or []
    for t in tactics if isinstance(tactics, list) else tactics.values():
        tactic_names[t["id"]] = t["name"]
    prios = json.loads((DATA / "technique_priorities.json").read_text(encoding="utf-8"))
    tiers = {t["technique_id"]: t for t in prios["techniques"]}
    rows = []
    for t in ent["techniques"]:
        if t.get("deprecated") or t.get("revoked"):
            continue
        names = [tactic_names.get(ta, ta) for ta in (t.get("tactics") or [])]
        tier = tiers.get(t["id"])
        rows.append({
            "id": t["id"],
            "name": t["name"],
            "tactics": ";".join(names) or "Unknown",
            "is_sub": bool(t.get("is_subtechnique")),
            "parent": t.get("parent_id") or "",
            "tier": tier["tier"] if tier else 9,
            "why": tier["why"] if tier else "",
            "components": t.get("data_sources") or [],
        })
    return attack["version"], rows


def attack_datatable(rows) -> str:
    lines = [
        "let Attack = datatable(TechniqueId:string, TechniqueName:string, Tactics:string, IsSub:bool, ParentId:string, Tier:long)["
    ]
    for r in rows:
        lines.append(
            f'{_kql_str(r["id"])},{_kql_str(r["name"])},{_kql_str(r["tactics"])},'
            f'{"true" if r["is_sub"] else "false"},{_kql_str(r["parent"])},{r["tier"]},'
        )
    lines.append("];")
    return "\n".join(lines)


def tier_datatable(rows) -> str:
    lines = [
        "let Priority = datatable(TechniqueId:string, TechniqueName:string, Tier:long, Why:string)["
    ]
    for r in rows:
        if r["tier"] <= 3:
            lines.append(
                f'{_kql_str(r["id"])},{_kql_str(r["name"])},{r["tier"]},{_kql_str(r["why"])},'
            )
    lines.append("];")
    return "\n".join(lines)


def telemetry_datatable(rows) -> str:
    counts = {}
    for r in rows:
        for c in r["components"]:
            counts[c] = counts.get(c, 0) + 1
    lines = [
        "let Needs = datatable(Component:string, DataType:string, TechniquesNeedingIt:long)["
    ]
    for comp, tables in COMPONENT_TABLES.items():
        n = counts.get(comp, 0)
        if n == 0:
            continue
        for table in tables:
            lines.append(f"{_kql_str(comp)},{_kql_str(table)},{n},")
    lines.append("];")
    return "\n".join(lines)


# --- workbook item helpers ------------------------------------------------

def text(md, tab=None, name="text"):
    item = {"type": 1, "content": {"json": md}, "name": name}
    if tab:
        item["conditionalVisibility"] = {
            "parameterName": "selectedTab", "comparison": "isEqualTo", "value": tab,
        }
    return item


def kql(query, tab, name, *, viz=None, title=None, size=0, width=None, extra=None):
    content = {
        "version": "KqlItem/1.0",
        "query": query,
        "size": size,
        "queryType": 0,
        "resourceType": "microsoft.operationalinsights/workspaces",
    }
    if viz:
        content["visualization"] = viz
    if title:
        content["title"] = title
    if extra:
        content.update(extra)
    item = {
        "type": 3,
        "content": content,
        "conditionalVisibility": {
            "parameterName": "selectedTab", "comparison": "isEqualTo", "value": tab,
        },
        "name": name,
    }
    if width:
        item["customWidth"] = width
    return item


def arm_rules_query(jsonpath_table, columns):
    """ARMEndpoint query string enumerating this workspace's analytics rules."""
    return json.dumps({
        "version": "ARMEndpoint/1.0",
        "data": None,
        "headers": [],
        "method": "GET",
        "path": "{Workspace}/providers/Microsoft.SecurityInsights/alertRules",
        "urlParams": [{"key": "api-version", "value": "2024-09-01"}],
        "batchDisabled": False,
        "transformers": [{
            "type": "jsonpath",
            "settings": {"tablePath": jsonpath_table, "columns": columns},
        }],
    })


def build(version, rows):
    attack_dt = attack_datatable(rows)
    n_total = len(rows)

    tabs = [
        ("Overview", "Overview"),
        ("Coverage", "Coverage"),
        ("RuleHealth", "Rule health"),
        ("Telemetry", "Telemetry"),
        ("TopGaps", "Top gaps"),
        ("FullAssessment", "Full assessment"),
    ]

    items = []

    # -- global parameters --------------------------------------------------
    items.append({
        "type": 9,
        "content": {
            "version": "KqlParameterItem/1.0",
            "parameters": [
                {
                    "name": "Workspace",
                    "label": "Sentinel workspace",
                    "type": 5,
                    "isRequired": True,
                    "query": "resources\n| where type =~ 'microsoft.operationalinsights/workspaces'\n| project id, name\n| order by name asc",
                    "crossComponentResources": ["value::selected"],
                    "typeSettings": {"resourceTypeFilter": {"microsoft.operationalinsights/workspaces": True}},
                    "queryType": 1,
                    "resourceType": "microsoft.resourcegraph/resources",
                },
                {
                    "name": "TimeRange",
                    "label": "Alert lookback",
                    "type": 4,
                    "isRequired": True,
                    "value": {"durationMs": 7776000000},
                    "typeSettings": {"selectableValues": [
                        {"durationMs": 2592000000}, {"durationMs": 7776000000},
                        {"durationMs": 15552000000},
                    ]},
                },
                {
                    # Flattened technique ids of ENABLED rules only — the
                    # honest-coverage core. Hidden; feeds every KQL tab.
                    "name": "CoveredTechniques",
                    "type": 1,
                    "isRequired": False,
                    "isHiddenWhenLocked": True,
                    "isGlobal": True,
                    "query": arm_rules_query(
                        "$.value[?(@.properties.enabled==true)].properties.techniques[*]",
                        [{"path": "$", "columnid": "TechniqueId"}],
                    ),
                    "delimiter": DELIM,
                    "queryType": 12,
                    "isVisible": False,
                },
                {
                    "name": "EnabledRuleNames",
                    "type": 1,
                    "isRequired": False,
                    "isHiddenWhenLocked": True,
                    "isGlobal": True,
                    "query": arm_rules_query(
                        "$.value[?(@.properties.enabled==true)]",
                        [{"path": "$.properties.displayName", "columnid": "RuleName"}],
                    ),
                    "delimiter": DELIM,
                    "queryType": 12,
                    "isVisible": False,
                },
            ],
            "style": "pills",
            "queryType": 0,
            "resourceType": "microsoft.operationalinsights/workspaces",
        },
        "name": "parameters",
    })

    # -- tab strip ----------------------------------------------------------
    items.append({
        "type": 11,
        "content": {
            "version": "LinkItem/1.0",
            "style": "tabs",
            "links": [
                {
                    "id": f"tab-{key}",
                    "cellValue": "selectedTab",
                    "linkTarget": "parameter",
                    "linkLabel": label,
                    "subTarget": key,
                    "style": "link",
                }
                for key, label in tabs
            ],
        },
        "name": "tabs",
    })

    # -- Overview -----------------------------------------------------------
    items.append(text(
        f"# ScopeSense MITRE ATT&CK Coverage — honest view\n---\n"
        f"Your detection coverage against **MITRE ATT&CK v{version}** "
        f"({n_total} enterprise techniques and sub-techniques), computed from "
        f"the analytics rules actually running in this workspace.\n\n"
        f"How this differs from the built-in MITRE blade:\n\n"
        f"- **Enabled rules only** — a disabled rule is a gap, not coverage.\n"
        f"- **Alert-fired evidence** — rules that never produced an alert in the "
        f"lookback window are flagged (Rule health tab).\n"
        f"- **No simulated inflation** — rule templates you haven't deployed don't count.\n"
        f"- **Telemetry reality check** — techniques whose required log tables aren't "
        f"being ingested (Telemetry tab).\n"
        f"- **Current ATT&CK v{version}** — the blade tracks an older framework version.\n\n"
        f"Viewer needs the **Microsoft Sentinel Reader** role. Nothing leaves your "
        f"tenant — every query runs with your own permissions.",
        tab="Overview", name="overview"))

    # -- Coverage -----------------------------------------------------------
    covered_prelude = (
        f'let CoveredIds = split("{{CoveredTechniques}}", "{DELIM}");\n{attack_dt}\n'
        "let Marked = Attack\n"
        "| extend Covered = TechniqueId in (CoveredIds)\n"
        "| extend ParentCovered = ParentId in (CoveredIds)\n"
        "| extend Effective = Covered or (IsSub and ParentCovered);\n"
    )
    items.append(kql(
        covered_prelude +
        "Marked\n| summarize Total=count(), Covered=countif(Effective)\n"
        "| extend CoveragePct = round(100.0 * Covered / Total, 1)\n"
        "| project ['Covered techniques']=Covered, ['Total techniques']=Total, ['Coverage %']=CoveragePct",
        "Coverage", "coverage-stat", viz="tiles", title="Enabled-rule coverage",
        extra={"tileSettings": {
            "showBorder": True,
            "titleContent": {"columnMatch": "Coverage %", "formatter": 12,
                             "formatOptions": {"palette": "coldHot"}},
        }}))
    items.append(kql(
        covered_prelude +
        "Marked\n| mv-expand Tactic = split(Tactics, ';')\n"
        "| extend Tactic = tostring(Tactic)\n"
        "| summarize Total=count(), Covered=countif(Effective) by Tactic\n"
        "| extend ['Coverage %'] = round(100.0 * Covered / Total, 1)\n"
        "| sort by ['Coverage %'] asc",
        "Coverage", "coverage-tactic", viz="barchart", title="Coverage by tactic (worst first)"))
    items.append(kql(
        covered_prelude +
        "Marked\n| where not(Effective)\n"
        "| project ['Technique']=TechniqueId, ['Name']=TechniqueName, ['Tactics']=Tactics,\n"
        "  ['Sub-technique']=IsSub, ['Priority tier']=iff(Tier==9, '', tostring(Tier))\n"
        "| sort by ['Priority tier'] asc, ['Technique'] asc",
        "Coverage", "coverage-grid", title="Not covered by any enabled rule",
        extra={"showExportToExcel": True,
               "gridSettings": {"rowLimit": 1000, "filter": True}}))

    # -- Rule health --------------------------------------------------------
    items.append(text(
        "## Rule health — is anything actually firing?\n"
        "A rule that exists but never produces an alert is either watching "
        "something that never happens, mis-tuned, or broken. Evidence below "
        "comes from `SecurityAlert` over the selected lookback.",
        tab="RuleHealth", name="health-intro"))
    items.append(kql(
        f'let Names = split("{{EnabledRuleNames}}", "{DELIM}");\n'
        "print n=Names\n| mv-expand n\n| extend RuleName = tostring(n)\n"
        "| join kind=leftouter (\n"
        "    SecurityAlert\n"
        "    | where TimeGenerated {TimeRange}\n"
        "    | summarize Fired=count(), LastFired=max(TimeGenerated) by AlertName\n"
        ") on $left.RuleName == $right.AlertName\n"
        "| extend Fired = coalesce(Fired, 0)\n"
        "| project ['Enabled rule']=RuleName, ['Alerts in window']=Fired, ['Last fired']=LastFired\n"
        "| sort by ['Alerts in window'] asc",
        "RuleHealth", "health-neverfired",
        title="Enabled rules by alert evidence (never-fired first)",
        extra={"showExportToExcel": True,
               "gridSettings": {"rowLimit": 500, "filter": True}}))
    items.append(kql(
        "SecurityAlert\n| where TimeGenerated {TimeRange}\n"
        "| summarize Alerts=count() by AlertName\n| top 15 by Alerts desc",
        "RuleHealth", "health-noisy", viz="barchart",
        title="Noisiest rules (tuning candidates)", width="50"))

    # Disabled rules straight from ARM — explicit risk, not silent absence.
    items.append({
        "type": 3,
        "content": {
            "version": "KqlItem/1.0",
            "query": arm_rules_query(
                "$.value[?(@.properties.enabled==false)]",
                [
                    {"path": "$.properties.displayName", "columnid": "Disabled rule"},
                    {"path": "$.kind", "columnid": "Kind"},
                    {"path": "$.properties.severity", "columnid": "Severity"},
                ],
            ),
            "size": 0,
            "title": "Disabled analytics rules (counted as gaps)",
            "queryType": 12,
            "gridSettings": {"rowLimit": 500, "filter": True},
        },
        "conditionalVisibility": {
            "parameterName": "selectedTab", "comparison": "isEqualTo", "value": "RuleHealth",
        },
        "customWidth": "50",
        "name": "health-disabled",
    })

    # -- Telemetry ----------------------------------------------------------
    items.append(text(
        "## Telemetry reality check\n"
        "A detection rule can only see what's being ingested. Rows below "
        "compare the log tables ATT&CK data-source components typically need "
        "against your actual ingestion (`Usage`, last 30 days). A missing "
        "table means every technique needing that component is dark — "
        "whatever the rule count says.",
        tab="Telemetry", name="telemetry-intro"))
    items.append(kql(
        telemetry_datatable(rows) +
        "\nlet Ingested = Usage\n| where TimeGenerated > ago(30d)\n"
        "| summarize MB=round(sum(Quantity), 1) by DataType;\n"
        "Needs\n| join kind=leftouter Ingested on DataType\n"
        "| extend Status = iff(isnotempty(MB) and MB > 0, '✔ ingesting', '✖ not ingested')\n"
        "| project ['Data component']=Component, ['Sentinel table']=DataType, Status,\n"
        "  ['MB (30d)']=coalesce(MB, 0.0), ['Techniques needing it']=TechniquesNeedingIt\n"
        "| sort by Status desc, ['Techniques needing it'] desc",
        "Telemetry", "telemetry-grid", title="Required tables vs. actual ingestion",
        extra={"showExportToExcel": True,
               "gridSettings": {"rowLimit": 500, "filter": True}}))

    # -- Top gaps -----------------------------------------------------------
    items.append(text(
        "## The gaps that matter most\n"
        "Uncovered techniques ranked by real-world prevalence (tiers curated "
        "from Red Canary TDR, Picus Red Report, CISA #StopRansomware, Verizon "
        "DBIR, Mandiant M-Trends). Tier 1 = near-universal in intrusions — "
        "close these first.",
        tab="TopGaps", name="gaps-intro"))
    items.append(kql(
        f'let CoveredIds = split("{{CoveredTechniques}}", "{DELIM}");\n'
        + tier_datatable(rows) +
        "\nPriority\n| where TechniqueId !in (CoveredIds)\n"
        "| project ['Tier']=Tier, ['Technique']=TechniqueId, ['Name']=TechniqueName, ['Why it matters']=Why\n"
        "| sort by ['Tier'] asc, ['Technique'] asc\n| take 15",
        "TopGaps", "gaps-grid", title="Top uncovered high-prevalence techniques",
        extra={"showExportToExcel": True, "gridSettings": {"rowLimit": 50, "filter": True}}))

    # -- Full assessment funnel --------------------------------------------
    items.append(text(
        "## This workbook is the honest snapshot. The full assessment goes further.\n---\n"
        "The free view above only counts rules that carry explicit ATT&CK tags. "
        f"The **[ScopeSense full assessment]({FULL_ASSESSMENT_URL})** adds:\n\n"
        "- **Keyword + AI mapping** of the untagged majority of your rules — "
        "most environments' biggest blind spot\n"
        "- **Applicability filtering** — score against the techniques that apply "
        "to *your* platforms, not the whole matrix\n"
        "- **Threat-actor-weighted gap ranking** and a phased remediation roadmap\n"
        "- **Executive PPTX / PDF / XLSX reports** ready for the board\n"
        "- **Trend tracking** across scheduled re-assessments, with newly-covered "
        "vs. regressed diffs\n"
        "- **Security-tool coverage credit** (EDR/email/identity tools, attested)\n"
        "- **Multi-SIEM** — the same assessment against Splunk\n\n"
        "Setup is read-only: a service principal with the **Microsoft Sentinel "
        "Reader** role, five IDs, and one click. "
        f"**[Start at scopesense.in]({FULL_ASSESSMENT_URL})**.",
        tab="FullAssessment", name="funnel"))

    return {
        "version": "Notebook/1.0",
        "items": items,
        "fromTemplateId": "scopewise-mitre-coverage",
        "$schema": "https://github.com/Microsoft/Application-Insights-Workbooks/blob/master/schema/workbook.json",
    }


def main():
    version, rows = load_techniques()
    workbook = build(version, rows)
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(workbook, indent=1, ensure_ascii=False), encoding="utf-8")
    size_kb = OUT.stat().st_size / 1024
    print(f"ATT&CK v{version}: {len(rows)} active techniques -> {OUT} ({size_kb:.0f} KB)")


if __name__ == "__main__":
    main()
