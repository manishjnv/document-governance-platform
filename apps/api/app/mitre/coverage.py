"""Pure coverage computation: use-case list + applicability -> states + rollups.

Use-case contract (frozen 2026-08-01, see MITRE_PHASE_0_PROMPT.md):

    {
      "row_ref": "sheet1:14",
      "name": "Suspicious PowerShell EncodedCommand",
      "enabled": True,          # None = unknown (treated as enabled + assumption)
      "mappings": [{"technique_id": "T1059.001", "source": "customer"|"ai",
                    "confidence": 1.0}],
    }

Semantics (plan §7):
- covered: >=1 enabled mapping with confidence >= COVERED_CONFIDENCE.
- partial: only disabled-rule mappings, or only mid-confidence
  [PARTIAL_CONFIDENCE, COVERED_CONFIDENCE) mappings.
- mappings below PARTIAL_CONFIDENCE don't count at all.
- ``disabled_counts_as_coverage`` (org policy, default No) promotes
  qualifying disabled-rule mappings to covered.
- parent with no direct qualifying mapping but >=1 covered sub-technique
  reports partial; both levels appear in results.
- multi-tactic techniques count in every tactic they belong to.
- headline % = covered / applicable (strict); weighted % credits partial
  at PARTIAL_WEIGHT.
- revoked techniques are not part of the register; mappings to them remap
  to their successor.

Inputs/outputs are plain dicts/lists — no ORM, no app imports beyond
attack_data.
"""

from collections import Counter

from .attack_data import DEFAULT

COVERED_CONFIDENCE = 0.7
PARTIAL_CONFIDENCE = 0.4
PARTIAL_WEIGHT = 0.5


def _state_from_hits(hits, disabled_counts_as_coverage, covered_conf, partial_conf):
    if any(
        h["confidence"] >= covered_conf
        and (h["enabled"] or disabled_counts_as_coverage)
        for h in hits
    ):
        return "covered"
    if any(
        (h["confidence"] >= covered_conf and not h["enabled"])
        or partial_conf <= h["confidence"] < covered_conf
        for h in hits
    ):
        return "partial"
    return "not_covered"


def _rollup(results, partial_weight):
    states = Counter(r["state"] for r in results)
    covered, partial = states["covered"], states["partial"]
    applicable = len(results) - states["not_applicable"]
    return {
        "covered": covered,
        "partial": partial,
        "not_covered": states["not_covered"],
        "not_applicable": states["not_applicable"],
        "applicable": applicable,
        "strict_pct": round(100 * covered / applicable, 1) if applicable else 0.0,
        "weighted_pct": (
            round(100 * (covered + partial_weight * partial) / applicable, 1)
            if applicable
            else 0.0
        ),
    }


def compute_coverage(
    use_cases,
    applicability,
    *,
    disabled_counts_as_coverage: bool = False,
    covered_confidence: float = None,
    partial_confidence: float = None,
    partial_weight: float = None,
    index=None,
) -> dict:
    # Optional org-tunable overrides (mitre_settings, wired in Phase 1);
    # None means the module defaults.
    covered_confidence = (
        COVERED_CONFIDENCE if covered_confidence is None else covered_confidence
    )
    partial_confidence = (
        PARTIAL_CONFIDENCE if partial_confidence is None else partial_confidence
    )
    partial_weight = PARTIAL_WEIGHT if partial_weight is None else partial_weight
    index = index if index is not None else DEFAULT
    na = (applicability or {}).get("na", {})
    assumptions = list((applicability or {}).get("assumptions", []))

    def note(line):
        if line not in assumptions:
            assumptions.append(line)

    # canonical technique id -> [{"row_ref", "enabled", "confidence"}]
    hits = {}
    for uc in use_cases or []:
        row_ref = uc.get("row_ref") or uc.get("name") or "?"
        enabled = uc.get("enabled")
        if enabled is None:
            enabled = True
            note(
                f"rule '{uc.get('name') or row_ref}' ({row_ref}): enabled/disabled "
                "status unknown — treated as enabled"
            )
        for mapping in uc.get("mappings") or []:
            raw_id = str(mapping.get("technique_id", "")).strip().upper()
            canonical, status = index.resolve(raw_id)
            if status in ("malformed", "unknown"):
                note(
                    f"mapping '{raw_id}' on {row_ref} is not a valid ATT&CK "
                    f"v{index.version} technique — ignored"
                )
                continue
            if status == "remapped":
                # customer-facing wording (2026-08-18 feedback): never say
                # "revoked" — it reads like an error, not a framework update
                successor = (index.get(canonical) or {}).get("name")
                note(
                    f"MITRE ATT&CK update: {raw_id} (tagged on {row_ref}) has "
                    f"been restructured and is now represented under "
                    f"{canonical}{f' ({successor})' if successor else ''} in "
                    f"ATT&CK v{index.version} — the detection counts toward "
                    f"{canonical}; this is a framework update, not a gap"
                )
            confidence = mapping.get("confidence")
            if confidence is None:
                confidence = 1.0 if mapping.get("source") == "customer" else 0.0
            hits.setdefault(canonical, []).append(
                {"row_ref": row_ref, "enabled": enabled, "confidence": float(confidence)}
            )

    results = []
    by_id = {}
    for tech in index.techniques():
        if tech.get("revoked"):
            continue
        tid = tech["id"]
        if tid in na:
            state, na_reason = "not_applicable", na[tid]["reason"]
        else:
            state = _state_from_hits(
                hits.get(tid, []),
                disabled_counts_as_coverage,
                covered_confidence,
                partial_confidence,
            )
            na_reason = None
        entry = {
            "technique_id": tid,
            "domain": tech["domain"],
            "tactics": tech.get("tactics", []),
            "state": state,
            "na_reason": na_reason,
            "use_case_refs": sorted({h["row_ref"] for h in hits.get(tid, [])}),
        }
        results.append(entry)
        by_id[tid] = entry

    # Sub-technique rollup: parent with no direct qualifying mapping but >=1
    # covered sub-technique reports partial at parent level.
    for entry in results:
        tech = index.get(entry["technique_id"])
        if tech.get("is_subtechnique") or entry["state"] != "not_covered":
            continue
        for sub in index.children.get(entry["technique_id"], []):
            sub_entry = by_id.get(sub["id"])
            if sub_entry and sub_entry["state"] == "covered":
                entry["state"] = "partial"
                break

    domains = {}
    for domain in index.domains:
        domain_results = [r for r in results if r["domain"] == domain]
        tactic_rollups = []
        for tactic in index.tactics(domain):
            in_tactic = [r for r in domain_results if tactic["id"] in r["tactics"]]
            tactic_rollups.append({**tactic, **_rollup(in_tactic, partial_weight)})
        domains[domain] = {
            **_rollup(domain_results, partial_weight),
            "tactics": tactic_rollups,
        }

    return {
        "attack_version": index.version,
        "params": {
            "disabled_counts_as_coverage": disabled_counts_as_coverage,
            "covered_confidence": covered_confidence,
            "partial_confidence": partial_confidence,
            "partial_weight": partial_weight,
        },
        "overall": _rollup(results, partial_weight),
        "domains": domains,
        "techniques": results,
        "assumptions": assumptions,
    }
