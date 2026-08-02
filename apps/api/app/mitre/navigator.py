"""ATT&CK Navigator layer export (Phase 8, plan §14). Pure.

Builds one Navigator layer (layer format 4.5) per applicable domain from
the STORED technique_results — states are read as persisted, nothing
recomputed. Colors mirror the report palette so the Navigator view, the
in-app heatmap, and the PDF all tell the same story. Deterministic (no
timestamps): a layer for a given assessment is byte-stable.
"""

from .report import STATE_COLORS, STATE_LABELS

LAYER_FORMAT = "4.5"
NAVIGATOR_VERSION = "5.1.1"

DOMAIN_TO_NAVIGATOR = {
    "enterprise": "enterprise-attack",
    "ics": "ics-attack",
    "mobile": "mobile-attack",
}


def _comment(result: dict) -> str:
    if result.get("state") == "not_applicable":
        return result.get("na_reason") or "not applicable"
    count = len(result.get("use_case_refs") or [])
    return f"{count} mapped detection rule(s)" if count else ""


def build_navigator_layers(assessment) -> list:
    """-> [(domain_key, layer_dict)] for each applicable domain, in stable
    enterprise/ics/mobile order.

    assessment: MitreAssessment ORM row (or any object with name,
    attack_version, technique_results, summary).
    """
    results = assessment.technique_results or []
    summary = assessment.summary or {}
    applicable = summary.get("applicable_domains") or sorted(
        {r.get("domain") for r in results if r.get("domain")}
    )

    layers = []
    for domain in ("enterprise", "ics", "mobile"):
        if domain not in applicable:
            continue
        domain_results = [r for r in results if r.get("domain") == domain]
        if not domain_results:
            continue
        layers.append(
            (
                domain,
                {
                    "name": f"{assessment.name} — {domain}",
                    "versions": {
                        "attack": str(assessment.attack_version),
                        "navigator": NAVIGATOR_VERSION,
                        "layer": LAYER_FORMAT,
                    },
                    "domain": DOMAIN_TO_NAVIGATOR[domain],
                    "description": (
                        f"ScopeWise MITRE ATT&CK coverage assessment "
                        f"'{assessment.name}' (ATT&CK v{assessment.attack_version}). "
                        "Green = covered, amber = partial, red = not covered, "
                        "grey/disabled = not applicable."
                    ),
                    "techniques": [
                        {
                            "techniqueID": r["technique_id"],
                            "color": STATE_COLORS.get(r.get("state"), "#9ca3af"),
                            "comment": _comment(r),
                            "enabled": r.get("state") != "not_applicable",
                        }
                        for r in domain_results
                    ],
                    "legendItems": [
                        {"label": STATE_LABELS[state], "color": color}
                        for state, color in STATE_COLORS.items()
                    ],
                    "hideDisabled": False,
                },
            )
        )
    return layers
