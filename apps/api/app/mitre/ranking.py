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
from datetime import date, datetime

from .attack_data import DEFAULT, load_technique_priorities, load_threat_profiles
from .ingest import _match_platform as _asset_platform, _norm as _asset_norm

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
    # Sentinel/Defender-native TABLE names — real Sentinel workbooks name
    # sources by table ("Sentinel table - SecurityEvent"), which none of the
    # product-name keywords above match (the 2026-08-13 VFQ review: the only
    # endpoint provider it could name was an email table).
    (("securityevent", "windowsevent", "wineventlog"),
     {"endpoint", "identity", "registry"}),
    (("deviceprocessevents", "devicefileevents", "deviceimageloadevents",
      "deviceevents"), {"endpoint"}),
    (("deviceregistryevents",), {"endpoint", "registry"}),
    (("syslog",), {"endpoint"}),
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

# Crown-jewel free-text entries -> derived ATT&CK platform names and/or the
# telemetry categories above (Phase A4). Deterministic, curated, reuses the
# exact same platform/category vocab the rest of the module already uses —
# no new taxonomy invented. Unmatched entries are the caller's job to
# surface as a single assumption line, never an error (see crown_jewel_hints).
_CROWN_JEWEL_RULES = [
    (("vcenter", "esxi", "vsphere"), {"platforms": {"ESXi"}}),
    (("database", "sql server", "oracle db", "postgres", "mysql", "mongodb",
      "data warehouse"), {"categories": {"application", "cloud"}}),
    (("payment", "pos system", "card processing", "payment gateway"),
     {"categories": {"application"}}),
    (("domain controller", "active directory", "adfs"), {"categories": {"identity"}}),
    (("kubernetes", "k8s", "container platform"), {"platforms": {"Containers"}}),
    (("s3 bucket", "cloud storage", "blob storage", "data lake"), {"categories": {"cloud"}}),
    (("email server", "exchange server", "mail server"), {"categories": {"application"}}),
    (("erp", "sap", "financial system", "financial platform"), {"categories": {"application"}}),
    (("scada", "plc", "historian", "ot network"), {"categories": {"ot"}}),
    (("windows server", "file server"), {"platforms": {"Windows"}}),
    (("linux server",), {"platforms": {"Linux"}}),
]


def crown_jewel_hints(entries) -> tuple:
    """Crown-jewel free-text entries -> ({"platforms": set, "categories":
    set}, [unmatched entry, ...]). Pure keyword bridge, same discipline as
    _categories_provided — SUBSTRING match over the normalized entry text.
    An entry can match more than one rule; an entry matching nothing is
    returned verbatim for a single assumption line."""
    platforms, categories, unmatched = set(), set(), []
    for entry in entries or []:
        norm = _norm(entry)
        hit = False
        for keywords, hints in _CROWN_JEWEL_RULES:
            if any(kw in norm for kw in keywords):
                platforms |= hints.get("platforms", set())
                categories |= hints.get("categories", set())
                hit = True
        # Fallback (2026-08-13): bridge through the SAME platform normalizer
        # the Assets sheet uses, so real inventory phrasing like
        # "IP Network: Fortinet (36 devices)" matches instead of landing in
        # unmatched (28 of VFQ's 30 crown-jewel entries missed the curated
        # rules above).
        platform = _asset_platform(_asset_norm(entry))
        if platform:
            platforms.add(platform)
            hit = True
        if not hit:
            unmatched.append(str(entry))
    return {"platforms": platforms, "categories": categories}, unmatched


def _technique_categories(tech: dict) -> list:
    """ATT&CK data-source components -> coarse telemetry categories for one
    technique (same mapping quality.py uses for its own, unrelated,
    telemetry-match scoring — kept local here to avoid a quality<->ranking
    import cycle, since quality.py already imports FROM ranking.py)."""
    categories = []
    for component in tech.get("data_sources") or []:
        category = component_category(component)
        if category and category not in categories:
            categories.append(category)
    return categories


def _norm(value) -> str:
    return re.sub(r"\s+", " ", re.sub(r"[^a-z0-9 ]", " ", str(value or "").lower())).strip()


# Phase A6: a log source's Last Event Seen is expected to be near-continuous
# (unlike a use-case rule's Last Triggered, which can legitimately go
# months between fires) — a much shorter staleness window.
_STALE_LOG_SOURCE_DAYS = 30
_DATE_FORMATS = ("%Y-%m-%d", "%m/%d/%Y", "%d/%m/%Y", "%Y/%m/%d")


def _is_stale_last_event(value) -> bool:
    """True when a Last Event Seen cell is the literal 'never' or a
    parseable date older than the staleness window. Unparseable/blank ->
    False (no claim, never an error)."""
    if not value:
        return False
    text = str(value).strip()
    if text.lower() == "never":
        return True
    for fmt in _DATE_FORMATS:
        try:
            parsed = datetime.strptime(text, fmt).date()
            return (date.today() - parsed).days > _STALE_LOG_SOURCE_DAYS
        except ValueError:
            continue
    return False


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


def _feasibility(tech: dict, onboarded: dict, ownable: dict, log_source_health: dict = None):
    """(bucket, via, category, hint) for one technique.

    Phase A6: when the onboarded source for a category has an optional
    health record (Normalized=N and/or a stale Last Event Seen from the Log
    Sources sheet), downgrade short -> mid with the reason in the hint —
    absent health data changes nothing (log_source_health defaults to {}).
    """
    log_source_health = log_source_health or {}
    counts: dict = {}
    for component in tech.get("data_sources") or []:
        category = component_category(component)
        if category:
            counts[category] = counts.get(category, 0) + 1
    # Dominant category first: a technique whose components are mostly
    # endpoint must not get its via/hint from a lone application-log
    # component (2026-08-13 VFQ review: T1685.005 Clear Windows Event Logs
    # was recommended on an email table). Ties keep component order.
    first_seen = list(counts)
    categories = sorted(counts, key=lambda c: (-counts[c], first_seen.index(c)))
    if not categories:
        return (
            "long", None, None,
            "ATT&CK lists no standard telemetry for this technique — needs "
            "bespoke detection engineering",
        )
    for category in categories:
        if category in onboarded:
            source = onboarded[category]
            health = log_source_health.get(source)
            if health and (health.get("normalized") is False or _is_stale_last_event(health.get("last_event_seen"))):
                reasons = []
                if health.get("normalized") is False:
                    reasons.append("not normalized")
                if _is_stale_last_event(health.get("last_event_seen")):
                    reasons.append("no recent events seen")
                return (
                    "mid", source, category,
                    f"{source} covers {category} but is {' and '.join(reasons)} — "
                    "fix the pipeline before relying on this detection",
                )
            return (
                "short", source, category,
                f"telemetry already onboarded ({source} covers "
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


def technique_feasibility(tech: dict, log_sources, tooling, log_source_health: dict = None):
    """(bucket, via, category, hint) for one technique outside the gap list —
    Phase 14a drawer explain for covered/N-A techniques (gaps already carry
    the same fields from rank_gaps)."""
    onboarded = _categories_provided(log_sources, _LOG_SOURCE_RULES)
    ownable = _categories_provided(tooling, _TOOLING_RULES)
    return _feasibility(tech, onboarded, ownable, log_source_health)


def _region_word_match(keyword: str, text: str) -> bool:
    """Whole-word/phrase match — short codes like 'us'/'uk'/'eu' must not
    fire inside unrelated words ('us' inside 'australia', 'eu' inside
    'europe' itself is fine since 'europe' is matched as its own keyword,
    not via 'eu' substring)."""
    return bool(re.search(rf"(?<![a-z0-9]){re.escape(keyword)}(?![a-z0-9])", text))


def build_threat_profile(industry, actors, region=None, profiles=None) -> dict:
    """Intake industry/actor/region selections -> {"techniques": {tid:
    [labels]}, "labels": [...]} for threat-informed weighting (Phase 11;
    region added Phase A8). Pure lookup over the curated
    threat_profiles.json; an unknown industry, actor, or region
    contributes nothing (deliberate no-op — profiles are curated, never
    guessed). Exact technique IDs only: a profile listing T1566.001 lifts
    that sub-technique, not its parent. `region` is free text (intake's
    200-char field) — matched by whole-word/phrase keyword against a
    coarse curated set (NA/Europe/APAC/MEA/LATAM); a match pulls in the
    SAME actor profiles a customer could pick explicitly, so it's a third
    input into the SAME within-tier lift — no new sort key, no % change.
    """
    if profiles is None:
        profiles = load_threat_profiles()
    relevant, labels = {}, []

    def _add(entry, label):
        if label not in labels:
            labels.append(label)
        for tid in entry.get("techniques", []):
            tid_labels = relevant.setdefault(tid, [])
            if label not in tid_labels:
                tid_labels.append(label)

    aliases = profiles.get("industry_aliases", {})
    key = str(industry or "").strip().lower()
    entry = profiles.get("industries", {}).get(aliases.get(key, key))
    if entry:
        _add(entry, entry.get("label") or str(industry))
    actor_map = profiles.get("actors", {})
    for actor in actors or []:
        entry = actor_map.get(str(actor).strip())
        if entry:
            _add(entry, str(actor).strip())

    region_text = _norm(region)
    if region_text:
        for region_profile in profiles.get("region_profiles") or []:
            if any(_region_word_match(kw, region_text) for kw in region_profile.get("keywords", [])):
                region_label = region_profile.get("label")
                if region_label and region_label not in labels:
                    labels.append(region_label)
                for actor_name in region_profile.get("actors", []):
                    actor_entry = actor_map.get(actor_name)
                    if actor_entry:
                        _add(actor_entry, actor_name)
                break  # first matching region wins — regions don't overlap
    return {"techniques": relevant, "labels": labels}


def rank_gaps(
    techniques, log_sources, tooling, *,
    index=None, priorities=None, profile=None, threat_weighting=True,
    crown_jewels=None, crown_jewel_weighting=True, log_source_health=None,
) -> dict:
    """Coverage per-technique results -> ranked gap list + roadmap buckets.

    techniques: coverage.compute_coverage()["techniques"].
    log_sources/tooling: raw customer rows from the environment workbook.
    profile: build_threat_profile() output (or None) — matching gaps carry
    threat_relevance labels and, when threat_weighting is on (org tunable
    `threat_weighting_enabled`, default on), rank above EQUAL-TIER peers.
    crown_jewels: raw Crown Jewels sheet rows (or None) — Phase A4. Matching
    gaps carry crown_jewel_relevant=True and, when crown_jewel_weighting is
    on (org tunable `crown_jewel_weighting_enabled`, default on), rank above
    equal-tier peers — a THIRD sort key, after tier and threat_relevance,
    never a tier jump. log_source_health: Phase A6, {entry name: {parser_
    format, normalized, last_event_seen}} from the Log Sources sheet's
    optional health columns (or None) — downgrades that source's short
    feasibility to mid with the reason in the hint when normalized=False
    or the last event looks stale; absent -> no change to feasibility.
    Never changes coverage %, states, or tier.
    Returns {"gaps": [gap...], "roadmap": {"short": [...], "mid": [...],
    "long": [...]}, "crown_jewel_unmatched": [str, ...]} — gap dicts carry
    technique_id, name, domain, state, tier, tactics, feasibility, via,
    category, hint, threat_relevance, crown_jewel_relevant, rank.
    """
    index = index if index is not None else DEFAULT
    if priorities is None:
        priorities = load_technique_priorities()
    tier_by_id = {t["technique_id"]: t["tier"] for t in priorities.get("techniques", [])}

    onboarded = _categories_provided(log_sources, _LOG_SOURCE_RULES)
    ownable = _categories_provided(tooling, _TOOLING_RULES)
    cj_hints, cj_unmatched = crown_jewel_hints(crown_jewels)

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
        bucket, via, category, hint = _feasibility(tech, onboarded, ownable, log_source_health)
        positions = [
            tactic_position.get((result["domain"], t), 99) for t in result["tactics"]
        ] or [99]
        relevance = (profile or {}).get("techniques", {}).get(result["technique_id"])
        crown_jewel_relevant = bool(
            set(tech.get("platforms") or []) & cj_hints["platforms"]
            or set(_technique_categories(tech)) & cj_hints["categories"]
        )
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
                "threat_relevance": relevance or None,
                "crown_jewel_relevant": crown_jewel_relevant,
                "_tactic_pos": min(positions),
            }
        )

    gaps.sort(
        key=lambda g: (
            g["tier"],
            # Phase 11: threat-informed lift WITHIN a tier — a gap on the
            # customer's industry/actor profile beats equal-tier peers but
            # never jumps a tier (and never touches coverage numbers).
            0 if (threat_weighting and g["threat_relevance"]) else 1,
            # Phase A4: crown-jewel lift, same within-tier pattern, one step
            # further down the sort key so it never overrides threat weighting.
            0 if (crown_jewel_weighting and g["crown_jewel_relevant"]) else 1,
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
    return {"gaps": gaps, "roadmap": roadmap, "crown_jewel_unmatched": cj_unmatched}
