"""Constants/helpers shared between report.py (HTML/PDF) and report_xlsx.py
(XLSX) — split out in Phase 14h so neither builder has to import the other
(report.py re-exports these names so existing imports/tests are unaffected).
"""

import re

STATE_LABELS = {
    "covered": "Covered",
    "partial": "Partial",
    "not_covered": "Not covered",
    "not_applicable": "N/A",
}
FEASIBILITY_LABELS = {"short": "Short term (0–3 mo)", "mid": "Mid term (3–9 mo)", "long": "Long term (9–18 mo)"}
DOMAIN_LABELS = {"enterprise": "Enterprise", "ics": "ICS / OT", "mobile": "Mobile"}
# Shared between the HTML appendix's "Status" column and the XLSX
# Use-Case Mappings sheet — despite the name, not XLSX-only.
_MAPPING_STATUS_PLAIN_XLSX = {
    "customer_tagged": "You tagged this",
    "keyword_tagged": "Matched by tool/technique keyword (no AI)",
    "ai_tagged": "AI-suggested — verify",
    "manual": "Edited by a reviewer",
    "tool_attested": "Tool-attested — alert path confirmed",
    "unmapped": "Could not be mapped",
    "invalid": "Tags were invalid — treated as untagged",
}
# Canonical display order: the stored summary follows the ATT&CK dataset's
# dict order (ICS, Mobile, Enterprise), which buries Enterprise last.
_DOMAIN_ORDER = ("enterprise", "ics", "mobile")


# ---- 2026-08-18 uplift: data builders shared by the PDF AND the PPTX ------
# (pure data, no markup — each format renders its own way, but the numbers
# and derivations are computed exactly once, here)

def rule_health(use_cases: list) -> tuple:
    """(disabled_rules, never_fired_enabled_rules) from the export's own
    Status / Last Triggered columns."""
    disabled = [uc for uc in use_cases if uc.get("enabled") is False]
    never_fired = [
        uc for uc in use_cases
        if uc.get("enabled")
        and str(uc.get("last_triggered") or "").strip().lower()
        in ("never", "never triggered")
    ]
    return disabled, never_fired


def compute_moves(roadmap: dict, disabled_count: int, never_fired_count: int) -> list:
    """The 'three moves' shown on the board and closing pages — plain
    deterministic strings, priority order."""
    moves = []
    if disabled_count:
        moves.append(
            f"Review the {disabled_count} disabled rules — enabling the "
            "right ones is the cheapest coverage you can buy."
        )
    short_gaps = roadmap.get("short") or []
    if short_gaps:
        g0 = short_gaps[0]
        moves.append(
            f"Build the {g0.get('technique_id')} ({g0.get('name')}) detection "
            "first"
            + (f" — it uses {g0.get('via')}, which you already collect."
               if g0.get("via") else ".")
        )
    if never_fired_count:
        moves.append(
            f"Test the {never_fired_count} enabled rules that have never "
            "fired — they count as coverage today, unproven."
        )
    for g in short_gaps[1:] + (roadmap.get("mid") or []):
        if len(moves) >= 3:
            break
        moves.append(f"Then build {g.get('technique_id')} ({g.get('name')}).")
    return moves[:3]


def covered_split(technique_results: list) -> tuple:
    """(rule_covered, tool_attested_covered) among covered techniques. A
    covered technique counts as tool-attested when ALL of its supporting
    rules are attestation rows (row_ref 'attest:N') — any real SIEM rule
    on it keeps it in the rule-covered count."""
    rule_n = tool_n = 0
    for r in technique_results or []:
        if r.get("state") != "covered":
            continue
        refs = r.get("use_case_refs") or []
        if refs and all(str(x).startswith("attest:") for x in refs):
            tool_n += 1
        else:
            rule_n += 1
    return rule_n, tool_n


def compute_tool_overlay(tooling_entries: list, technique_results: list):
    """Tool-native detection credit (MITRE_TOOL_COVERAGE_PLAN.md), computed
    at read/render time — pure lookup over the declared Security Tooling
    entries x stored technique states, so it applies to every existing
    assessment with no pipeline or storage change.

    Returns None when no declared tool matches the curated map. Otherwise:
    {matched_tools: [{label, source, url}], unmatched: [entry, ...],
     by_technique: {tid: [label, ...]},   # only open/partial techniques
     extra_open_covered: int,             # not_covered but tool-evaluated
     adjusted_pct: float|None,            # (covered + extra) / applicable
     caveat: str}
    Invariant: adjusted_pct is a SECOND labeled number — callers must never
    replace the rule-based coverage figure with it."""
    from app.mitre import attack_data

    cfg = attack_data.load_tool_coverage()
    tools_cfg = cfg.get("tools") or {}
    core = cfg.get("core_evaluated_techniques") or []
    matched_tools, unmatched, seen_labels = [], [], set()
    tech_map: dict = {}
    for entry in tooling_entries or []:
        text = str(entry).strip()
        low = text.lower()
        hit = None
        for key, tool in tools_cfg.items():
            names = [key] + [str(s).lower() for s in tool.get("synonyms") or []]
            if any(n and (n in low or low == n) for n in names):
                hit = tool
                break
        if hit is None:
            unmatched.append(text)
            continue
        label = hit["label"]
        if label in seen_labels:
            continue
        seen_labels.add(label)
        matched_tools.append(
            {"label": label, "source": hit.get("source"), "url": hit.get("url")}
        )
        for tid in hit.get("techniques") or core:
            canonical, status = attack_data.DEFAULT.resolve(str(tid))
            if status in ("ok", "remapped"):
                tech_map.setdefault(canonical, [])
                if label not in tech_map[canonical]:
                    tech_map[canonical].append(label)
    if not matched_tools:
        return None

    by_technique: dict = {}
    covered = applicable = extra = 0
    for r in technique_results or []:
        state = r.get("state")
        if state in ("covered", "partial", "not_covered"):
            applicable += 1
        if state == "covered":
            covered += 1
        labels = tech_map.get(r.get("technique_id"))
        if labels and state in ("partial", "not_covered"):
            by_technique[r.get("technique_id")] = labels
            if state == "not_covered":
                extra += 1
    return {
        "matched_tools": matched_tools,
        "unmatched": unmatched,
        "by_technique": by_technique,
        "extra_open_covered": extra,
        "adjusted_pct": (
            round(100 * (covered + extra) / applicable, 1) if applicable else None
        ),
        "caveat": cfg.get("caveat") or "",
    }


def top10_vs_you(state_by_id: dict, index) -> dict:
    """The curated most-prevalent-techniques list joined against this
    assessment's real states. rows: (rank, canonical_id, name, state|None)."""
    from app.mitre import attack_data

    cfg = attack_data.load_top_attacker_techniques()
    rows, covered, partial = [], 0, 0
    for entry in cfg.get("techniques", []):
        canonical, status = index.resolve(str(entry.get("id")))
        state = state_by_id.get(canonical) if status in ("ok", "remapped") else None
        if state == "covered":
            covered += 1
        elif state == "partial":
            partial += 1
        name = (index.get(canonical) or {}).get("name") or entry.get("name")
        rows.append((entry.get("rank"), canonical or entry.get("id"), name, state))
    return {
        "source": cfg.get("source"), "year": cfg.get("year"),
        "source_note": cfg.get("source_note"), "url": cfg.get("url"),
        "rows": rows, "covered": covered, "partial": partial,
    }


def adversary_spotlight(intake: dict, state_by_id: dict, index, tactic_order: list):
    """Chosen threat actor (or industry profile) joined against real states.
    Returns None when intake names neither, or nothing in the profile is in
    scope. strip: (tactic_name, covered_count, in_scope_count) in kill-chain
    order."""
    from app.mitre import attack_data

    profiles = attack_data.load_threat_profiles()
    actors_cfg = profiles.get("actors") or {}
    industries_cfg = profiles.get("industries") or {}
    aliases = profiles.get("industry_aliases") or {}
    chosen_actor = next(
        (a for a in (intake.get("threat_actors") or []) if a in actors_cfg), None
    )
    if chosen_actor:
        actor = actors_cfg[chosen_actor]
        spot = {
            "title": chosen_actor
            + (f" ({actor.get('attack_id')})" if actor.get("attack_id") else ""),
            "attack_id": actor.get("attack_id"),
            "sub": actor.get("note") or "",
            "tids": actor.get("techniques") or [],
            "source": "Technique list: MITRE ATT&CK Groups + the curated "
                      "threat profiles shipped with this product (public "
                      "reporting cited in-file)",
        }
    else:
        industry_key = aliases.get(
            (intake.get("industry") or "").strip().lower(),
            (intake.get("industry") or "").strip().lower(),
        )
        if industry_key not in industries_cfg:
            return None
        entry = industries_cfg[industry_key]
        spot = {
            "title": f"Attacks on {entry.get('label')}",
            "attack_id": None,
            "sub": "The techniques most reported in attacks on your industry.",
            "tids": entry.get("techniques") or [],
            "source": f"Sources: {entry.get('sources')}",
        }

    resolved = []
    for tid in spot["tids"]:
        canonical, status = index.resolve(str(tid))
        if status in ("ok", "remapped") and canonical not in resolved:
            resolved.append(canonical)
    detected = [t for t in resolved if state_by_id.get(t) == "covered"]
    partial_hits = [t for t in resolved if state_by_id.get(t) == "partial"]
    blind = [t for t in resolved if state_by_id.get(t) == "not_covered"]
    in_scope = len(detected) + len(partial_hits) + len(blind)
    if not in_scope:
        return None
    strip = []
    for t in tactic_order:
        relevant = [
            tid for tid in resolved
            if t.get("id") in ((index.get(tid) or {}).get("tactics") or [])
            and state_by_id.get(tid) in ("covered", "partial", "not_covered")
        ]
        if relevant:
            hit = sum(1 for tid in relevant if state_by_id.get(tid) == "covered")
            strip.append((t.get("name"), hit, len(relevant)))
    return {
        **spot, "detected": detected, "partial_hits": partial_hits,
        "blind": blind, "in_scope": in_scope, "strip": strip,
    }


def _ordered_domains(domains: dict):
    return sorted(
        (domains or {}).items(),
        key=lambda kv: _DOMAIN_ORDER.index(kv[0]) if kv[0] in _DOMAIN_ORDER else 99,
    )


def _row_ref_sort_key(uc: dict):
    """Numeric-aware sort for row refs ('Rules:2' before 'Rules:10')."""
    import re as _re

    ref = str(uc.get("row_ref") or "")
    return (
        _re.sub(r"\d+", "#", ref),
        [int(n) for n in _re.findall(r"\d+", ref)],
    )


# --- Phase 14h: report branding -------------------------------------------
# Keys mirror app.mitre.service.SETTING_DEFAULTS's report_* tunables, kept
# as literal defaults here (not imported from service.py) so this leaf
# module doesn't pull in the settings/pipeline import graph.
DEFAULT_BRANDING = {
    # Unbranded by default (2026-08-18 user request): generated reports
    # carry no product name unless the org sets report_display_name.
    "report_display_name": "",
    "report_accent_color": "#0057B8",
    "report_watermark_text": "",
}

_HEX_COLOR_RE = re.compile(r"^#[0-9A-Fa-f]{6}$")


def resolve_branding(branding: dict | None) -> dict:
    """Merge caller-supplied branding overrides over the platform defaults.

    The accent color is re-validated here (not just at settings-write time
    in service.validate_setting) because report.py interpolates it directly
    into a <style> block as a CSS color token — HTML-escaping (_esc) is the
    wrong defense for a CSS context, so a strict hex-color allowlist regex
    is used instead, falling back to the platform default on any mismatch.
    """
    merged = {**DEFAULT_BRANDING, **(branding or {})}
    color = merged.get("report_accent_color")
    if not isinstance(color, str) or not _HEX_COLOR_RE.match(color):
        merged["report_accent_color"] = DEFAULT_BRANDING["report_accent_color"]
    return merged


# --- Phase A10 piece 3: coverage by log source ----------------------------

OTHER_LOG_SOURCE = "Other / unrecognized"


def compute_log_source_coverage(use_cases, technique_results, index) -> list:
    """Deterministic read-time grouping (plan phase A10 piece 3): detection
    rules grouped by their log_source, normalized through ranking.py's own
    text normalizer (``ranking._norm`` — reused, never a second one) so
    case/punctuation variants of the same source collapse into one group;
    the group's display name is the first raw log_source text seen. Rules
    with no log_source (or nothing recognizable) land in
    ``OTHER_LOG_SOURCE`` — never dropped. No pipeline change: use_cases and
    technique_results are the exact same stored data every other read-time
    view (drill-downs, explain endpoint) already consumes.

    Returns [{"log_source", "rule_count", "techniques_covered", "tactics",
    "techniques": [{"technique_id", "name", "state"}], "row_refs": [...]}],
    sorted by rule count (desc) then log source name, with
    ``OTHER_LOG_SOURCE`` always last regardless of count. Pure; no AI.
    """
    from .ranking import _norm as _log_source_norm

    results_by_id = {r.get("technique_id"): r for r in technique_results or []}
    groups: dict = {}
    for uc in use_cases or []:
        raw = str(uc.get("log_source") or "").strip()
        key = _log_source_norm(raw) if raw else ""
        display = raw or OTHER_LOG_SOURCE
        bucket = groups.setdefault(
            key, {"display": display, "rule_count": 0, "technique_ids": set(), "row_refs": []}
        )
        bucket["rule_count"] += 1
        if uc.get("row_ref"):
            bucket["row_refs"].append(uc["row_ref"])
        for mapping in uc.get("mappings") or []:
            canonical, _status = index.resolve(
                str(mapping.get("technique_id", "")).strip().upper()
            )
            if canonical:
                bucket["technique_ids"].add(canonical)

    rows = []
    for bucket in groups.values():
        techniques = []
        tactics = set()
        for tid in sorted(bucket["technique_ids"]):
            result = results_by_id.get(tid)
            tech = index.get(tid) or {}
            techniques.append({
                "technique_id": tid,
                "name": tech.get("name", tid),
                "state": result.get("state") if result else None,
            })
            if result:
                tactic_names = {t["id"]: t["name"] for t in index.tactics(result.get("domain"))}
                tactics.update(
                    tactic_names[t] for t in (result.get("tactics") or []) if t in tactic_names
                )
        rows.append({
            "log_source": bucket["display"],
            "rule_count": bucket["rule_count"],
            "techniques_covered": len(techniques),
            "tactics": sorted(tactics),
            "techniques": techniques,
            "row_refs": bucket["row_refs"],
        })

    rows.sort(key=lambda r: (r["log_source"] == OTHER_LOG_SOURCE, -r["rule_count"], r["log_source"]))
    return rows
