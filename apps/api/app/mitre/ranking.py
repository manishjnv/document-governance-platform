"""Deterministic gap ranking + roadmap bucketing (plan §7 stage 6). Pure.

Rank order: priority tier (technique_priorities.json, user-approved
2026-08-01) → detection feasibility (customer's onboarded log sources vs
the technique's ATT&CK data components; already-onboarded = cheapest win)
→ not_covered before partial → tactic order → technique id.

Roadmap buckets by dependency:
- short (0–3 mo): a required telemetry category is already onboarded —
  build the detection now, on the named source.
- mid (3–9 mo): the telemetry is obtainable from security tooling the
  customer already owns — onboard it, then detect.
- long (9–18 mo): needs a new capability (or ATT&CK lists no standard
  telemetry — bespoke detection engineering).

The log-source/tooling → telemetry-category bridge is keyword-based.
ponytail: coarse heuristic buckets; replace with a curated mapping table
if real customer dumps defeat them.
"""

import re

from .attack_data import DEFAULT, load_technique_priorities

_FEASIBILITY_RANK = {"short": 0, "mid": 1, "long": 2}
_STATE_RANK = {"not_covered": 0, "partial": 1}
UNLISTED_TIER = 4  # techniques absent from the priorities file rank below tier 3

# Category detection over ATT&CK data-component names. Checked in order —
# first hit wins; "endpoint" last because its keywords are broadest.
# Phase 6 note: recon/threat-intel components (Response Content/Metadata,
# Domain Registration, Social Media, Malware Content/Metadata) are LEFT
# unmatched on purpose — "no standard telemetry -> long term" is the honest
# verdict for those; a SIEM log source can't provide them.
_COMPONENT_CATEGORY_RULES = [
    ("registry", ("registry",)),
    ("cloud", ("cloud", "instance", "snapshot", "volume", "bucket", "container",
               "pod", "image creation", "image metadata", "image modification")),
    ("network", ("network", "dns", "firewall", "traffic", "internet scan")),
    ("identity", ("logon", "account", "credential", "authentication",
                  "active directory", "group", "token", "certificate")),
    ("application", ("application log", "web", "email")),
    # Mobile-domain components — providable by MDM/EMM telemetry.
    ("mobile", ("application permission", "application state", "system settings",
                "system notification", "protected configuration",
                "permissions request", "api calls", "application assets")),
    # ICS-domain components — providable by OT security monitoring.
    ("ot", ("device alarm", "asset inventory", "software")),
    ("endpoint", ("process", "command", "module", "script", "image load", "os api",
                  "driver", "service", "scheduled", "wmi", "named pipe", "file",
                  "kernel", "firmware", "drive", "sensor", "host status")),
]

# Customer log-source names -> telemetry categories they provide.
# NOTE: matched by SUBSTRING over the normalized entry — keep every keyword
# long/specific enough not to hide inside an unrelated word (no bare "ot":
# it's inside "remote"; no bare "ics": it's inside "analytics").
_LOG_SOURCE_RULES = [
    (("sysmon",), {"endpoint", "registry", "network"}),
    (("edr", "crowdstrike", "falcon", "defender", "sentinelone", "sentinel one",
      "carbon black", "cortex", "xdr", "trellix", "mcafee", "symantec",
      "tanium", "cybereason", "sophos", "trend micro", "bitdefender", "eset",
      "huntress"), {"endpoint", "registry"}),
    (("windows event", "wineventlog", "winlog", "security log", "event log",
      "domain controller"), {"endpoint", "identity", "registry"}),
    (("auditd", "linux audit", "osquery", "powershell"), {"endpoint"}),
    (("active directory", "okta", "entra", "azure ad", "idp", "sso", "auth",
      "identity", "duo", "adfs", "ldap", "kerberos", "radius", "ping identity",
      "ping federate", "mfa", "onelogin", "jumpcloud", "keycloak"), {"identity"}),
    (("dns", "umbrella", "infoblox", "route 53", "route53"), {"network"}),
    (("zeek", "bro", "netflow", "ndr", "pcap", "packet", "firewall", "palo",
      "fortigate", "fortinet", "network", "suricata", "snort", "corelight",
      "extrahop", "gigamon", "meraki", "sonicwall", "juniper", "cisco asa",
      "checkpoint", "check point", "darktrace", "vectra"), {"network"}),
    (("proxy", "swg", "web gateway", "waf", "iis", "apache", "nginx",
      "web server", "web", "zscaler", "netskope", "bluecoat", "blue coat",
      "squid", "cloudflare", "akamai", "haproxy"), {"application", "network"}),
    (("cloudtrail", "cloud trail", "azure activity", "gcp audit", "cloud audit",
      "aws config", "s3 access", "cloud", "guardduty", "cloudwatch",
      "azure monitor", "security hub", "stackdriver", "unified audit",
      "m365 audit", "office 365 audit"), {"cloud"}),
    (("vpc flow", "flow log"), {"network", "cloud"}),
    (("kubernetes", "k8s", "container", "docker", "eks", "openshift",
      "rancher", "containerd", "falco", "sysdig"), {"cloud"}),
    (("email", "message trace", "proofpoint", "mimecast", "exchange",
      "barracuda", "ironport", "abnormal security", "avanan"), {"application"}),
    (("fim", "file integrity", "tripwire"), {"endpoint"}),
    (("dlp", "data loss prevention", "digital guardian"), {"endpoint"}),
    # MDM/EMM telemetry provides the Mobile-matrix components.
    (("mdm", "intune", "jamf", "workspace one", "airwatch", "mobileiron",
      "kandji", "soti", "maas360", "emm"), {"mobile"}),
    # OT security monitoring provides the ICS-matrix components.
    (("claroty", "nozomi", "dragos", "scada", "industrial", "modbus",
      "ot telemetry", "ot network", "operational technology"), {"ot"}),
]

# Security-tooling names -> categories that tooling could be onboarded to provide.
_TOOLING_RULES = [
    (("edr", "crowdstrike", "falcon", "defender", "sentinelone", "sentinel one",
      "carbon black", "cortex", "xdr", "antivirus", "av", "trellix", "mcafee",
      "symantec", "tanium", "cybereason", "sophos", "trend micro",
      "bitdefender", "eset", "malwarebytes", "huntress",
      "elastic defend"), {"endpoint", "registry"}),
    (("ndr", "network detection", "zeek", "corelight", "darktrace", "vectra",
      "netflow", "firewall", "suricata", "snort", "extrahop",
      "gigamon"), {"network"}),
    (("email", "proofpoint", "mimecast", "email security", "barracuda",
      "ironport", "abnormal security", "avanan"), {"application"}),
    (("proxy", "swg", "waf", "web gateway", "zscaler", "netskope", "bluecoat",
      "forcepoint", "squid"), {"application", "network"}),
    (("casb", "cloud security", "wiz", "cspm", "prisma", "defender for cloud",
      "orca", "lacework", "aqua", "sysdig", "guardduty"), {"cloud"}),
    (("iam", "pam", "identity", "okta", "entra", "cyberark", "sailpoint",
      "beyondtrust", "delinea", "thycotic", "duo", "jumpcloud", "adfs",
      "keycloak", "onelogin", "ping identity"), {"identity"}),
    (("dlp", "purview", "digital guardian"), {"endpoint"}),
    # MDM/EMM could be onboarded to feed Mobile-matrix telemetry.
    (("mdm", "intune", "jamf", "workspace one", "airwatch", "mobileiron",
      "kandji", "soti", "maas360", "emm"), {"mobile"}),
    # OT monitoring platforms could be onboarded to feed ICS telemetry.
    (("claroty", "nozomi", "dragos", "scada", "operational technology",
      "industrial"), {"ot"}),
]


def _norm(value) -> str:
    return re.sub(r"\s+", " ", re.sub(r"[^a-z0-9 ]", " ", str(value or "").lower())).strip()


def component_category(component_name: str):
    """ATT&CK data-component name -> coarse telemetry category (or None)."""
    name = _norm(component_name)
    for category, keywords in _COMPONENT_CATEGORY_RULES:
        if any(kw in name for kw in keywords):
            return category
    return None


def _categories_provided(entries, rules) -> dict:
    """{category: first entry name that provides it} over customer rows."""
    provided = {}
    for entry in entries or []:
        entry_norm = _norm(entry)
        for keywords, categories in rules:
            if any(kw in entry_norm for kw in keywords):
                for category in categories:
                    provided.setdefault(category, str(entry))
    return provided


def _feasibility(tech: dict, onboarded: dict, ownable: dict):
    """(bucket, via, category, hint) for one technique."""
    categories = []
    for component in tech.get("data_sources") or []:
        category = component_category(component)
        if category and category not in categories:
            categories.append(category)
    if not categories:
        return (
            "long", None, None,
            "ATT&CK lists no standard telemetry for this technique — needs "
            "bespoke detection engineering",
        )
    for category in categories:
        if category in onboarded:
            return (
                "short", onboarded[category], category,
                f"telemetry already onboarded ({onboarded[category]} covers "
                f"{category}) — build the detection now",
            )
    for category in categories:
        if category in ownable:
            return (
                "mid", ownable[category], category,
                f"onboard {category} telemetry from {ownable[category]} first, "
                "then build the detection",
            )
    return (
        "long", None, categories[0],
        f"requires a new telemetry capability ({', '.join(categories)})",
    )


def rank_gaps(techniques, log_sources, tooling, *, index=None, priorities=None) -> dict:
    """Coverage per-technique results -> ranked gap list + roadmap buckets.

    techniques: coverage.compute_coverage()["techniques"].
    log_sources/tooling: raw customer rows from the environment workbook.
    Returns {"gaps": [gap...], "roadmap": {"short": [...], "mid": [...],
    "long": [...]}} — gap dicts carry technique_id, name, domain, state,
    tier, tactics, feasibility, via, category, hint, rank.
    """
    index = index if index is not None else DEFAULT
    if priorities is None:
        priorities = load_technique_priorities()
    tier_by_id = {t["technique_id"]: t["tier"] for t in priorities.get("techniques", [])}

    onboarded = _categories_provided(log_sources, _LOG_SOURCE_RULES)
    ownable = _categories_provided(tooling, _TOOLING_RULES)

    tactic_position = {}
    for domain in index.domains:
        for pos, tactic in enumerate(index.tactics(domain)):
            tactic_position[(domain, tactic["id"])] = pos

    gaps = []
    for result in techniques:
        if result["state"] not in _STATE_RANK:
            continue
        tech = index.get(result["technique_id"])
        if tech is None:
            continue
        bucket, via, category, hint = _feasibility(tech, onboarded, ownable)
        positions = [
            tactic_position.get((result["domain"], t), 99) for t in result["tactics"]
        ] or [99]
        gaps.append(
            {
                "technique_id": result["technique_id"],
                "name": tech.get("name", result["technique_id"]),
                "domain": result["domain"],
                "state": result["state"],
                "tier": tier_by_id.get(result["technique_id"], UNLISTED_TIER),
                "tactics": result["tactics"],
                "feasibility": bucket,
                "via": via,
                "category": category,
                "hint": hint,
                "_tactic_pos": min(positions),
            }
        )

    gaps.sort(
        key=lambda g: (
            g["tier"],
            _FEASIBILITY_RANK[g["feasibility"]],
            _STATE_RANK[g["state"]],
            g["_tactic_pos"],
            g["technique_id"],
        )
    )
    roadmap = {"short": [], "mid": [], "long": []}
    for rank, gap in enumerate(gaps, start=1):
        gap.pop("_tactic_pos")
        gap["rank"] = rank
        roadmap[gap["feasibility"]].append(gap)
    return {"gaps": gaps, "roadmap": roadmap}
