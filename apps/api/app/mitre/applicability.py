"""Pure applicability engine: environment dict -> per-technique N/A decisions.

Input contract (frozen 2026-08-01, see MITRE_PHASE_0_PROMPT.md):

    {
      "platforms": ["Windows", "Linux", ...],   # ATT&CK platform strings
      "has_ics_assets": False,                  # gates the ICS domain
      "has_managed_mobile": False,              # gates the Mobile domain
      "inventory_provided": True,               # False => filter nothing (loud assumption)
      "exclusions": [{"target": "T1200"|"mobile"|"macOS", "reason": "..."}],
    }

Output:

    {
      "na": {technique_id: {"reason": str, "kind": str,
                            "source": "derived"|"customer-declared"}},
      "assumptions": [str, ...],
      "applicable_domains": ["enterprise", ...],
    }

Revoked techniques are not part of the assessable register at all (their
mappings remap to successors in coverage), so they never appear in ``na``.
No app imports beyond attack_data; no I/O.
"""

from .attack_data import DEFAULT, DOMAINS, is_valid_technique_id

# Most specific reason wins: technique-scoped > platform-scoped >
# domain-scoped; within a scope, customer-declared beats derived.
_RANK = {
    "excluded_technique": 60,
    "deprecated": 50,
    "excluded_platform": 40,
    "platform": 35,
    "excluded_domain": 30,
    "domain": 25,
}

_DOMAIN_GATE_REASON = {
    "ics": "ICS matrix: no OT/ICS assets declared in inventory",
    "mobile": "Mobile matrix: no managed mobile fleet declared in inventory",
}

NO_INVENTORY_ASSUMPTION = (
    "no environment inventory provided — full matrices assumed applicable; "
    "coverage % is a lower bound"
)
NO_PLATFORMS_ASSUMPTION = (
    "no platforms declared in the environment inventory — platform filtering "
    "skipped; coverage % is a lower bound"
)


def compute_applicability(environment: dict, index=None) -> dict:
    index = index if index is not None else DEFAULT
    env = environment or {}
    env_platforms = {str(p).strip().lower() for p in env.get("platforms") or [] if p}
    inventory_provided = env.get("inventory_provided", True)
    assumptions = []
    na = {}

    def propose(tech_id, kind, reason, source):
        current = na.get(tech_id)
        if current is None or _RANK[kind] > _RANK[current["kind"]]:
            na[tech_id] = {"reason": reason, "kind": kind, "source": source}

    # Classify customer exclusions by target scope.
    excl_techniques, excl_domains, excl_platforms = {}, {}, {}
    for row in env.get("exclusions") or []:
        target = str(row.get("target", "")).strip()
        reason = str(row.get("reason", "")).strip() or "no reason given"
        if not target:
            continue
        if is_valid_technique_id(target.upper()):
            tid = target.upper()
            if index.get(tid) is None:
                assumptions.append(
                    f"scope exclusion target {tid} not found in ATT&CK "
                    f"v{index.version} — ignored"
                )
            else:
                excl_techniques[tid] = reason
        elif target.lower() in DOMAINS:
            excl_domains[target.lower()] = reason
        else:
            excl_platforms[target.lower()] = reason

    if not inventory_provided:
        assumptions.append(NO_INVENTORY_ASSUMPTION)
    elif not env_platforms:
        assumptions.append(NO_PLATFORMS_ASSUMPTION)
    platform_filtering = inventory_provided and bool(env_platforms)

    domain_gated = set()
    if inventory_provided:
        if not env.get("has_ics_assets"):
            domain_gated.add("ics")
        if not env.get("has_managed_mobile"):
            domain_gated.add("mobile")

    for tech in index.techniques():
        if tech.get("revoked"):
            continue
        tid, domain = tech["id"], tech["domain"]
        tech_platforms = tech.get("platforms") or []

        if tid in excl_techniques:
            propose(tid, "excluded_technique", excl_techniques[tid], "customer-declared")
        elif tech.get("parent_id") in excl_techniques:  # parent exclusion covers subs
            propose(
                tid,
                "excluded_technique",
                excl_techniques[tech["parent_id"]],
                "customer-declared",
            )

        if tech.get("deprecated"):
            propose(tid, "deprecated", f"deprecated in ATT&CK v{index.version}", "derived")

        if domain in excl_domains:
            propose(tid, "excluded_domain", excl_domains[domain], "customer-declared")
        if domain in domain_gated:
            propose(tid, "domain", _DOMAIN_GATE_REASON[domain], "derived")

        # Platform rules — only within domains still being assessed: a gated
        # or customer-excluded domain already blankets its techniques with the
        # more meaningful domain-level reason. "PRE" (reconnaissance/resource
        # development) and "None" (every ICS technique in v19.1) are
        # environment-independent markers, not real platforms — techniques
        # carrying only those are never platform-filtered.
        domain_out = domain in domain_gated or domain in excl_domains
        filterable = [p for p in tech_platforms if p.lower() not in ("pre", "none")]
        if filterable and not domain_out:
            present = (
                [p for p in filterable if p.lower() in env_platforms]
                if platform_filtering
                else list(filterable)
            )
            if platform_filtering and not present:
                if len(filterable) == 1:
                    reason = (
                        f"targets {filterable[0]}; "
                        f"{filterable[0]} not in asset inventory"
                    )
                else:
                    reason = (
                        f"targets {', '.join(filterable)}; "
                        "none in asset inventory"
                    )
                propose(tid, "platform", reason, "derived")
            elif present and all(p.lower() in excl_platforms for p in present):
                reasons = []
                for p in present:  # keep first-seen order, dedupe reasons
                    r = excl_platforms[p.lower()]
                    if r not in reasons:
                        reasons.append(r)
                propose(tid, "excluded_platform", "; ".join(reasons), "customer-declared")

    applicable_domains = [
        d
        for d in index.domains
        if d not in excl_domains and d not in domain_gated
    ]
    return {
        "na": na,
        "assumptions": assumptions,
        "applicable_domains": applicable_domains,
    }
