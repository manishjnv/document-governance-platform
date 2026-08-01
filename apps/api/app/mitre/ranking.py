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
_COMPONENT_CATEGORY_RULES = [
    ("registry", ("registry",)),
    ("cloud", ("cloud", "instance", "snapshot", "volume", "bucket", "container", "pod")),
    ("network", ("network", "dns", "firewall", "traffic", "internet scan")),
    ("identity", ("logon", "account", "credential", "authentication",
                  "active directory", "group", "token", "certificate")),
    ("application", ("application log", "web", "email")),
    ("endpoint", ("process", "command", "module", "script", "image load", "os api",
                  "driver", "service", "scheduled", "wmi", "named pipe", "file",
                  "kernel", "firmware", "drive", "sensor")),
]

# Customer log-source names -> telemetry categories they provide.
_LOG_SOURCE_RULES = [
    (("sysmon",), {"endpoint", "registry", "network"}),
    (("edr", "crowdstrike", "falcon", "defender", "sentinelone", "sentinel one",
      "carbon black", "cortex", "xdr"), {"endpoint", "registry"}),
    (("windows event", "wineventlog", "winlog", "security log", "event log",
      "domain controller"), {"endpoint", "identity", "registry"}),
    (("auditd", "linux audit", "osquery"), {"endpoint"}),
    (("active directory", "okta", "entra", "azure ad", "idp", "sso", "auth",
      "identity"), {"identity"}),
    (("dns",), {"network"}),
    (("zeek", "bro", "netflow", "ndr", "pcap", "packet", "firewall", "palo",
      "fortigate", "fortinet", "network"), {"network"}),
    (("proxy", "swg", "web gateway", "waf", "iis", "apache", "nginx",
      "web server", "web"), {"application", "network"}),
    (("cloudtrail", "cloud trail", "azure activity", "gcp audit", "cloud audit",
      "aws config", "s3 access", "cloud"), {"cloud"}),
    (("kubernetes", "k8s", "container", "docker", "eks"), {"cloud"}),
    (("email", "message trace", "proofpoint", "mimecast", "exchange"), {"application"}),
    (("fim", "file integrity", "tripwire"), {"endpoint"}),
]

# Security-tooling names -> categories that tooling could be onboarded to provide.
_TOOLING_RULES = [
    (("edr", "crowdstrike", "falcon", "defender", "sentinelone", "sentinel one",
      "carbon black", "cortex", "xdr", "antivirus", "av"), {"endpoint", "registry"}),
    (("ndr", "network detection", "zeek", "corelight", "darktrace", "vectra",
      "netflow", "firewall"), {"network"}),
    (("email", "proofpoint", "mimecast", "email security"), {"application"}),
    (("proxy", "swg", "waf", "web gateway"), {"application", "network"}),
    (("casb", "cloud security", "wiz", "cspm"), {"cloud"}),
    (("iam", "pam", "identity", "okta", "entra", "cyberark"), {"identity"}),
    (("dlp",), {"endpoint"}),
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
