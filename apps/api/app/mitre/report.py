"""MITRE assessment reports: exec+detailed HTML/PDF (the XLSX gap register
lives in report_xlsx.py — plan §10).

Numbers come ONLY from the stored summary/technique_results JSONB — never
recomputed here, never parsed out of narrative text. Every customer/LLM
string goes through _esc (HTML) or _guard (XLSX formula injection): rule
names, descriptions, exclusion reasons, and narrative output are all
attacker-controlled.

PDF rendering reuses the house WeasyPrint approach (app/scoring/report.py):
lazily imported because its native libs (Pango/Cairo) only exist in the
prod image — local dev fails soft at call time, not import time.

Phase 14h: the document skeleton (head/style/cover/executive/detail/
appendix/footer wrappers) renders via Jinja2 templates under ./templates/
so the report's look can be edited without touching this module. All
per-item HTML fragments (scorecard tiles, gap cards, table rows, ...) are
still built here as plain Python strings via _esc()/f-strings exactly as
before — Jinja only stitches the already-escaped fragments into the page
skeleton. The Jinja Environment below runs with autoescape=False: every
value handed to a template has already been through _esc() (or is a
static, developer-authored fragment with no user input), so this is
equivalent to the original f-string's escaping discipline, not a
regression — Jinja's own auto-escaping would double-encode content that
_esc() already encoded. This is not a template-injection risk either:
templates are loaded only from this package's local ./templates/
directory (never built from request/DB content), so the only
attacker-reachable surface is variable *values*, which _esc() already
neutralizes before they reach render().
"""

import base64
import logging
import os
import re
from datetime import datetime, timezone

import jinja2

from app.mitre.report_common import (
    DOMAIN_LABELS,
    FEASIBILITY_LABELS,
    STATE_LABELS,
    _MAPPING_STATUS_PLAIN_XLSX,
    _ordered_domains,
    _row_ref_sort_key,
    resolve_branding,
)
from app.mitre.report_xlsx import build_xlsx_export, _guard  # noqa: F401 (re-exported for callers/tests)
from app.mitre.report_pptx import build_pptx_export  # noqa: F401 (re-exported for callers/tests)
from app.scoring.report import _esc  # house escaper, stored-XSS lesson baked in

logger = logging.getLogger(__name__)

STATE_COLORS = {
    "covered": "#10b981",
    "partial": "#f59e0b",
    "not_covered": "#f43f5e",
    "not_applicable": "#9ca3af",
}

_TEMPLATES_DIR = os.path.join(os.path.dirname(__file__), "templates")
_JINJA_ENV = jinja2.Environment(
    loader=jinja2.FileSystemLoader(_TEMPLATES_DIR),
    autoescape=False,  # see module docstring: fragments are pre-escaped by _esc()
    trim_blocks=True,
    lstrip_blocks=True,
)

# Phase 14h: cover + running-header logo, embedded as a data URI so the PDF
# never fetches over the network (WeasyPrint would otherwise need base_url
# plumbing for a relative path). Loaded once at import time; a missing/
# unreadable asset degrades to no logo rather than failing report generation.
_LOGO_PATH = os.path.join(os.path.dirname(__file__), "assets", "scopewise-logo.png")
try:
    with open(_LOGO_PATH, "rb") as _f:
        LOGO_DATA_URI = "data:image/png;base64," + base64.b64encode(_f.read()).decode("ascii")
except OSError:
    logger.warning("MITRE report logo asset missing at %s — rendering without it", _LOGO_PATH)
    LOGO_DATA_URI = None

# PDF appendix cap — a 5,000-row use-case appendix belongs in the XLSX, not
# a PDF. The cap is stated in the report when it bites.
MAX_APPENDIX_ROWS = 500

# Per-tab PDF cuts (scope -> [start, end) markers inside the full document)
_SECTION_SCOPES = {
    "coverage": ('<h2 id="tactics"', '<h2 id="roadmap"'),
    "gaps": ('<h2 id="roadmap"', "<!-- ========================== APPENDICES"),
    "assumptions": ('<h2 id="na"', '<h2 id="mappings"'),
}

_NA_GROUPS = [
    ("Whole matrix not applicable", lambda r: "matrix:" in r),
    ("Platform not in the environment", lambda r: r.startswith("targets ")),
    ("Deprecated by MITRE", lambda r: r.startswith("deprecated in ATT&CK")),
    ("Customer-declared exclusions", lambda r: True),
]


def _pct_bar(pct: float, color: str = "#0057B8") -> str:
    width = max(0.0, min(100.0, float(pct or 0)))
    return (
        '<div style="background:#e5e7eb;border-radius:4px;height:10px;width:100%;">'
        f'<div style="background:{color};border-radius:4px;height:10px;width:{width}%;"></div></div>'
    )


# Filled state pills: amber needs dark text, the rest carry white.
_STATE_CHIP_TEXT = {"partial": "#713f12"}


def _state_chip(state: str) -> str:
    background = STATE_COLORS.get(state, "#6b7280")
    color = _STATE_CHIP_TEXT.get(state, "#ffffff")
    return (
        f'<span style="background:{background};color:{color};padding:1px 7px;'
        'border-radius:8px;font-size:10px;font-weight:600;white-space:nowrap;">'
        f"{_esc(STATE_LABELS.get(state, state))}</span>"
    )


def _traffic_color(pct) -> str:
    """Deterministic traffic-light band for the executive scorecard."""
    value = float(pct or 0)
    if value >= 50:
        return "#10b981"
    if value >= 15:
        return "#f59e0b"
    return "#f43f5e"


def _stacked_bar(covered, partial, not_covered, applicable) -> str:
    """CSS stacked horizontal bar for one tactic (deterministic widths)."""
    total = max(1, int(applicable or 0))
    seg = (
        "<span style='display:inline-block;height:9px;background:{c};width:{w}%;'></span>"
    )
    return (
        "<div style='background:#e5e7eb;border-radius:4px;height:9px;width:100%;"
        "font-size:0;line-height:0;overflow:hidden;'>"
        + seg.format(c="#10b981", w=round(100 * (covered or 0) / total, 2))
        + seg.format(c="#f59e0b", w=round(100 * (partial or 0) / total, 2))
        + seg.format(c="#f43f5e", w=round(100 * (not_covered or 0) / total, 2))
        + "</div>"
    )


def build_html_report(assessment, use_cases: list, compare=None, files=None,
                      scope="full", branding: dict | None = None) -> str:
    """Executive + detailed report as one self-contained HTML document
    (rebuilt in Phase 14e: cover → executive ≤2 pages → detailed →
    appendices, TOC with real page numbers, running header, deterministic
    HTML/CSS only — numbers come solely from the stored JSONB).

    assessment: MitreAssessment ORM row (or anything with the same
    attributes). use_cases: dicts {row_ref, name, description, log_source,
    enabled, mappings, mapping_status}. compare: optional
    service.compare_assessments() output (+ baseline_name) for the trend
    block. files: optional [{kind, filename, row_count}] for the cover.
    scope: "full" (default) | "executive" (cover + executive section only —
    the 1-3 page leadership PDF) | "coverage" / "gaps" / "assumptions"
    (title + just that tab's section, for per-tab downloads).
    branding: optional org overrides (display name/accent color/watermark
    text — plan §14h), merged over the platform defaults.
    """
    from app.mitre import attack_data, plain_language

    branding = resolve_branding(branding)
    summary = assessment.summary or {}
    params = assessment.params or {}
    overall = summary.get("overall", {})
    domains = summary.get("domains", {})
    gaps = summary.get("gaps", [])
    roadmap = summary.get("roadmap", {})
    narrative = summary.get("narrative", {})
    assumptions = summary.get("assumptions", [])
    not_applicable = summary.get("not_applicable", [])
    counts = summary.get("counts", {})
    index = attack_data.DEFAULT

    completed = assessment.completed_at.strftime("%Y-%m-%d %H:%M UTC") if assessment.completed_at else "—"
    intake = params.get("intake") or {}
    doc_title = intake.get("project_name") or assessment.name

    # Per-technique mapped rules (feeds why-phrases). Same inputs the drawer
    # explain endpoint uses — numbers/wording stay consistent across surfaces.
    mapped_by_technique: dict = {}
    for uc in use_cases:
        for m in uc.get("mappings") or []:
            mapped_by_technique.setdefault(m.get("technique_id"), []).append(
                {"name": uc.get("name"), "enabled": uc.get("enabled"),
                 "source": m.get("source"), "confidence": m.get("confidence")}
            )
    results = assessment.technique_results or []
    state_by_id = {r.get("technique_id"): r.get("state") for r in results}
    total_rules = counts.get("use_cases", len(use_cases))
    confidence_covered = (params.get("thresholds") or {}).get("confidence_covered", 0.7)
    gap_recs = narrative.get("gap_recommendations", {})
    ai_badge = (
        "<span class='badge ai'>AI-written text</span>"
        if narrative.get("generated_by") == "ai"
        else "<span class='badge'>Standard text</span>"
    )

    # --- cover ----------------------------------------------------------
    meta_rows = "".join(
        f"<tr><th>{_esc(label)}</th><td>{_esc(intake.get(key))}</td></tr>"
        for key, label in (
            ("project_name", "Organization / project"),
            ("scope_label", "Scope"),
            ("prepared_by", "Prepared by"),
            ("purpose_note", "Purpose"),
        )
        if intake.get(key)
    )
    files = files or []
    uc_file = next((f for f in files if f.get("kind") == "use_cases"), None)
    env_file = next((f for f in files if f.get("kind") == "environment"), None)
    env = params.get("environment") or {}
    env_lists = params.get("environment_lists") or {}
    upload_bits = [
        (f"Detection rules: {_esc(uc_file.get('filename'))} — " if uc_file else "Detection rules: ")
        + f"{_esc(total_rules)} rules ({_esc(counts.get('customer_tagged', 0))} tagged by you, "
        + f"{_esc(counts.get('keyword_tagged', 0))} keyword-matched, {_esc(counts.get('ai_tagged', 0))} AI-tagged, "
        + f"{_esc(counts.get('unmapped', 0))} unmapped, {_esc(counts.get('invalid', 0))} invalid)"
    ]
    if env_file or env.get("platforms"):
        upload_bits.append(
            (f"Environment: {_esc(env_file.get('filename'))} — " if env_file else "Environment: ")
            + f"platforms {_esc(', '.join(env.get('platforms') or []) or 'none detected')}"
            + (" · OT/ICS assets" if env.get("has_ics_assets") else "")
            + (" · managed mobile" if env.get("has_managed_mobile") else "")
            + f" · {len(env_lists.get('log_sources') or [])} log sources"
            + f" · {len(env_lists.get('tooling') or [])} tooling entries"
        )
    else:
        upload_bits.append(
            "Environment: none provided — full ATT&CK matrices assessed, the score is a lower bound"
        )
    upload_html = "".join(f"<p class='muted'>{b}</p>" for b in upload_bits)

    # --- executive: scorecard, top-5 fixes, roadmap glance, trend --------
    scorecard = "".join(
        "<div class='tile'>"
        f"<b style='color:{_traffic_color(d.get('strict_pct'))}'>{_esc(d.get('strict_pct'))}%</b>"
        f"{_esc(DOMAIN_LABELS.get(key, key))}<br>"
        f"<span class='muted'>{_esc(d.get('covered'))} of {_esc(d.get('applicable'))} techniques covered</span>"
        "</div>"
        for key, d in _ordered_domains(domains)
        if d.get("applicable", 0) > 0
    )
    gated_notes = "".join(
        f"<p class='muted'>{_esc(DOMAIN_LABELS.get(key, key))}: not assessed — "
        f"{_esc(next((n['reason'] for n in not_applicable if n.get('domain') == key), ''))}</p>"
        for key, d in _ordered_domains(domains)
        if d.get("applicable", 0) == 0
    )

    fixes_html = ""
    for g in gaps[:5]:
        tid = g.get("technique_id")
        described = plain_language.describe_technique(tid, index)
        relevance = g.get("threat_relevance") or []
        matters = (
            "Publicly reported technique of " + ", ".join(relevance)
            if relevance
            else ("Among the most-used attacker techniques in real intrusions"
                  if g.get("tier", 4) <= 2 else "A common supporting attacker behavior")
        )
        sketch = plain_language.detection_sketch(tid, g.get("via")) or g.get("hint") or ""
        fixes_html += (
            "<div class='fix'>"
            f"<p><strong>{_esc(tid)} {_esc(g.get('name'))}</strong> "
            f"<span class='badge'>{_esc(FEASIBILITY_LABELS.get(g.get('feasibility'), ''))}</span> "
            f"<a class='xref' href='#g-{_esc(tid)}'></a></p>"
            + (f"<p>{_esc(described.get('definition'))}</p>" if described.get("definition") else "")
            + f"<p class='muted'>Why it matters to you: {_esc(matters)}.</p>"
            + f"<p class='muted'>The fix: {_esc(sketch)}</p>"
            + "</div>"
        )

    short_items = roadmap.get("short", [])
    applicable_total = overall.get("applicable") or 0
    projected = (
        round(100 * ((overall.get("covered") or 0) + len(short_items)) / applicable_total, 1)
        if applicable_total
        else None
    )
    roadmap_glance = " · ".join(
        f"{_esc(FEASIBILITY_LABELS[b])}: {len(roadmap.get(b, []))}" for b in ("short", "mid", "long")
    )
    projection_html = (
        f"<p><strong>Effort to impact:</strong> completing just the short-term items "
        f"raises coverage from {_esc(overall.get('strict_pct'))}% to about {_esc(projected)}%.</p>"
        if projected is not None and short_items
        else ""
    )

    trend_html = ""
    if compare:
        delta = (compare.get("overall_delta") or {}).get("strict_pct")
        arrow = "▲" if (delta or 0) > 0 else ("▼" if (delta or 0) < 0 else "•")
        color = "#10b981" if (delta or 0) > 0 else ("#f43f5e" if (delta or 0) < 0 else "#6b7280")
        trend_html = (
            "<h3>Trend vs your previous run</h3>"
            f"<p><span style='color:{color};font-weight:bold'>{arrow} "
            f"{_esc(abs(delta) if delta is not None else 0)} points</span> vs "
            f"“{_esc(compare.get('baseline_name'))}”"
            f" — newly covered: {len(compare.get('newly_covered') or [])}, "
            f"regressed: {len(compare.get('regressed') or [])}, "
            f"applicability changed: {len(compare.get('na_changed') or [])}."
            + (" <span class='muted'>ATT&CK versions differ between runs — "
               "version-drift techniques were skipped.</span>"
               if compare.get("attack_version_mismatch") else "")
            + "</p>"
        )

    # --- detailed: stacked tactic bars + one-liners ----------------------
    tactic_sections = ""
    for key, d in _ordered_domains(domains):
        if d.get("applicable", 0) == 0:
            continue
        rows = ""
        for t in d.get("tactics", []):
            line = plain_language.TACTIC_LINES.get(t.get("shortname"))
            rows += (
                "<tr><td style='width:46%'>"
                f"<strong>{_esc(t.get('name'))}</strong>"
                + (f" — <span class='muted'>{_esc(line)}</span>" if line else "")
                + "</td>"
                f"<td class='num' style='width:88px'>{_esc(t.get('covered'))}/{_esc(t.get('applicable'))}"
                f" · {_esc(t.get('strict_pct'))}%</td>"
                f"<td>{_stacked_bar(t.get('covered'), t.get('partial'), t.get('not_covered'), t.get('applicable'))}</td></tr>"
            )
        tactic_sections += (
            f"<h3>{_esc(DOMAIN_LABELS.get(key, key))} — coverage by attack stage</h3>"
            "<table><thead><tr><th>Attack stage — what it means</th>"
            "<th style='text-align:right'>Covered</th><th>Coverage bar "
            "(green covered · amber partial · red not covered)</th></tr></thead>"
            f"<tbody>{rows}</tbody></table>"
        )

    # --- detailed: mini parent-level heatmap grids -----------------------
    heatmap_sections = ""
    for key, d in _ordered_domains(domains):
        if d.get("applicable", 0) == 0:
            continue
        cells = "".join(
            f"<span class='cell' style='background:{STATE_COLORS.get(r.get('state'), '#9ca3af')}' "
            f"title='{_esc(r.get('technique_id'))}'>{_esc(r.get('technique_id'))}</span>"
            for r in results
            if r.get("domain") == key and "." not in (r.get("technique_id") or "")
        )
        heatmap_sections += (
            f"<h3>{_esc(DOMAIN_LABELS.get(key, key))} — technique map (parent level)</h3>"
            f"<div class='heatmap'>{cells}</div>"
        )

    # --- detailed: roadmap — compact per-bucket index into the register --
    # (Phase A9: this used to hold the full per-gap narrative inline per
    # bucket, duplicating what the gap register below also needs to be the
    # single home of that detail; it now just points there.)
    roadmap_sections = ""
    for bucket in ("short", "mid", "long"):
        bucket_gaps = [g for g in gaps if g.get("feasibility") == bucket]
        if not bucket_gaps:
            continue
        index_rows = "".join(
            f"<tr><td>{_esc(g.get('technique_id'))}</td><td>{_esc(g.get('name'))}</td>"
            f"<td class='num'>{'P' + str(g['tier']) if g.get('tier', 4) < 4 else 'Unranked'}</td>"
            f"<td><a class='xref' href='#g-{_esc(g.get('technique_id'))}'></a></td></tr>"
            for g in bucket_gaps
        )
        roadmap_sections += (
            f"<h3 class='bucket {bucket}'>{_esc(FEASIBILITY_LABELS[bucket])} — "
            f"{len(bucket_gaps)} item{'' if len(bucket_gaps) == 1 else 's'}</h3>"
            f"<p class='muted'>{_esc(narrative.get('roadmap_prose', {}).get(bucket, ''))}</p>"
            "<table class='compact'><thead><tr><th>Technique</th><th>Name</th>"
            "<th>Priority</th><th>Full details</th></tr></thead>"
            f"<tbody>{index_rows}</tbody></table>"
        )

    # --- detailed: gap register — single home of full per-gap detail ----
    # Dense table (not spaced-out cards) so every gap's full narrative
    # prints exactly once without the per-card spacing/badge overhead that
    # drove ~680 pages on a real 842-gap assessment; ranked order, one row
    # per gap, anchored by id for the roadmap's "details p. N" cross-refs.
    referenced_components: set = set()
    register_body_rows = ""
    for g in gaps:
        tid = g.get("technique_id")
        result = next((r for r in results if r.get("technique_id") == tid), None) or {
            "technique_id": tid, "state": g.get("state"), "na_reason": None,
        }
        mapped = mapped_by_technique.get(tid, [])
        why = plain_language.derive_why(
            result, mapped, total_rules=total_rules,
            sub_states=plain_language.sub_states_for(result, mapped, state_by_id, index),
            confidence_covered=confidence_covered,
        )
        sketch = plain_language.detection_sketch(tid, g.get("via"))
        bucket = g.get("feasibility")
        # Phase 14h: name the components here; the field guidance is
        # printed ONCE in the reference table below (the same components
        # recur across hundreds of gaps — repeating the full text per gap
        # added ~1.2MB / ~680 pages on a real 842-gap assessment).
        telemetry_components = [
            e["component"] for e in plain_language.telemetry_requirements(tid, index)
            if e["fields"]
        ]
        for _component in telemetry_components:
            referenced_components.add(_component)
        via_line = (
            f"Uses logs you already collect: {g.get('via')}" if bucket == "short" and g.get("via")
            else f"Onboard telemetry from tooling you own: {g.get('via')}" if bucket == "mid" and g.get("via")
            else "Needs a new telemetry capability"
        )
        tier = g.get("tier", 4)
        relevance = g.get("threat_relevance") or []
        flags = (
            [f"<span class='badge p{tier}'>P{tier}</span>"] if tier < 4
            else ["<span class='badge'>Unranked</span>"]
        )
        if relevance:
            flags.append("<span class='badge threat'>Threat match: " + _esc(", ".join(relevance)) + "</span>")
        if g.get("crown_jewel_relevant"):
            flags.append("<span class='badge crown'>Crown jewel</span>")
        details_bits = [f"<em>Why it's a gap:</em> {_esc(why)}"]
        if sketch:
            details_bits.append(f"<em>What good looks like:</em> {_esc(sketch)}")
        if telemetry_components:
            details_bits.append(
                f"<span class='muted'>Log fields needed: {_esc(', '.join(telemetry_components))}"
                " — see the log-fields reference after this register.</span>"
            )
        details_bits.append(f"<span class='muted'>{_esc(via_line)}</span>")
        if gap_recs.get(tid):
            details_bits.append(f"{ai_badge} {_esc(gap_recs.get(tid))}")
        else:
            details_bits.append(f"<span class='muted'>{_esc(g.get('hint') or '')}</span>")
        # Two-column layout: rank/id/name with state+flags stacked beneath in
        # ONE technique cell, so Details keeps ~2/3 of the page width instead
        # of losing it to three sparse columns (#/Flags/State).
        register_body_rows += (
            f"<tr id='g-{_esc(tid)}'>"
            f"<td class='gap-tech'><strong>#{_esc(g.get('rank'))} · {_esc(tid)}</strong> "
            f"{_esc(g.get('name'))}"
            f"<span class='gap-meta'>{_state_chip(g.get('state', ''))} {' '.join(flags)}</span></td>"
            f"<td>{'<br>'.join(details_bits)}</td></tr>"
        )
    gap_register_html = (
        "<table class='compact register'><thead><tr><th>Technique</th>"
        "<th>Details</th></tr></thead>"
        f"<tbody>{register_body_rows}</tbody></table>"
    ) if gaps else "<p class='muted'>No gaps — nothing to register.</p>"

    # Phase 14h reference: one row per curated component referenced above.
    telemetry_reference = ""
    if referenced_components:
        rows = "".join(
            f"<tr><td>{_esc(component)}</td>"
            f"<td>{_esc(', '.join(plain_language.TELEMETRY_FIELDS[component]['fields']))}</td>"
            f"<td>{_esc(plain_language.TELEMETRY_FIELDS[component]['where'])}<br>"
            f"<span class='muted'>{_esc(plain_language.TELEMETRY_FIELDS[component]['gotcha'])}</span></td></tr>"
            for component in sorted(referenced_components)
        )
        telemetry_reference = (
            "<h3>Log fields reference</h3>"
            "<p class='muted'>What a detection query needs from each kind of "
            "telemetry named above, and the most common reason a source you "
            "already collect still cannot support it. Verify these fields are "
            "present in your connector before building the rule.</p>"
            "<table class='compact'><thead><tr><th>Telemetry</th>"
            "<th>Your query needs</th><th>Where it comes from · what to check</th>"
            "</tr></thead>"
            f"<tbody>{rows}</tbody></table>"
        )

    # --- appendices ------------------------------------------------------
    register_rows = "".join(
        f"<tr><td>{_esc(r.get('technique_id'))}</td>"
        f"<td>{_esc((index.get(r.get('technique_id')) or {}).get('name', ''))}</td>"
        f"<td>{_esc(DOMAIN_LABELS.get(r.get('domain'), r.get('domain')))}</td>"
        f"<td>{_state_chip(r.get('state', ''))}</td>"
        f"<td class='num'>{len(r.get('use_case_refs', []))}</td></tr>"
        for r in results
    )
    assumptions_html = "".join(f"<li>{_esc(a)}</li>" for a in assumptions)
    # Space optimization: one row per distinct REASON with its techniques
    # listed — 37 identical "deprecated" rows collapse into one.
    na_sections = ""
    remaining = list(not_applicable)
    for title, match in _NA_GROUPS:
        grouped = [n for n in remaining if match(n.get("reason") or "")]
        remaining = [n for n in remaining if n not in grouped]
        if not grouped:
            continue
        by_reason: dict = {}
        for n in grouped:
            by_reason.setdefault(n.get("reason") or "", []).append(
                n.get("technique_id")
            )
        rows = "".join(
            f"<tr><td style='width:45%'>{_esc(reason)}</td>"
            f"<td class='num'>{len(tids)}</td>"
            f"<td>{_esc(', '.join(tids))}</td></tr>"
            for reason, tids in sorted(
                by_reason.items(), key=lambda kv: -len(kv[1])
            )
        )
        na_sections += (
            f"<h3>{_esc(title)} ({len(grouped)})</h3>"
            "<table class='compact'><thead><tr><th>Reason</th><th>#</th>"
            "<th>Techniques</th></tr></thead>"
            f"<tbody>{rows}</tbody></table>"
        )

    # Phase 14g: "How we read your files" — the parser's per-entry evidence.
    interpretations = env_lists.get("interpretations") or []
    how_read_html = ""
    if interpretations:
        rows = "".join(
            f"<tr><td>{_esc(i.get('entry'))}</td><td>{_esc(i.get('sheet'))}</td>"
            f"<td>{_esc(i.get('interpretation'))}</td></tr>"
            for i in interpretations
        )
        how_read_html = (
            "<h2 id='how-read'>Appendix: how we read your files</h2>"
            "<p class='muted'>Every environment entry and what the parser did with it — "
            "the evidence behind platform filtering and roadmap feasibility.</p>"
            "<table><thead><tr><th>Your entry</th><th>Sheet</th><th>How it was read</th></tr></thead>"
            f"<tbody>{rows}</tbody></table>"
        )

    appendix_note = ""
    shown_use_cases = sorted(use_cases, key=_row_ref_sort_key)
    if len(shown_use_cases) > MAX_APPENDIX_ROWS:
        shown_use_cases = shown_use_cases[:MAX_APPENDIX_ROWS]
        appendix_note = (
            f"<p class='muted'>Showing the first {MAX_APPENDIX_ROWS} of "
            f"{len(use_cases)} rules — the XLSX export contains all of them.</p>"
        )
    uc_rows = "".join(
        f"<tr><td>{_esc(uc.get('row_ref'))}</td><td>{_esc(uc.get('name'))}</td>"
        f"<td>{'Enabled' if uc.get('enabled') else ('Disabled' if uc.get('enabled') is False else 'Unknown')}</td>"
        f"<td>{_esc(', '.join(m.get('technique_id', '') for m in (uc.get('mappings') or [])) or '—')}</td>"
        f"<td>{_esc(_MAPPING_STATUS_PLAIN_XLSX.get(uc.get('mapping_status'), uc.get('mapping_status')))}</td>"
        f"<td>{_esc(uc.get('log_source') or '')}</td></tr>"
        for uc in shown_use_cases
    )

    # --- audit footer ----------------------------------------------------
    thresholds = params.get("thresholds", {})
    models_used = params.get("models_used", {})
    footer_bits = [
        f"ATT&amp;CK v{_esc(assessment.attack_version)}",
        f"generated {_esc(datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC'))}",
        f"run completed {_esc(completed)}",
        f"narrative: {_esc(narrative.get('generated_by', 'n/a'))}"
        + (f" ({_esc(narrative.get('model_used'))})" if narrative.get("model_used") else ""),
    ]
    if os.getenv("GIT_SHA"):
        footer_bits.append(f"build {_esc(os.getenv('GIT_SHA'))}")
    if models_used:
        footer_bits.append(
            "models: " + _esc("; ".join(f"{k}: {', '.join(v)}" for k, v in models_used.items()))
        )
    siem = params.get("siem") or {}
    if siem:
        # Phase 13d provenance: which SIEM, manual vs scheduled, when.
        # Non-secret fields only (workspace_ref never holds credentials).
        source_bits = [
            "source: Microsoft Sentinel pull",
            _esc(siem.get("trigger") or "manual"),
        ]
        if (siem.get("workspace_ref") or {}).get("workspace"):
            source_bits.append(_esc(siem["workspace_ref"]["workspace"]))
        if siem.get("connection_name"):
            source_bits.append(_esc(siem["connection_name"]))
        if siem.get("pulled_at"):
            source_bits.append("pulled " + _esc(str(siem["pulled_at"])[:16]))
        footer_bits.append(" · ".join(source_bits))
    if thresholds:
        footer_bits.append(
            _esc(
                f"thresholds: covered≥{thresholds.get('confidence_covered')}, "
                f"partial≥{thresholds.get('confidence_partial_floor')}, "
                f"partial credit {thresholds.get('partial_credit')}, "
                f"disabled counts: {'yes' if thresholds.get('count_disabled_as_coverage') else 'no'}"
            )
        )

    context = {
        "page_title": f"MITRE ATT&amp;CK Coverage Assessment — {_esc(assessment.name)}",
        "logo_data_uri": LOGO_DATA_URI,
        "brand_name_esc": _esc(branding["report_display_name"]),
        "brand_color": branding["report_accent_color"],  # hex-validated by resolve_branding, not HTML content
        "brand_watermark_esc": _esc(branding["report_watermark_text"]),
        "doc_title_esc": _esc(doc_title),
        "doc_title_suffix": '' if doc_title == assessment.name else f" — {_esc(assessment.name)}",
        "meta_rows": meta_rows,
        "attack_version_esc": _esc(assessment.attack_version),
        "completed_esc": _esc(completed),
        "overall_strict_pct_esc": _esc(overall.get('strict_pct')),
        "overall_weighted_pct_esc": _esc(overall.get('weighted_pct')),
        "overall_applicable_esc": _esc(overall.get('applicable')),
        "overall_covered_esc": _esc(overall.get('covered')),
        "overall_partial_esc": _esc(overall.get('partial')),
        "upload_html": upload_html,
        "toc_how_read_li": '<li><a href="#how-read">Appendix: how we read your files</a></li>' if how_read_html else '',
        "scorecard": scorecard,
        "gated_notes": gated_notes,
        "narrative_summary_esc": _esc(narrative.get('executive_summary', '')),
        "ai_badge": ai_badge,
        "fixes_html_or_default": fixes_html or "<p class='muted'>No gaps — nothing to fix.</p>",
        "roadmap_glance": roadmap_glance,
        "projection_html": projection_html,
        "trend_html": trend_html,
        "tactic_sections": tactic_sections,
        "heatmap_sections": heatmap_sections,
        "gaps_len": len(gaps),
        "roadmap_sections": roadmap_sections,
        "gap_register_html": gap_register_html,
        "telemetry_reference": telemetry_reference,
        "results_len": len(results),
        "register_rows": register_rows,
        "not_applicable_len": len(not_applicable),
        "na_sections": na_sections,
        "assumptions_html_or_default": assumptions_html or '<li>None.</li>',
        "how_read_html": how_read_html,
        "use_cases_len": len(use_cases),
        "appendix_note": appendix_note,
        "uc_rows": uc_rows,
        "footer_line": ' · '.join(footer_bits),
    }
    html = _JINJA_ENV.get_template("report.html").render(**context)

    if scope == "executive":
        # Cut everything between the DETAILED marker and the footer, drop the
        # TOC (its page numbers point at removed sections), and strip the
        # executive cross-reference links whose anchors no longer exist.
        start = html.index("<!-- =========================== DETAILED")
        end = html.index('<div class="footer">')
        html = html[:start] + html[end:]
        toc_start = html.index("<h3>Contents</h3>")
        toc_end = html.index("</ul>", toc_start) + len("</ul>")
        html = html[:toc_start] + html[toc_end:]
        html = re.sub(r"<a class='xref' href='#g-[^']*'></a>", "", html)
        # Phase A11 piece 3: this cut is ONLY cover + executive summary (the
        # detailed/appendix parts are already gone above) — forcing a break
        # between them here just strands a half-empty page 2. Let the two
        # flow together; the full PDF still keeps the break (a genuine
        # cover->executive PART boundary there).
        html = html.replace(' class="page-break"', '')
    elif scope in _SECTION_SCOPES:
        # Per-tab download: document title + just that section + footer.
        start_marker, end_marker = _SECTION_SCOPES[scope]
        head_end = html.index('<table class="cover-meta"')
        section_start = html.index(start_marker)
        section_end = html.index(end_marker)
        footer_start = html.index('<div class="footer">')
        html = html[:head_end] + html[section_start:section_end] + html[footer_start:]
        html = html.replace(' class="page-break"', '')
        html = re.sub(r"<a class='xref' href='#g-[^']*'></a>", "", html)
    return html


def generate_pdf(html_content: str) -> bytes:
    """HTML -> PDF. Lazy import: WeasyPrint's native libs exist only in the
    prod image (Dockerfile.prod) — see app/scoring/report.py precedent."""
    from weasyprint import HTML

    return HTML(string=html_content).write_pdf()
